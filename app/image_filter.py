"""
Image Filter Module using Gemini AI
Filters manhwa panels to keep only essential/engaging images for video
"""

import os
import json
import base64
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageFilter:
    """Filters manhwa panels to keep only essential/engaging ones for video"""
    
    def __init__(self, api_keys: list = None, config_path: str = None):
        self.api_keys = []
        self.current_key_index = 0
        
        # Load from config if path provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if config.get('gemini_api_keys'):
                    self.api_keys = config['gemini_api_keys']
                elif config.get('gemini_api_key'):
                    self.api_keys = [config['gemini_api_key']]
        
        # Override with explicit keys
        if api_keys:
            self.api_keys = api_keys
        
        if not self.api_keys:
            raise ValueError("No Gemini API keys provided")
        
        self._configure_model()
    
    def _configure_model(self):
        """Configure GenAI with the current key"""
        genai.configure(api_key=self.api_keys[self.current_key_index])
        # Use cheaper/faster model for filtering to save API quota
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def _rotate_key(self):
        """Switch to the next available API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_model()
        logger.info(f"Rotated to API key #{self.current_key_index + 1}")
    
    def _load_image(self, image_path: str):
        """Load and prepare image for API"""
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize for API (max 1024px on longest side to save tokens)
        max_size = 512
        ratio = min(max_size / img.width, max_size / img.height)
        if ratio < 1:
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=70)
        buffer.seek(0)
        
        return {
            'mime_type': 'image/jpeg',
            'data': base64.b64encode(buffer.read()).decode()
        }
    
    def _batch_images(self, image_paths: list, batch_size: int = 10):
        """Split images into batches for API calls (reduced to 10 for faster processing)"""
        return [image_paths[i:i + batch_size] for i in range(0, len(image_paths), batch_size)]
    
    def _analyze_batch(self, image_paths: list, batch_num: int, total_batches: int) -> list:
        """
        Analyze a batch of images and return selection info.
        Returns list of dicts: [{filename, keep, score, type}, ...]
        """
        # Load images
        images = []
        filenames = []
        for path in image_paths:
            try:
                img = self._load_image(path)
                images.append(img)
                filenames.append(os.path.basename(path))
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
        
        if not images:
            return []
        
        # Build prompt
        prompt = f"""You are analyzing manhwa/manga panels for a recap video. 
Analyze these {len(images)} panels (batch {batch_num}/{total_batches}) and decide which ones to KEEP for an engaging video.

KEEP panels that have:
- Action scenes or dramatic moments
- Strong character emotions (anger, shock, happiness, sadness)
- Important plot reveals or story moments
- Visually striking art with minimal text
- Key character interactions

SKIP panels that have:
- Mostly text/dialogue (too much reading in video is boring)
- Transition or filler scenes
- Repetitive content (same scene from different angles)
- Plain backgrounds or establishing shots
- Panels that are mostly black/white borders

For a good recap video, aim to keep about 30-50% of panels - only the most visually engaging ones!

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "panels": [
    {{"index": 0, "keep": true/false, "score": 1-10, "type": "action/emotion/dialogue/plot/filler"}},
    {{"index": 1, "keep": true/false, "score": 1-10, "type": "action/emotion/dialogue/plot/filler"}},
    ...
  ]
}}

Where:
- index: panel number (0 to {len(images)-1})
- keep: true if should be included in video
- score: importance score 1-10 (10 = must include, 1 = skip)
- type: category of the panel

Return ONLY valid JSON, no other text."""

        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content([prompt] + images)
                response_text = response.text.strip()
                
                # Clean up response (remove markdown code blocks if present)
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                # Parse JSON
                result = json.loads(response_text)
                panels = result.get('panels', [])
                
                # Map back to filenames
                analyzed = []
                for panel in panels:
                    idx = panel.get('index', -1)
                    if 0 <= idx < len(filenames):
                        analyzed.append({
                            'filename': filenames[idx],
                            'path': image_paths[idx],
                            'keep': panel.get('keep', False),
                            'score': panel.get('score', 5),
                            'type': panel.get('type', 'unknown')
                        })
                
                return analyzed
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
                # Return all as "keep" on failure
                return [{'filename': f, 'path': p, 'keep': True, 'score': 5, 'type': 'unknown'} 
                        for f, p in zip(filenames, image_paths)]
                        
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "exhausted" in error_str.lower():
                    logger.warning(f"Quota exceeded, rotating key...")
                    self._rotate_key()
                    continue
                logger.error(f"API error: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)
                    continue
                raise
        
        # Fallback: keep all
        return [{'filename': f, 'path': p, 'keep': True, 'score': 5, 'type': 'unknown'} 
                for f, p in zip(filenames, image_paths)]
    
    def filter_images(self, images_dir: str, manga_name: str = "", chapter: str = "",
                      min_keep_ratio: float = 0.25, max_keep_ratio: float = 0.6) -> dict:
        """
        Filter images in directory and return selection.
        
        Args:
            images_dir: Directory containing panel images
            manga_name: Name of the manga (for context)
            chapter: Chapter number (for context)
            min_keep_ratio: Minimum percentage of images to keep (default 25%)
            max_keep_ratio: Maximum percentage of images to keep (default 60%)
        
        Returns:
            dict with:
                - selected_images: list of image paths to include (in order)
                - total_images: original count
                - selected_count: filtered count
                - analysis: full analysis data for each image
        """
        logger.info(f"Filtering images in {images_dir}")
        
        # Get sorted images
        image_files = sorted([
            os.path.join(images_dir, f) for f in os.listdir(images_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
            and '_processed' not in f and '_part_' not in f
        ])
        
        if not image_files:
            raise ValueError(f"No images found in {images_dir}")
        
        total_images = len(image_files)
        logger.info(f"Found {total_images} images to analyze")
        
        # Batch and analyze
        batches = self._batch_images(image_files)
        all_analysis = []
        
        for i, batch in enumerate(batches):
            logger.info(f"Analyzing batch {i + 1}/{len(batches)} ({len(batch)} images)")
            batch_results = self._analyze_batch(batch, i + 1, len(batches))
            all_analysis.extend(batch_results)
        
        # Sort by score and apply keep/skip decisions
        # First, respect the AI's keep decisions
        selected = [a for a in all_analysis if a.get('keep', False)]
        not_selected = [a for a in all_analysis if not a.get('keep', False)]
        
        # Ensure we meet minimum/maximum ratios
        min_count = int(total_images * min_keep_ratio)
        max_count = int(total_images * max_keep_ratio)
        
        # If too few selected, add more from not_selected by score
        if len(selected) < min_count:
            not_selected_sorted = sorted(not_selected, key=lambda x: x.get('score', 0), reverse=True)
            needed = min_count - len(selected)
            selected.extend(not_selected_sorted[:needed])
            logger.info(f"Added {needed} more images to meet minimum ratio")
        
        # If too many selected, remove lowest scores
        if len(selected) > max_count:
            selected_sorted = sorted(selected, key=lambda x: x.get('score', 0), reverse=True)
            selected = selected_sorted[:max_count]
            logger.info(f"Trimmed to {max_count} images to meet maximum ratio")
        
        # Sort back to original order (by filename)
        selected_sorted = sorted(selected, key=lambda x: x.get('filename', ''))
        selected_paths = [a['path'] for a in selected_sorted]
        
        logger.info(f"Filtered {total_images} images to {len(selected_paths)} essential panels")
        
        return {
            'selected_images': selected_paths,
            'total_images': total_images,
            'selected_count': len(selected_paths),
            'analysis': all_analysis
        }


def filter_images(images_dir: str, api_keys: list = None, config_path: str = None,
                  min_keep_ratio: float = 0.25, max_keep_ratio: float = 0.6) -> dict:
    """Convenience function for filtering images"""
    filter_instance = ImageFilter(api_keys=api_keys, config_path=config_path)
    return filter_instance.filter_images(images_dir, min_keep_ratio=min_keep_ratio, 
                                         max_keep_ratio=max_keep_ratio)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        images_dir = sys.argv[1]
        config_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        result = filter_images(images_dir, config_path=config_path)
        print(f"\nFiltering complete!")
        print(f"Original: {result['total_images']} images")
        print(f"Selected: {result['selected_count']} images")
        print(f"Reduction: {100 - (result['selected_count'] / result['total_images'] * 100):.1f}%")
    else:
        print("Usage: python image_filter.py <images_dir> [config_path]")
