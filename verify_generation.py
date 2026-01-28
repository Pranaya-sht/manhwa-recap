import google.generativeai as genai
import os
import json

def verify_generation():
    print("Verifying Gemini Model Generation...")
    
    # Load settings
    config_path = os.path.join("config", "settings.json")
    with open(config_path, 'r') as f:
        settings = json.load(f)
        api_keys = settings.get('gemini_api_keys', [])
        if not api_keys and 'gemini_api_key' in settings:
            api_keys = [settings['gemini_api_key']]
            
    if not api_keys:
        print("FAIL: No API keys found")
        return

    # Use first key
    api_key = api_keys[0]
    genai.configure(api_key=api_key)
    
    # Model to test
    model_name = "gemini-2.0-flash"
    print(f"Testing model: {model_name}")
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, can you hear me?")
        print(f"Response: {response.text}")
        print("SUCCESS: Generation worked!")
        return True
    except Exception as e:
        print(f"FAIL: Generation failed: {e}")
        return False

if __name__ == "__main__":
    verify_generation()
