import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def trigger_video_generation():
    # 1. Get Projects
    try:
        resp = requests.get(f"{BASE_URL}/api/projects")
        projects = resp.json()
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return

    if not projects:
        print("No projects found.")
        return

    # Find the target project
    target_project = None
    for p in projects:
        # Check matching name
        if "Extras Academy" in p.get('manga_name', '') or "225Abb58" in p.get('images_dir', ''):
            target_project = p
            break
            
    if not target_project:
        print("Target project not found. Available projects:")
        for p in projects:
            print(f"- {p.get('manga_name')} (ID: {p.get('id')})")
        # Fallback to the first one if only one exists
        if len(projects) == 1:
            target_project = projects[0]
            print(f"Using the only available project: {target_project.get('manga_name')}")
        else:
            return

    project_id = target_project['id']
    print(f"Found project: {target_project.get('manga_name')} (ID: {project_id})")
    
    # 2. Trigger Create Video
    # We set ken_burns=False explicitly for speed and "normal" view
    payload = {
        "project_id": project_id,
        "ken_burns": False,
        "transition_duration": 0.0 # Disable transitions
    }
    
    print("Triggering video creation (this includes image filtering)...")
    print("This may take some time. Check terminal for server logs.")
    
    try:
        # Increase timeout because filtering + rendering takes time
        resp = requests.post(f"{BASE_URL}/api/create-video", json=payload, timeout=300)
        
        if resp.status_code == 200:
            result = resp.json()
            print("\nSUCCESS! Video created.")
            print(f"Path: {result.get('video_path')}")
            print(f"Duration: {result.get('duration')}s")
        else:
            print(f"\nFAILED with status {resp.status_code}")
            print(resp.text)
            
    except requests.exceptions.Timeout:
        print("\nRequest timed out (server is likely still processing). Check the output folder later.")
    except Exception as e:
        print(f"\nError creating video: {e}")

if __name__ == "__main__":
    trigger_video_generation()
