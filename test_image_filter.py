"""Test the image filter module"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.image_filter import ImageFilter

def test_filter():
    images_dir = "temp/The Extras Academy Survival Guide 225Abb58/chapter_83/images"
    config_path = "config/settings.json"
    
    if not os.path.exists(images_dir):
        print(f"Images directory not found: {images_dir}")
        return
    
    print(f"Testing image filter on: {images_dir}")
    
    try:
        filter_instance = ImageFilter(config_path=config_path)
        result = filter_instance.filter_images(images_dir)
        
        print(f"\nResults:")
        print(f"  Total images: {result['total_images']}")
        print(f"  Selected: {result['selected_count']}")
        print(f"  Reduction: {100 - (result['selected_count'] / result['total_images'] * 100):.1f}%")
        
        # Show first 10 selected
        print(f"\nFirst 10 selected images:")
        for path in result['selected_images'][:10]:
            print(f"  - {os.path.basename(path)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_filter()
