import google.generativeai as genai
import os

# Use the first key from the top of the list in settings.json
# "AIzaSyDFtekIH_XfqS9X0pnEWgeZ42R8piUgy-Y"
key = "AIzaSyDFtekIH_XfqS9X0pnEWgeZ42R8piUgy-Y"

genai.configure(api_key=key)

print("Listing available models...")
with open("models_list.txt", "w") as f:
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                f.write(f"{m.name}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
