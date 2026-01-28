"""
Script Generator Module using Gemini AI
Generates narration scripts from manhwa panel images
"""

import os
import json
import base64
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from pathlib import Path
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptGenerator:
    """Generates recap scripts from manhwa images using Gemini AI"""
    
    def __init__(self, api_keys: list = None, config_path: str = None):
        # Model configuration - valid free models
        self.models = [
            'gemini-2.0-flash',
            'gemini-1.5-flash',
        ]
        self.current_model_index = 0
        self.current_key_index = 0
        
        # Load API keys from config if not provided
        if not api_keys and config_path:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Support both single key (string) and multiple keys (list)
                if 'gemini_api_keys' in config and isinstance(config['gemini_api_keys'], list):
                    self.api_keys = config['gemini_api_keys']
                elif 'gemini_api_key' in config:
                    self.api_keys = [config['gemini_api_key']]
        elif api_keys:
            self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
            
        if not self.api_keys:
            raise ValueError("No Gemini API keys found. Please provide at least one key.")
            
        # Per-key quota tracking
        self.key_last_used = {}  # Track when each key was last used
        self.key_exhausted_until = {}  # Track when each key becomes available again
        self.recent_429_count = 0  # Track recent quota errors for adaptive slowdown
        self.successful_requests = 0  # Track successes
        
        logger.info(f"Initialized with {len(self.api_keys)} API keys")
        self._configure_model()
        
        # Load config for templates
        self.config = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)

    def _configure_model(self):
        """Configure GenAI with the current key and model"""
        current_key = self.api_keys[self.current_key_index]
        current_model = self.models[self.current_model_index]
        
        genai.configure(api_key=current_key)
        self.model = genai.GenerativeModel(current_model)
        
        # Mask key for logging (first 4 chars ... last 4 chars)
        masked_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else "***"
        logger.info(f"Active Configuration: Model={current_model}, Key=#{self.current_key_index + 1} ({masked_key})")

    def _rotate_key(self):
        """Switch to the next available API key"""
        if len(self.api_keys) <= 1:
            return False
            
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_model()
        return True

    def _rotate_model(self):
        """Switch to the next available model"""
        if self.current_model_index >= len(self.models) - 1:
            return False
            
        self.current_model_index += 1
        # Reset key index when switching models to try all keys with new model
        self.current_key_index = 0
        self._configure_model()
        logger.warning(f"Fallback triggered: Switched to model {self.models[self.current_model_index]}")
        return True
    
    def _is_key_available(self, key_index: int) -> bool:
        """Check if a key is available (not exhausted)"""
        if key_index in self.key_exhausted_until:
            if time.time() < self.key_exhausted_until[key_index]:
                return False  # Still exhausted
            else:
                # Cooldown expired, remove from exhausted list
                del self.key_exhausted_until[key_index]
        return True
    
    def _mark_key_exhausted(self, key_index: int, cooldown_minutes: int = 10):
        """Mark a key as exhausted for a certain period"""
        cooldown_seconds = cooldown_minutes * 60
        self.key_exhausted_until[key_index] = time.time() + cooldown_seconds
        logger.warning(f"Key #{key_index + 1} marked as exhausted for {cooldown_minutes} minutes")
    
    def _get_available_key_count(self) -> int:
        """Count how many keys are currently available"""
        return sum(1 for i in range(len(self.api_keys)) if self._is_key_available(i))
    
    def _get_adaptive_delay(self, base_delay: float) -> float:
        """Calculate adaptive delay based on recent quota pressure"""
        # If we're seeing many 429s, slow down exponentially
        if self.recent_429_count > 5:
            multiplier = min(self.recent_429_count / 5, 4.0)  # Max 4x slowdown
            adjusted_delay = base_delay * multiplier
            logger.warning(f"Adaptive slowdown: {adjusted_delay:.1f}s (recent 429s: {self.recent_429_count})")
            return adjusted_delay
        return base_delay
    
    
    def _load_image(self, image_path: str) -> Image.Image:
        """Load and prepare image for API"""
        img = Image.open(image_path)
        
        # Resize if too large (Gemini has limits)
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
    
    def _batch_images(self, image_paths: list, batch_size: int = 10) -> list:
        """Split images into batches for API calls"""
        return [image_paths[i:i + batch_size] for i in range(0, len(image_paths), batch_size)]
    
    def _generate_batch_script(self, image_paths: list, batch_num: int, total_batches: int, 
                                manga_name: str, chapter: str) -> str:
        """Generate script for a batch of images"""
        
        # Load images
        images = []
        for path in image_paths:
            try:
                img = self._load_image(path)
                images.append(img)
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
        
        if not images:
            return ""
        
        # Build prompt for image-level narrations
        prompt = f"""You are a professional manhwa recap narrator. Analyze these {len(images)} manhwa panels from "{manga_name}" Chapter {chapter}.

This is batch {batch_num} of {total_batches} - {"start the story from the beginning" if batch_num == 1 else "continue the story from where the previous batch left off"}.

For EACH image (0 to {len(images)-1}), provide:
1. Engaging narration text for that specific panel
2. Estimated duration in seconds (how long to display this panel)

Instructions:
- Use present tense and dramatic narration style
- Include character emotions and key dialogue when visible
- Focus ONLY on story events, character actions, and dialogue
- DO NOT describe art style or panel composition
- Keep narration descriptive and substantial (Aim for 40-60 words per image to ensure good pacing)
- Make it engaging for viewers who haven't read the chapter

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "narrations": [
    {{"image_index": 0, "text": "The hero stands at the dungeon entrance.", "duration": 3.5}},
    {{"image_index": 1, "text": "A massive shadow emerges!", "duration": 2.8}}
  ]
}}

Return ONLY valid JSON, no other text."""

        max_fails = 50  # Total allowed failures before giving up
        current_fails = 0
        base_delay = 2
        max_delay = 300  # 5 minutes maximum backoff
        cooldown_period = 300  # 5 minutes cool-down
        
        # Track failures for the CURRENT model specifically
        keys_tried_for_model = set()
        
        while current_fails < max_fails:
            try:
                # Call Gemini API with images
                response = self.model.generate_content([prompt] + images)
                response_text = response.text.strip()
                
                # Parse JSON response
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                # Success! Return parsed JSON
                self.successful_requests += 1
                self.recent_429_count = max(0, self.recent_429_count - 1)  # Decay on success
                return json.loads(response_text)
                
            except Exception as e:
                current_fails += 1
                error_str = str(e)
                current_model = self.models[self.current_model_index]
                
                if "429" in error_str or "Resource has been exhausted" in error_str:
                    logger.warning(f"Quota exceeded (429) on Key #{self.current_key_index + 1} using {current_model}")
                    
                    # Track quota pressure
                    self.recent_429_count += 1
                    
                    # Mark current key as exhausted (adaptive cooldown based on pressure)
                    cooldown_min = 5 if self.recent_429_count < 10 else 10
                    self._mark_key_exhausted(self.current_key_index, cooldown_minutes=cooldown_min)
                    keys_tried_for_model.add(self.current_key_index)
                    
                    # Check how many keys are still available
                    available_keys = self._get_available_key_count()
                    logger.info(f"Available keys: {available_keys}/{len(self.api_keys)}")
                    
                    # If NO keys available: enter cool-down mode
                    if available_keys == 0:
                        logger.error("=" * 70)
                        logger.error("ALL API KEYS EXHAUSTED!")
                        logger.error(f"Entering cool-down mode for {cooldown_period/60:.0f} minutes...")
                        logger.error("=" * 70)
                        
                        time.sleep(cooldown_period)
                        self.key_exhausted_until.clear()
                        keys_tried_for_model.clear()
                        continue
                    
                    # Try to find an available key
                    found_available = False
                    for i in range(len(self.api_keys)):
                        next_key_idx = (self.current_key_index + i + 1) % len(self.api_keys)
                        if self._is_key_available(next_key_idx):
                            self.current_key_index = next_key_idx
                            self._configure_model()
                            logger.info(f"Rotated to available Key #{self.current_key_index + 1}")
                            found_available = True
                            time.sleep(1)
                            break
                    
                    if found_available:
                        continue
                    
                    # If all keys tried for this model, try switching MODEL
                    if len(keys_tried_for_model) >= len(self.api_keys):
                        if self._rotate_model():
                            logger.info(f"All keys exhausted for {current_model}. Switching to {self.models[self.current_model_index]}...")
                            keys_tried_for_model.clear()
                            time.sleep(2)
                            continue
                    
                    # Extended exponential backoff
                    sleep_time = min(base_delay * (2 ** (current_fails // 5)), max_delay)
                    sleep_time += random.uniform(0, 5)
                    logger.warning(f"Retrying in {sleep_time:.1f}s... (Failures {current_fails}/{max_fails})")
                    time.sleep(sleep_time)
                    continue
                
                # Non-429 errors
                logger.error(f"Gemini API error ({current_model}): {e}")
                if current_fails < 5:
                    time.sleep(2)
                    continue
                raise
        
        # If we exit the loop, raise error
        raise RuntimeError(f"Failed to generate script after {current_fails} failures across all keys/models.")
    
    def generate_script(self, images_dir: str, manga_name: str, chapter: str, 
                        progress_callback=None) -> dict:
        """
        Generate full narration script from chapter images
        
        Returns:
            dict with 'script', 'full_script', 'script_path', 'segments'
        """
        # Get all images
        image_paths = sorted([
            os.path.join(images_dir, f) for f in os.listdir(images_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        ])
        
        if not image_paths:
            raise ValueError(f"No images found in {images_dir}")
        
        logger.info(f"Generating script for {len(image_paths)} images")
        
        # Create batches
        batch_size = self.config.get('generation_batch_size', 3) 
        batches = self._batch_images(image_paths, batch_size=batch_size)
        
        # Generator config
        base_delay = self.config.get('generation_delay', 30)
        
        # Generate script for each batch
        segments = []
        raw_scripts = []
        segment_counter = 0
        
        for idx, batch in enumerate(batches):
            # Apply adaptive delay between batches based on quota pressure
            if idx > 0:
                adaptive_delay = self._get_adaptive_delay(base_delay)
                available_keys = self._get_available_key_count()
                
                # Extra caution if many keys are exhausted
                if available_keys < len(self.api_keys) * 0.3:  # Less than 30% available
                    logger.warning(f"Low key availability ({available_keys}/{len(self.api_keys)}). Extending delay...")
                    adaptive_delay *= 1.5
                
                logger.info(f"Waiting {adaptive_delay:.1f}s before next batch...")
                time.sleep(adaptive_delay)
                
            logger.info(f"Processing batch {idx + 1}/{len(batches)} (Size: {len(batch)})")
            
            batch_result = self._generate_batch_script(
                batch, idx + 1, len(batches), manga_name, chapter
            )
            
            # Handle JSON response with image-level narrations
            if isinstance(batch_result, dict) and 'narrations' in batch_result:
                narrations = batch_result['narrations']
                
                # Create image-level segments
                for narration in narrations:
                    img_idx = narration.get('image_index', 0)
                    if img_idx < len(batch):
                        segments.append({
                            'text': narration['text'],
                            'images': [batch[img_idx]],
                            'duration': narration.get('duration', 3.0),
                            'batch_index': segment_counter,
                            'original_batch': idx,
                            'image_index': img_idx
                        })
                        raw_scripts.append(narration['text'])
                        segment_counter += 1
            else:
                # Fallback to old batch-level format
                raw_scripts.append(str(batch_result))
                segments.append({
                    'text': str(batch_result),
                    'images': batch,
                    'batch_index': segment_counter,
                    'original_batch': idx
                })
                segment_counter += 1
            
            if progress_callback:
                progress_callback(idx + 1, len(batches))
        
        # Combine scripts
        combined_script = " ".join(raw_scripts)
        
        # Add intro and outro
        channel_name = self.config.get('channel_name', 'Manhwa Recaps')
        intro = f"Welcome back to {channel_name}! Today we're diving into Chapter {chapter} of {manga_name}. Let's get into it!\n\n"
        outro = f"\n\nAnd that's all for Chapter {chapter} of {manga_name}! If you enjoyed this recap, make sure to like and subscribe for more content. See you in the next one!"
        
        full_script = intro + combined_script + outro
        
        # Save script to file
        script_dir = os.path.dirname(images_dir)
        script_path = os.path.join(script_dir, "script.txt")
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(full_script)
            
        # Save segment data for advanced sync
        segments_path = os.path.join(script_dir, "script_segments.json")
        with open(segments_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, indent=2)
        
        logger.info(f"Script saved to: {script_path}")
        
        return {
            'script': combined_script,
            'full_script': full_script,
            'script_path': script_path,
            'segments': segments, # New: Return segments for sync
            'word_count': len(full_script.split()),
            'estimated_duration': len(full_script.split()) / 150
        }


def generate_script(images_dir: str, manga_name: str, chapter: str,
                    api_keys: list = None, config_path: str = None,
                    progress_callback=None) -> dict:
    """Convenience function for generating script"""
    generator = ScriptGenerator(api_keys, config_path)
    return generator.generate_script(images_dir, manga_name, chapter, progress_callback)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 3:
        images_dir = sys.argv[1]
        manga_name = sys.argv[2]
        chapter = sys.argv[3]
        if len(sys.argv) > 4:
            api_keys_str = sys.argv[4]
            api_keys = api_keys_str.split(',') if ',' in api_keys_str else [api_keys_str]
        else:
            api_keys = None
        
        result = generate_script(images_dir, manga_name, chapter, api_keys)
        print(f"\nScript generated!")
        print(f"Saved to: {result['script_path']}")
        print(f"Word count: {result['word_count']}")
        print(f"Estimated duration: {result['estimated_duration']:.1f} minutes")
