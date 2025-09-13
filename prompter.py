import os
import glob
from typing import Optional, List, Dict, Any

import base64
import mimetypes
from pathlib import Path

import anthropic
from templater import partial_render

def encode_image(image_path: str) -> tuple[str, str]:
    """
    Encode an image file to base64 and determine its MIME type.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (base64_string, mime_type)
    """
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError(f"File is not a supported image type: {image_path}")
    
    # Read and encode the image
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    
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

def prompt_claude_haiku_with_images(
    message: str,
    image_paths: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 1000
) -> str:
    """
    Send a prompt with optional images to Claude Haiku and return the response.
    
    Args:
        message: The text prompt/message to send to Claude
        image_paths: List of paths to image files (optional)
        api_key: Your Anthropic API key (if not set as environment variable)
        max_tokens: Maximum tokens in the response
        
    Returns:
        Claude's response as a string
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
            return "Error: No content to send (no text or valid images)"
        
        # Send the message to Claude Haiku
        response = client.messages.create(
            model="claude-3-haiku-20240307",
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
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
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

    print(files)
    print(prompt_claude_haiku_with_images(partial_render(
        open('./prompts/template.jinja').read(),
        {
            'personality': open('./prompts/alex.md').read()
        }),
        image_paths=files,
        api_key=os.environ["CLAUDE_API_KEY"],
        max_tokens=100000
    ))