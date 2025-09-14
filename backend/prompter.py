import os
import functools
import glob
import io

from typing import Optional, List, Dict, Any, Iterator

import base64
import mimetypes
from pathlib import Path
from PIL import Image

import anthropic
from templater import partial_render

def downsample_image_to_480p(image_path: str) -> bytes:
    """
    Downsample an image to 480p (640x480 or maintaining aspect ratio with max height 480px).
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Downsampled image as bytes
    """
    with Image.open(image_path) as img:
        # Convert to RGB if necessary (handles RGBA, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate new dimensions maintaining aspect ratio
        original_width, original_height = img.size
        
        # Target height is 480px, calculate width to maintain aspect ratio
        target_height = 480
        target_width = int((original_width * target_height) / original_height)
        
        # If the calculated width is too large, limit it and recalculate height
        max_width = 640
        if target_width > max_width:
            target_width = max_width
            target_height = int((original_height * target_width) / original_width)
        
        # Only downsample if the image is larger than target
        if original_width > target_width or original_height > target_height:
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            print(f"  Downsampled from {original_width}x{original_height} to {target_width}x{target_height}")
        else:
            print(f"  Image already smaller than 480p ({original_width}x{original_height}), keeping original size")
        
        # Save to bytes buffer as JPEG with high quality
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        return buffer.getvalue()

@functools.cache
def encode_image(image_path: str) -> tuple[str, str]:
    """
    Encode an image file to base64 and determine its MIME type, with 480p downsampling.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (base64_string, mime_type)
    """
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Get original MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError(f"File is not a supported image type: {image_path}")
    
    # Downsample the image
    try:
        downsampled_bytes = downsample_image_to_480p(image_path)
        # After downsampling, we always use JPEG format
        mime_type = 'image/jpeg'
    except Exception as e:
        print(f"  Warning: Failed to downsample {image_path}, using original: {e}")
        # Fall back to original file if downsampling fails
        with open(image_path, "rb") as image_file:
            downsampled_bytes = image_file.read()
    
    # Encode to base64
    encoded_image = base64.b64encode(downsampled_bytes).decode('utf-8')
    
    return encoded_image, mime_type

def create_message_content(text: str, image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Create message content with text and optional images.
    
    Args:
        text: The text prompt
        image_paths: List of paths to image files (optional)
        
    Returns:
        List of content blocks for the API
    """
    content = []
    image_names = []
    
    # Add images with associated filenames
    if image_paths:
        for image_path in image_paths:
            try:
                print(f"Processing image: {os.path.basename(image_path)}")
                encoded_image, mime_type = encode_image(image_path)
                image_name = os.path.basename(image_path)
                
                # Add a text block with the filename before each image
                content.append({
                    "type": "text",
                    "text": f"Image: {image_name}"
                })
                
                # Add the image block
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": encoded_image
                    }
                })
                
                image_names.append(image_name)
                print(f"✓ Added image: {image_name}")
            except Exception as e:
                print(f"✗ Failed to add image {image_path}: {e}")
    
    # Add main text content
    if text.strip():
        content.append({
            "type": "text",
            "text": text
        })
    
    # Add summary of images if any were included
    if image_names:
        image_list = ", ".join(image_names)
        content.append({
            "type": "text",
            "text": f"\nTotal images provided: {len(image_names)} ({image_list})"
        })
    
    return content

def prompt_claude_haiku_with_images_streaming(
    message: str,
    image_paths: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 1000,
    model: str = "claude-3-haiku-20240307"
) -> Iterator[str]:
    """
    Send a prompt with optional images to Claude and stream the response.
    
    Args:
        message: The text prompt/message to send to Claude
        image_paths: List of paths to image files (optional)
        api_key: Your Anthropic API key (if not set as environment variable)
        max_tokens: Maximum tokens in the response
        model: Claude model to use
        
    Yields:
        Chunks of Claude's response as strings
    """
    
    # Initialize the client
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        client = anthropic.Anthropic()
    
    try:
        # Create message content with text and images
        content = create_message_content(message, image_paths)
        
        if not content:
            yield "Error: No content to send (no text or valid images)"
            return
        
        print(f"Sending message to {model} with streaming...")
        
        # Send the message to Claude with streaming
        stream = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            stream=True
        )
        
        # Yield chunks as they arrive
        for chunk in stream:
            if chunk.type == "content_block_delta":
                if hasattr(chunk.delta, 'text'):
                    yield chunk.delta.text
        
    except Exception as e:
        yield f"Error: {str(e)}"

def prompt_claude_haiku_with_images(
    message: str,
    image_paths: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 1000,
    model: str = "claude-3-haiku-20240307",
    stream: bool = False
) -> str:
    """
    Send a prompt with optional images to Claude and return the response.
    
    Args:
        message: The text prompt/message to send to Claude
        image_paths: List of paths to image files (optional)
        api_key: Your Anthropic API key (if not set as environment variable)
        max_tokens: Maximum tokens in the response
        model: Claude model to use
        stream: Whether to use streaming (if True, prints response as it arrives)
        
    Returns:
        Claude's complete response as a string
    """
    
    if stream:
        # Use streaming and collect the full response
        full_response = ""
        print("Streaming response:")
        print("-" * 50)
        
        for chunk in prompt_claude_haiku_with_images_streaming(
            message, image_paths, api_key, max_tokens, model
        ):
            print(chunk, end='', flush=True)
            full_response += chunk
        
        print("\n" + "-" * 50)
        return full_response
    else:
        # Use non-streaming (original behavior)
        # Initialize the client
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
        else:
            client = anthropic.Anthropic()
        
        try:
            # Create message content with text and images
            content = create_message_content(message, image_paths)
            
            if not content:
                return "Error: No content to send (no text or valid images)"
            
            # Send the message to Claude
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )
            
            # Extract and return the text response
            return response.content[0].text
            
        except Exception as e:
            return f"Error: {str(e)}"

def get_image_files_from_input(image_input: str) -> List[str]:
    """
    Parse image file paths from user input.
    Supports single file, multiple files separated by commas, or glob patterns.
    
    Args:
        image_input: User input string with image paths
        
    Returns:
        List of valid image file paths
    """
    if not image_input.strip():
        return []
    
    image_paths = []
    
    # Split by comma and clean up paths
    raw_paths = [path.strip().strip('"\'') for path in image_input.split(',')]
    
    for path in raw_paths:
        if '*' in path or '?' in path:
            # Handle glob patterns
            from glob import glob
            matches = glob(path)
            image_paths.extend(matches)
        else:
            # Handle direct file paths
            if os.path.exists(path):
                image_paths.append(path)
            else:
                print(f"Warning: File not found: {path}")
    
    # Filter to only image files
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff'}
    valid_images = []
    
    for path in image_paths:
        if Path(path).suffix.lower() in supported_extensions:
            valid_images.append(path)
        else:
            print(f"Warning: Unsupported file type: {path}")
    
    return valid_images


if __name__ == "__main__":
    # Change this to your directory
    directory = "./demo/hack/"

    # Match common image extensions (case-insensitive if you normalize with .lower())
    image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.gif", "*.bmp", "*.tiff", "*.webp")

    # Collect all images
    files = []
    for ext in image_extensions:
        files.extend(glob.glob(os.path.join(directory, ext)))

    print(f"Found {len(files)} image files")
    print(files)
    
    # Example usage with streaming
    for agent in glob.glob('./prompts/agents/*.md'):
        print(agent)
        response = prompt_claude_haiku_with_images(
            partial_render(partial_render(
                open('./prompts/template.jinja').read(),
                {
                    'personality': open(agent).read()
                }
            ), context={"post_type": "Instagram Story for a fun philosophy club."}),
            image_paths=files,
            api_key=os.environ["CLAUDE_API_KEY"],
            max_tokens=4096,
            model="claude-3-haiku-20240307",
            stream=False  # Enable streaming
        )
        print(response)