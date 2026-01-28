
import google.generativeai as genai
import os
import json

def list_models():
    print("Listing available Gemini models...")
    
    # Load key from settings
    try:
        with open(os.path.join("config", "settings.json"), 'r') as f:
            settings = json.load(f)
            api_key = settings.get('gemini_api_key') or settings.get('gemini_api_keys')[0]
    except Exception as e:
        print(f"Could not load settings: {e}")
        return

    try:
        genai.configure(api_key=api_key)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
