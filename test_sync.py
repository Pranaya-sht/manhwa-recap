
import os
import shutil
from app.tts_generator import TTSGenerator
from app.video_editor import VideoEditor
import asyncio
from PIL import Image

async def test_sync_logic():
    print("Testing Sync Logic...")
    
    # Setup dummy data
    test_dir = "temp_test_sync"
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Dummy Images
    images_dir = os.path.join(test_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Create 5 images
    for i in range(5):
        img = Image.new('RGB', (100, 100), color=(i*50, 0, 0))
        img.save(os.path.join(images_dir, f"img_{i:03d}.jpg"))
        
    print(f"Created 5 dummy images in {images_dir}")
    
    # 2. Dummy Script (3 paragraphs)
    # Para 1: Short
    # Para 2: Long
    # Para 3: Short
    script = """This is a short paragraph.
    
    This is a significantly longer paragraph that should take more time to read and thus should display more images or hold onto images for longer duration during the video generation process.
    
    Ending short."""
    
    # 3. Generate Audio with Segments
    tts = TTSGenerator()
    # Mocking _generate_audio_async or just running it if API key/edge-tts is reliable?
    # edge-tts is free and no key needed, so we can run it.
    
    audio_path = os.path.join(test_dir, "test_audio.mp3")
    print("Generating segmented audio...")
    try:
        result = await tts.generate(script, audio_path)
        
        if 'segments' not in result:
            print("FAILED: No segments returned!")
            return
            
        segments = result['segments']
        print(f"Got {len(segments)} segments")
        for seg in segments:
            print(f"  Seg {seg['index']}: {seg['duration']:.2f}s - {seg['text'][:20]}...")
            
    except Exception as e:
        print(f"TTS Failed (network?): {e}")
        # Create dummy segments if TTS fails (offline mode)
        segments = [
            {'duration': 2.0, 'text': "Short", 'index': 0},
            {'duration': 5.0, 'text': "Long", 'index': 1},
            {'duration': 2.0, 'text': "Short", 'index': 2}
        ]
        # Create dummy audio file
        with open(audio_path, 'wb') as f:
            f.write(b'\0' * 1000)
    
    # 4. Create Video with Sync
    editor = VideoEditor({'video_resolution': [100, 100]}) # Small res for speed
    output_video = os.path.join(test_dir, "output.mp4")
    
    print("Creating video...")
    try:
        # We need a real audio file for moviepy to read, 
        # checking if the one we made is valid or dummy
        if os.path.getsize(audio_path) < 100:
             print("Skipping real video render due to dummy audio")
        else:
            result = editor.create_video(
                images_dir,
                audio_path,
                output_video,
                audio_segments=segments
            )
            print("Video created successfully!")
            print(f"Output: {result['video_path']}")
            print(f"Duration: {result['duration']}")
            
    except Exception as e:
        print(f"Video creation failed: {e}")
        
    # Cleanup
    # shutil.rmtree(test_dir)

if __name__ == "__main__":
    asyncio.run(test_sync_logic())
