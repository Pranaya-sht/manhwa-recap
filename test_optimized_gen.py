
import os
import json
from app.script_generator import ScriptGenerator

def test_optimization_config():
    print("Testing Script Generator Optimization Config...")
    
    # 1. Check Settings File
    config_path = os.path.join("config", "settings.json")
    with open(config_path, 'r') as f:
        settings = json.load(f)
        
    print(f"Settings loaded: Batch Size={settings.get('generation_batch_size')}, Delay={settings.get('generation_delay')}")
    
    if settings.get('generation_batch_size') != 8:
        print("FAIL: Batch size not updated in settings.json ")
        return
        
    # 2. Check Generator Initialization
    # We need at least one key to init
    # We can trust the settings file has keys
    try:
        generator = ScriptGenerator(config_path=config_path)
        
        # Verify Model Order
        print(f"Model Priority: {generator.models}")
        if generator.models[0] != 'gemini-2.0-flash':
             print("FAIL: Model priority not updated (expected gemini-2.0-flash first)")
             return
             
        # Verify Config Loading
        gen_batch = generator.config.get('generation_batch_size')
        gen_delay = generator.config.get('generation_delay')
        
        print(f"Generator Config: Batch={gen_batch}, Delay={gen_delay}")
        
        if gen_batch == 8 and gen_delay == 5:
            print("SUCCESS: Configuration correctly loaded!")
        else:
            print("FAIL: Generator did not load correct config values")

    except Exception as e:
        print(f"Initialization Failed: {e}")

if __name__ == "__main__":
    test_optimization_config()
