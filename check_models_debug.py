
import google.generativeai as genai
import os
import json

def list_models_to_file():
    print("Listing available Gemini models to models_list.txt...")
    
    # Load key from settings
    try:
        with open(os.path.join("config", "settings.json"), 'r') as f:
            settings = json.load(f)
            # Try specific key first, then list
            api_key = settings.get('gemini_api_key')
            if not api_key and settings.get('gemini_api_keys'):
                api_key = settings.get('gemini_api_keys')[0]
    except Exception as e:
        print(f"Could not load settings: {e}")
        return

    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        
        with open("models_list.txt", "w") as f:
            for m in models:
                f.write(f"{m}\n")
        
        print(f"Successfully wrote {len(models)} models to models_list.txt")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models_to_file()
