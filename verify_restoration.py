# Test that the pipeline runs without the filter step
import requests
import time
import os
import shutil

BASE_URL = "http://127.0.0.1:8000"

def test_full_process():
    print("Testing Full Process (No Filter)...")
    
    # Use a dummy or easy URL (we might need to mock scrape or use a real stable one)
    # Using a known Asura Scans URL or similar
    url = "https://asuracomic.net/series/reaper-of-the-drifting-moon-362f0682/chapter/96"
    
    payload = {
        "url": url,
        "voice": "en-US-GuyNeural",
        "rate": 1.0,
        "ken_burns": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/process", json=payload)
        
        # We expect a background task to start, but the current API seems to run synchronously 
        # based on the implementation (except for the BackgroundTasks arg which might be unused in the snippet shown?)
        # Actually in the code `async def full_process(...)` awaits everything, so it's synchronous.
        # Wait, `background_tasks` is in the signature but `full_process` awaits steps.
        
        if response.status_code == 200:
            print("Process started/completed successfully!")
            data = response.json()
            print(f"Project ID: {data.get('project_id')}")
            print(f"Video Path: {data.get('video_path')}")
            return True
        else:
            print(f"Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_full_process()
