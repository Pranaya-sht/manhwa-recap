
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

try:
    from app.script_generator import ScriptGenerator
    print("Import successful")
    
    # Try instantiation with dummy key
    try:
        gen = ScriptGenerator(api_keys=["dummy_key"])
        print("Successfully instantiated ScriptGenerator")
        
        # Verify attribute exists
        if hasattr(gen, 'current_key_index'):
             print(f"current_key_index is {gen.current_key_index}")
        else:
             print("current_key_index is missing!")
             
    except Exception as e:
        print(f"Instantiation failed: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"Import failed: {e}")
