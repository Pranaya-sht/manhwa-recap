
import sys
import os
sys.path.append(os.getcwd())

print("Testing imports...")
try:
    from app.video_editor import VideoEditor
    print("VideoEditor imported successfully")
except Exception as e:
    print(f"VideoEditor import failed: {e}")

try:
    from app.script_generator import ScriptGenerator
    print("ScriptGenerator imported successfully")
except Exception as e:
    print(f"ScriptGenerator import failed: {e}")

try:
    from app.main import app
    print("Main app imported successfully")
except Exception as e:
    print(f"Main app import failed: {e}")
