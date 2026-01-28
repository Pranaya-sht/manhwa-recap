
import os
import json
import google.generativeai as genai

def list_models():
    # Load config to get a key
    config_path = "config/settings.json"
    api_key = None
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            if config.get('gemini_api_keys'):
                api_key = config['gemini_api_keys'][0]
            elif config.get('gemini_api_key'):
                api_key = config['gemini_api_key']
    
    if not api_key:
        print("No API key found in config/settings.json")
        return

    print(f"Using API Key: {api_key[:5]}...")
    genai.configure(api_key=api_key)

    print("\nListing available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
