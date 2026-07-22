"""
Test actual API connection with DEMO_MODE disabled
"""

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Temporarily override DEMO_MODE for testing
os.environ["DEMO_MODE"] = "false"

print("Testing Gemini API with actual API key...")
print(f"API Key: {os.getenv('GEMINI_API_KEY')[:10]}...")
print(f"Model: {os.getenv('GEMINI_MODEL')}")
print()

try:
    from google import genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    print(f"Initializing client with API key: {api_key[:10]}...")
    client = genai.Client(api_key=api_key)
    print("✓ Client initialized")
    
    print("\nListing available models...")
    try:
        models_list = list(client.models.list())
        print(f"✓ Successfully retrieved {len(models_list)} models")
        print("\nAvailable models:")
        for model_info in models_list:
            print(f"  - {model_info.name}")
        
        print(f"\n\nConfigured model: {model_name}")
        
        # Check if model exists
        available_names = [m.name for m in models_list]
        model_found = any(model_name in name or f"models/{model_name}" == name for name in available_names)
        
        if model_found:
            print(f"✓ Model '{model_name}' is available!")
        else:
            print(f"✗ Model '{model_name}' NOT FOUND in available models")
            print("\nSuggested fix:")
            print("  Update GEMINI_MODEL in .env to one of:")
            for m in models_list[:5]:  # Show first 5
                simple_name = m.name.replace("models/", "")
                print(f"    - {simple_name}")
                
    except Exception as e:
        print(f"✗ Error listing models: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
    print("\n\nTesting simple generation with configured model...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Hello' in JSON format with a 'message' field",
            config={"response_mime_type": "application/json"}
        )
        print(f"✓ Generation successful!")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"✗ Fatal error: {e}")
    import traceback
    traceback.print_exc()
