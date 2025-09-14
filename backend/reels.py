#!/usr/bin/env python3
"""
Instagram Reels-Style Highlight Generator with Suno AI
Creates engaging video reels from images with AI-generated music and descriptions
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import moviepy.editor as mp
from moviepy.video.fx import resize, fadein, fadeout
import anthropic
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class VideoConfig:
    """Configuration for video generation"""
    output_width: int = 1080
    output_height: int = 1920  # Instagram Reels aspect ratio
    fps: int = 30
    image_duration: float = 2.5  # seconds per image
    transition_duration: float = 0.5
    fade_duration: float = 0.3
    max_video_length: int = 60  # seconds (Instagram Reels limit)

@dataclass
class SunoConfig:
    """Configuration for Suno AI integration"""
    api_key: str = ""
    base_url: str = "https://api.suno.ai/v1"
    song_duration: int = 60  # seconds
    
class ReelsGenerator:
    def __init__(self, anthropic_api_key: str, suno_api_key: str = ""):
        """
        Initialize the Reels Generator
        
        Args:
            anthropic_api_key: API key for Claude 3.5
            suno_api_key: API key for Suno AI (optional, can be set later)
        """
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.suno_config = SunoConfig(api_key=suno_api_key)
        self.video_config = VideoConfig()
        
    def analyze_images_with_claude(self, image_paths: List[str]) -> Dict[str, str]:
        """
        Use Claude 3.5 to analyze images and generate descriptions and music prompts
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            Dictionary with 'description' and 'music_prompt' keys
        """
        logger.info(f"Analyzing {len(image_paths)} images with Claude 3.5...")
        
        # Prepare image data for Claude (in real implementation, you'd encode images)
        image_names = [Path(path).name for path in image_paths]
        
        prompt = f"""
        I have {len(image_paths)} images for creating an Instagram Reel: {', '.join(image_names)}
        
        Please provide:
        1. A compelling description of what story these images might tell (2-3 sentences)
        2. A music prompt for Suno AI that would complement this visual story
        
        The music should be:
        - Upbeat and engaging for social media
        - Appropriate for a 30-60 second highlight reel
        - Match the mood/theme of the images
        
        Format your response as JSON:
        {{
            "description": "Your description here",
            "music_prompt": "Your Suno AI music prompt here",
            "suggested_tags": ["tag1", "tag2", "tag3"],
            "mood": "upbeat/chill/dramatic/etc"
        }}
        """
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            response_text = response.content[0].text
            # Extract JSON from response (Claude might wrap it in text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            json_str = response_text[start_idx:end_idx]
            
            result = json.loads(json_str)
            logger.info("Successfully analyzed images with Claude 3.5")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing images with Claude: {e}")
            # Fallback response
            return {
                "description": "A beautiful collection of moments captured in time",
                "music_prompt": "upbeat electronic music with positive vibes, perfect for social media",
                "suggested_tags": ["memories", "moments", "life"],
                "mood": "upbeat"
            }
    
    def generate_music_with_suno(self, prompt: str, duration: int = 60) -> Optional[str]:
        """
        Generate music using Suno AI
        
        Args:
            prompt: Text prompt for music generation
            duration: Duration in seconds
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not self.suno_config.api_key:
            logger.warning("Suno AI API key not provided. Skipping music generation.")
            return None
            
        logger.info(f"Generating music with Suno AI: '{prompt}'")
        
        headers = {
            "Authorization": f"Bearer {self.suno_config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "duration": duration,
            "format": "mp3",
            "quality": "high"
        }
        
        try:
            # Submit generation request
            response = requests.post(
                f"{self.suno_config.base_url}/generate",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Suno AI request failed: {response.status_code}")
                return None
                
            job_data = response.json()
            job_id = job_data.get("id")
            
            if not job_id:
                logger.error("No job ID returned from Suno AI")
                return None
                
            # Poll for completion
            max_retries = 30  # 5 minutes max
            for attempt in range(max_retries):
                time.sleep(10)  # Wait 10 seconds between polls
                
                status_response = requests.get(
                    f"{self.suno_config.base_url}/jobs/{job_id}",
                    headers=headers,
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data.get("status") == "completed":
                        audio_url = status_data.get("audio_url")
                        if audio_url:
                            # Download the audio file
                            audio_response = requests.get(audio_url, timeout=30)
                            if audio_response.status_code == 200:
                                output_path = f"generated_music_{int(time.time())}.mp3"
                                with open(output_path, "wb") as f:
                                    f.write(audio_response.content)
                                logger.info(f"Music generated successfully: {output_path}")
                                return output_path
                    
                    elif status_data.get("status") == "failed":
                        logger.error("Suno AI generation failed")
                        break
                        
                logger.info(f"Music generation in progress... (attempt {attempt + 1}/{max_retries})")
            
            logger.error("Music generation timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error generating music with Suno AI: {e}")
            return None
    
    def enhance_image(self, image_path: str) -> np.ndarray:
        """
        Enhance image for better video quality
        
        Args:
            image_path: Path to image file
            
        Returns:
            Enhanced image as numpy array
        """
        # Load image
        pil_image = Image.open(image_path)
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Enhance image
        # Increase contrast slightly
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.1)
        
        # Increase saturation slightly
        enhancer = ImageEnhance.Color(pil_image)
        pil_image = enhancer.enhance(1.1)
        
        # Sharpen slightly
        pil_image = pil_image.filter(ImageFilter.UnsharpMask(radius=1, percent=50))
        
        # Convert to numpy array
        return np.array(pil_image)
    
    def create_video_clip_from_image(self, image_path: str, duration: float) -> mp.ImageClip:
        """
        Create a video clip from a single image with Ken Burns effect
        
        Args:
            image_path: Path to image file
            duration: Duration of the clip in seconds
            
        Returns:
            MoviePy ImageClip with effects applied
        """
        # Enhance image
        enhanced_image = self.enhance_image(image_path)
        
        # Create clip
        clip = mp.ImageClip(enhanced_image, duration=duration)
        
        # Resize to fit target dimensions while maintaining aspect ratio
        clip = clip.resize(height=self.video_config.output_height)
        
        # If width is too large, crop from center
        if clip.w > self.video_config.output_width:
            x_center = clip.w // 2
            x1 = x_center - self.video_config.output_width // 2
            x2 = x1 + self.video_config.output_width
            clip = clip.crop(x1=x1, x2=x2)
        
        # Add Ken Burns effect (subtle zoom and pan)
        def ken_burns_effect(get_frame, t):
            frame = get_frame(t)
            progress = t / duration
            
            # Zoom effect (1.0 to 1.1 scale)
            scale = 1.0 + 0.1 * progress
            h, w = frame.shape[:2]
            
            # Calculate new dimensions
            new_h, new_w = int(h * scale), int(w * scale)
            
            # Resize frame
            resized = cv2.resize(frame, (new_w, new_h))
            
            # Crop to original size (from center)
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            
            return resized[start_y:start_y + h, start_x:start_x + w]
        
        clip = clip.fl(ken_burns_effect)
        
        # Add fade in and fade out
        clip = clip.fadein(self.video_config.fade_duration)
        clip = clip.fadeout(self.video_config.fade_duration)
        
        return clip
    
    def add_transitions(self, clips: List[mp.VideoClip]) -> List[mp.VideoClip]:
        """
        Add smooth transitions between clips
        
        Args:
            clips: List of video clips
            
        Returns:
            List of clips with transitions applied
        """
        if len(clips) <= 1:
            return clips
        
        transition_clips = []
        
        for i, clip in enumerate(clips):
            if i == 0:
                # First clip - no transition needed
                transition_clips.append(clip)
            else:
                # Add crossfade transition
                prev_clip = transition_clips[-1]
                
                # Adjust timing for overlap
                transition_start = prev_clip.duration - self.video_config.transition_duration
                
                # Create transition effect
                clip = clip.set_start(transition_start)
                clip = clip.crossfadein(self.video_config.transition_duration)
                
                transition_clips.append(clip)
        
        return transition_clips
    
    def create_reel(self, image_paths: List[str], output_path: str = None, 
                   custom_music_path: str = None) -> str:
        """
        Create Instagram Reel from images
        
        Args:
            image_paths: List of paths to image files
            output_path: Custom output path (optional)
            custom_music_path: Path to custom music file (optional)
            
        Returns:
            Path to generated video file
        """
        if not image_paths:
            raise ValueError("No image paths provided")
        
        logger.info(f"Creating Instagram Reel from {len(image_paths)} images...")
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"instagram_reel_{timestamp}.mp4"
        
        # Analyze images with Claude 3.5
        analysis = self.analyze_images_with_claude(image_paths)
        logger.info(f"Analysis: {analysis['description']}")
        
        # Generate or use custom music
        music_path = custom_music_path
        if not music_path:
            music_path = self.generate_music_with_suno(
                analysis['music_prompt'], 
                self.suno_config.song_duration
            )
        
        # Calculate video timing
        total_image_time = len(image_paths) * self.video_config.image_duration
        max_duration = min(total_image_time, self.video_config.max_video_length)
        
        # Adjust image duration if needed
        if total_image_time > self.video_config.max_video_length:
            adjusted_duration = self.video_config.max_video_length / len(image_paths)
            logger.info(f"Adjusting image duration to {adjusted_duration:.2f}s to fit time limit")
        else:
            adjusted_duration = self.video_config.image_duration
        
        # Create video clips from images
        logger.info("Creating video clips from images...")
        clips = []
        for i, image_path in enumerate(image_paths):
            try:
                clip = self.create_video_clip_from_image(image_path, adjusted_duration)
                clips.append(clip)
                logger.info(f"Processed image {i+1}/{len(image_paths)}: {Path(image_path).name}")
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                continue
        
        if not clips:
            raise ValueError("No valid clips could be created from the provided images")
        
        # Add transitions
        clips = self.add_transitions(clips)
        
        # Concatenate clips
        logger.info("Combining video clips...")
        final_video = mp.concatenate_videoclips(clips, method="compose")
        
        # Add music if available
        if music_path and os.path.exists(music_path):
            logger.info("Adding background music...")
            try:
                audio = mp.AudioFileClip(music_path)
                
                # Trim or loop audio to match video duration
                if audio.duration > final_video.duration:
                    audio = audio.subclip(0, final_video.duration)
                elif audio.duration < final_video.duration:
                    # Loop the audio
                    loops_needed = int(np.ceil(final_video.duration / audio.duration))
                    audio = mp.concatenate_audioclips([audio] * loops_needed)
                    audio = audio.subclip(0, final_video.duration)
                
                # Reduce volume slightly to not overpower
                audio = audio.volumex(0.7)
                final_video = final_video.set_audio(audio)
                
            except Exception as e:
                logger.error(f"Error adding music: {e}")
        
        # Export final video
        logger.info(f"Exporting video to {output_path}...")
        final_video.write_videofile(
            output_path,
            fps=self.video_config.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None  # Suppress moviepy logging
        )
        
        # Cleanup
        final_video.close()
        for clip in clips:
            clip.close()
        
        if music_path and music_path != custom_music_path:
            # Remove generated music file (optional)
            pass
        
        logger.info(f"Instagram Reel created successfully: {output_path}")
        
        # Print analysis results
        print(f"\n📱 Instagram Reel Generated!")
        print(f"📁 Output: {output_path}")
        print(f"📝 Description: {analysis['description']}")
        print(f"🎵 Music prompt: {analysis['music_prompt']}")
        print(f"🏷️ Suggested tags: {', '.join(analysis.get('suggested_tags', []))}")
        print(f"😊 Mood: {analysis.get('mood', 'Unknown')}")
        
        return output_path

def main():
    """
    Example usage of the Instagram Reels Generator
    """
    # API Keys (replace with your actual keys)
    ANTHROPIC_API_KEY = "your_anthropic_api_key_here"
    SUNO_API_KEY = "your_suno_api_key_here"  # Optional
    
    # Initialize generator
    generator = ReelsGenerator(
        anthropic_api_key=ANTHROPIC_API_KEY,
        suno_api_key=SUNO_API_KEY
    )
    
    # Example image paths (replace with your actual image paths)
    image_paths = [
        "photo1.jpg",
        "photo2.jpg",
        "photo3.jpg",
        "photo4.jpg",
        "photo5.jpg"
    ]
    
    try:
        # Generate the reel
        output_video = generator.create_reel(image_paths)
        print(f"\n✅ Success! Your Instagram Reel is ready: {output_video}")
        
    except Exception as e:
        print(f"❌ Error creating reel: {e}")

if __name__ == "__main__":
    main()
