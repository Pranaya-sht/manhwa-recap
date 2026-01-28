"""
TTS Generator Module using Edge-TTS
Generates voiceover audio from narration scripts
"""

import os
import asyncio
import edge_tts
import logging

import logging
import tempfile
import shutil
from moviepy.editor import AudioFileClip, concatenate_audioclips

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Available voices for Edge-TTS
AVAILABLE_VOICES = {
    # Male voices
    'en-US-GuyNeural': {'gender': 'male', 'description': 'American Male (Guy)'},
    'en-US-ChristopherNeural': {'gender': 'male', 'description': 'American Male (Christopher)'},
    'en-GB-RyanNeural': {'gender': 'male', 'description': 'British Male (Ryan)'},
    'en-AU-WilliamNeural': {'gender': 'male', 'description': 'Australian Male (William)'},
    
    # Female voices
    'en-US-JennyNeural': {'gender': 'female', 'description': 'American Female (Jenny)'},
    'en-US-AriaNeural': {'gender': 'female', 'description': 'American Female (Aria)'},
    'en-GB-SoniaNeural': {'gender': 'female', 'description': 'British Female (Sonia)'},
    'en-AU-NatashaNeural': {'gender': 'female', 'description': 'Australian Female (Natasha)'},
}


class TTSGenerator:
    """Generates voiceover audio using Edge-TTS"""
    
    def __init__(self, voice: str = "en-US-GuyNeural", rate: float = 1.0):
        self.voice = voice
        self.rate = rate
        
        # Validate voice
        if voice not in AVAILABLE_VOICES:
            logger.warning(f"Voice '{voice}' not found, using default")
            self.voice = "en-US-GuyNeural"
    
    def _format_rate(self) -> str:
        """Format speech rate for Edge-TTS"""
        if self.rate == 1.0:
            return "+0%"
        elif self.rate > 1.0:
            percent = int((self.rate - 1) * 100)
            return f"+{percent}%"
        else:
            percent = int((1 - self.rate) * 100)
            return f"-{percent}%"
    
    async def _generate_audio_async(self, text: str, output_path: str) -> dict:
        """Async method to generate audio"""
        rate = self._format_rate()
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=rate
        )
        
        # Generate audio
        await communicate.save(output_path)
        
        # Get file info
        file_size = os.path.getsize(output_path)
        
        return {
            'audio_path': output_path,
            'file_size': file_size,
            'voice': self.voice,
            'rate': self.rate
        }
    
    async def generate(self, text: str, output_path: str) -> dict:
        """
        Generate voiceover audio from text
        
        Args:
            text: The script text to convert to speech
            output_path: Path to save the audio file (MP3)
        
        Returns:
            dict with 'audio_path', 'file_size', 'voice', 'rate'
        """
        logger.info(f"Generating voiceover with voice: {self.voice}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Check if we should segment (simple heuristic: if it has multiple newlines)
        if text.count('\n') > 1:
            return await self._generate_segmented(text, output_path)
        
        logger.info(f"Text length: {len(text)} characters")
        
        # Run async generation directly
        result = await self._generate_audio_async(text, output_path)
        
        logger.info(f"Audio saved to: {output_path}")
        logger.info(f"File size: {result['file_size'] / 1024:.1f} KB")
        
        return result
    
    async def _generate_segmented(self, text: str, output_path: str) -> dict:
        """Generate audio in segments (per paragraph)"""
        logger.info("Generating segmented audio...")
        
        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        if not paragraphs:
            raise ValueError("Empty script")
            
        logger.info(f"Found {len(paragraphs)} paragraphs")
        
        if not paragraphs:
            raise ValueError("Empty script")
            
        logger.info(f"Found {len(paragraphs)} paragraphs")
        
        # Create temp dir for segments (Manual creation to control cleanup on Windows)
        temp_dir = tempfile.mkdtemp()
        segments = []
        audio_clips = []
        
        try:
            for i, paragraph in enumerate(paragraphs):
                # Sanitize paragraph for path (just use index)
                seg_path = os.path.join(temp_dir, f"seg_{i:03d}.mp3")
                
                # Generate audio for this segment
                try:
                    await self._generate_audio_async(paragraph, seg_path)
                except Exception as e:
                    logger.warning(f"Failed to generate audio for segment {i}: {e}")
                    # Create a silent dummy file or skip? 
                    # If we skip, sync will be partial. Let's try to proceed.
                    continue
                
                # Load clip to get duration
                try:
                    clip = AudioFileClip(seg_path)
                    duration = clip.duration
                    
                    segments.append({
                        'text': paragraph,
                        'audio_path': seg_path, # This path is temporary!
                        'duration': duration,
                        'index': i
                    })
                    
                    audio_clips.append(clip)
                except Exception as e:
                    logger.error(f"Failed to process segment {i}: {e}")
            
            if not audio_clips:
                raise RuntimeError("Failed to generate any audio segments")
            
            # Concatenate all clips
            final_audio = concatenate_audioclips(audio_clips)
            
            # Save final audio
            final_audio.write_audiofile(output_path, logger=None)
            
            # Close main composite clip
            final_audio.close()
            
            # Calculate offsets for segments
            current_offset = 0.0
            for seg in segments:
                seg['offset'] = current_offset
                current_offset += seg['duration']
                # Remove temporary path from result since it will be deleted
                del seg['audio_path']
                
        except Exception as e:
            logger.error(f"Error during segmented audio generation: {e}")
            raise
            
        finally:
            # explicit close of all clips to release file handles
            for clip in audio_clips:
                try:
                    clip.close()
                    # Force delete object to help GC (Video/AudioFileClip can be sticky)
                    del clip
                except:
                    pass
            
            # Clean up temp dir
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Could not delete temp dir {temp_dir}: {e}")
        
        file_size = os.path.getsize(output_path)
        
        return {
            'audio_path': output_path,
            'file_size': file_size,
            'voice': self.voice,
            'rate': self.rate,
            'segments': segments
        }
        
        file_size = os.path.getsize(output_path)
        
        return {
            'audio_path': output_path,
            'file_size': file_size,
            'voice': self.voice,
            'rate': self.rate,
            'segments': segments
        }

    async def generate_from_file(self, script_path: str, output_path: str = None) -> dict:
        """
        Generate voiceover from a script file
        
        Args:
            script_path: Path to the script text file
            output_path: Path to save audio (default: same dir as script)
        
        Returns:
            dict with audio info
        """
        # Read script
        with open(script_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # Default output path
        if not output_path:
            script_dir = os.path.dirname(script_path)
            output_path = os.path.join(script_dir, "voiceover.mp3")
        
        return await self.generate(text, output_path)

    async def generate_sync_audio(self, segments: list, output_dir: str) -> list:
        """
        Generate audio for each script segment independently for perfect sync.
        Uses parallel execution with a semaphore to speed up generation.
        """
        os.makedirs(output_dir, exist_ok=True)
        results = []
        
        # Limit concurrency to avoid rate limits or IP bans
        semaphore = asyncio.Semaphore(5)
        
        async def process_segment(i, segment):
            async with semaphore:
                text = segment.get('text', '').strip()
                if not text:
                    return None
                    
                idx = segment.get('batch_index', i)
                audio_path = os.path.join(output_dir, f"segment_{idx:03d}.mp3")
                
                try:
                    # Generate audio
                    await self._generate_audio_async(text, audio_path)
                    
                    # Get duration
                    clip = AudioFileClip(audio_path)
                    duration = clip.duration
                    clip.close()
                    del clip
                    
                    logger.info(f"Generated audio for segment {idx}: {duration:.1f}s")
                    return {
                        'audio_path': audio_path,
                        'duration': duration,
                        'batch_index': idx
                    }
                except Exception as e:
                    logger.error(f"Failed to generate audio for segment {idx}: {e}")
                    return None

        # Create tasks for all segments
        tasks = [process_segment(i, seg) for i, seg in enumerate(segments)]
        
        # Run tasks in parallel
        parallel_results = await asyncio.gather(*tasks)
        
        # Filter out None results and sort by index
        results = [r for r in parallel_results if r is not None]
        results.sort(key=lambda x: x['batch_index'])
        
        return results


async def generate_voiceover(script_path: str, output_path: str = None,
                       voice: str = "en-US-GuyNeural", rate: float = 1.0) -> dict:
    """Convenience function for generating voiceover"""
    generator = TTSGenerator(voice, rate)
    return await generator.generate_from_file(script_path, output_path)


def list_voices() -> dict:
    """Return available voices"""
    return AVAILABLE_VOICES


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
        voice = sys.argv[2] if len(sys.argv) > 2 else "en-US-GuyNeural"
        
        result = generate_voiceover(script_path, voice=voice)
        print(f"\nVoiceover generated!")
        print(f"Saved to: {result['audio_path']}")
        print(f"Size: {result['file_size'] / 1024:.1f} KB")
    else:
        print("Available voices:")
        for voice_id, info in AVAILABLE_VOICES.items():
            print(f"  {voice_id}: {info['description']}")
