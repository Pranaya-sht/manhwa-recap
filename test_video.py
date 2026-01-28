from app.video_editor import VideoEditor
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)

# Paths
base_dir = r"c:\Users\prana\OneDrive\Desktop\manhwa recap\temp\The Extras Academy Survival Guide 225Abb58\chapter_83"
images_dir = os.path.join(base_dir, "images")
audio_path = os.path.join(base_dir, "voiceover.mp3")
output_path = "test_output.mp4"

config = {
    'video_resolution': [1920, 1080],
    'video_fps': 30,
    'transition_duration': 0.5,
    'ken_burns_enabled': True
}

print("Starting video test...")
try:
    editor = VideoEditor(config)
    result = editor.create_video(
        images_dir=images_dir,
        audio_path=audio_path,
        output_path=output_path,
        manga_name="Test Manga",
        chapter="1"
    )
    print("Success!")
except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
