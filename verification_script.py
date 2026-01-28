import os
import sys
from PIL import Image
from app.script_generator import generate_script

# Ensure temp directory exists
os.makedirs("temp_test/test_chapter", exist_ok=True)

# Create a dummy image
img = Image.new('RGB', (100, 100), color = 'red')
img.save('temp_test/test_chapter/image1.jpg')

print("Starting verification of script generation...")
try:
    # Use the first key from settings
    # You might need to adjust this depending on how your env is set up
    # but the script generator loads from config/settings.json by default if no keys provided
    # However, script_generator.py line 304 takes keys from argv or config.
    # Let's try calling it via the convenience function which loads from config if not provided.
    
    # We need to make sure config/settings.json exists and has keys. 
    # It does based on previous reads.
    
    result = generate_script(
        images_dir=os.path.abspath("temp_test/test_chapter"),
        manga_name="Test Manga",
        chapter="1",
        config_path=os.path.abspath("config/settings.json")
    )
    
    if result and 'script' in result and len(result['script']) > 0:
        print("SUCCESS: Script generated successfully!")
        print(f"Script length: {len(result['script'])}")
    else:
        print("FAILURE: Script generated but was empty.")

except Exception as e:
    print(f"FAILURE: An error occurred: {e}")
    # Print traceback
    import traceback
    traceback.print_exc()

# Clean up
try:
    import shutil
    shutil.rmtree("temp_test")
except:
    pass
