"""
Diagnostic script to verify environment configuration and Gemini API setup.
Run this from the backend directory to check your configuration.
"""

import os
import sys
from pathlib import Path

# Step 1: Print current working directory
print("=" * 80)
print("STEP 1: CURRENT WORKING DIRECTORY")
print("=" * 80)
print(f"Current Working Directory: {os.getcwd()}")
print(f"Script Location: {os.path.abspath(__file__)}")
print()

# Step 2: Load dotenv and check if .env file exists
print("=" * 80)
print("STEP 2: ENVIRONMENT FILE DETECTION")
print("=" * 80)

backend_dir = Path(__file__).parent
env_file = backend_dir / ".env"
print(f"Expected .env location: {env_file}")
print(f".env file exists: {env_file.exists()}")

if env_file.exists():
    print(f".env file size: {env_file.stat().st_size} bytes")
    print("\n.env file contents (with sensitive data masked):")
    print("-" * 80)
    with open(env_file, 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.strip() and not line.strip().startswith('#'):
                if 'API_KEY' in line:
                    key, _, value = line.partition('=')
                    masked_value = value[:8] + '...' if len(value) > 8 else '***'
                    print(f"{key}={masked_value}")
                else:
                    print(line)
            elif line.strip():
                print(line)
    print("-" * 80)
else:
    print("ERROR: .env file not found!")
print()

# Step 3: Load environment variables
print("=" * 80)
print("STEP 3: LOADING ENVIRONMENT VARIABLES")
print("=" * 80)

from dotenv import load_dotenv
result = load_dotenv(dotenv_path=env_file, override=True, verbose=True)
print(f"load_dotenv() returned: {result}")
print()

# Step 4: Check environment variables
print("=" * 80)
print("STEP 4: ENVIRONMENT VARIABLES CHECK")
print("=" * 80)

demo_mode = os.getenv("DEMO_MODE")
api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")
db_url = os.getenv("DATABASE_URL")

print(f"DEMO_MODE: {demo_mode}")
print(f"DEMO_MODE (boolean evaluation): {demo_mode.lower() == 'true' if demo_mode else False}")
print(f"GEMINI_API_KEY present: {api_key is not None}")
print(f"GEMINI_API_KEY first 8 chars: {api_key[:8] if api_key else 'NOT SET'}")
print(f"GEMINI_API_KEY length: {len(api_key) if api_key else 0}")
print(f"GEMINI_MODEL: {model}")
print(f"DATABASE_URL: {db_url}")
print()

# Step 5: Check if API key format looks valid
print("=" * 80)
print("STEP 5: API KEY FORMAT VALIDATION")
print("=" * 80)

if api_key:
    print(f"API Key starts with: {api_key[:10]}...")
    print(f"API Key length: {len(api_key)} characters")
    
    # Google AI Studio keys typically start with "AI" (not "AQ")
    if api_key.startswith("AI"):
        print("✓ API key format looks correct (Google AI Studio format)")
    else:
        print(f"⚠ WARNING: API key starts with '{api_key[:2]}' - Google AI Studio keys typically start with 'AI'")
        print("  This might be a Google Cloud API key or invalid key format")
else:
    print("✗ ERROR: No API key found!")
print()

# Step 6: Check installed packages
print("=" * 80)
print("STEP 6: INSTALLED PACKAGE VERSIONS")
print("=" * 80)

try:
    import google.genai as genai
    print(f"✓ google-genai installed")
    print(f"  Version: {genai.__version__ if hasattr(genai, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"✗ google-genai not installed: {e}")

try:
    import dotenv
    print(f"✓ python-dotenv installed")
    print(f"  Version: {dotenv.__version__ if hasattr(dotenv, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"✗ python-dotenv not installed: {e}")

try:
    import fastapi
    print(f"✓ fastapi installed")
    print(f"  Version: {fastapi.__version__}")
except ImportError as e:
    print(f"✗ fastapi not installed: {e}")

print()

# Step 7: Test Gemini API connection
print("=" * 80)
print("STEP 7: GEMINI API CONNECTION TEST")
print("=" * 80)

if demo_mode and demo_mode.lower() == "true":
    print("⚠ DEMO_MODE is enabled - API calls will return mock data")
    print("  To test real API, set DEMO_MODE=false in .env")
else:
    if api_key:
        try:
            from google import genai
            print("Attempting to initialize Gemini client...")
            client = genai.Client(api_key=api_key)
            print("✓ Client initialized successfully")
            
            print("\nAttempting to list available models...")
            try:
                models = client.models.list()
                print("✓ Successfully connected to Gemini API")
                print("\nAvailable models:")
                for model_info in models:
                    print(f"  - {model_info.name}")
                
                print(f"\n⚠ Your configured model: {model}")
                if model:
                    # Check if configured model is in available models
                    available_model_names = [m.name for m in models]
                    # Model names might be returned as "models/gemini-..." so check both formats
                    model_found = any(
                        model in name or f"models/{model}" == name 
                        for name in available_model_names
                    )
                    if model_found:
                        print(f"✓ Configured model IS available")
                    else:
                        print(f"✗ Configured model NOT found in available models!")
                        print(f"  Recommended: Use one of the models listed above")
                        
            except Exception as e:
                print(f"✗ Error listing models: {e}")
                print(f"  Error type: {type(e).__name__}")
                
        except Exception as e:
            print(f"✗ Error initializing client: {e}")
            print(f"  Error type: {type(e).__name__}")
    else:
        print("✗ Cannot test API - no API key configured")

print()

# Step 8: Summary and recommendations
print("=" * 80)
print("STEP 8: SUMMARY AND RECOMMENDATIONS")
print("=" * 80)

issues_found = []
recommendations = []

if not env_file.exists():
    issues_found.append("No .env file found")
    recommendations.append("Create .env file in backend directory")

if not api_key:
    issues_found.append("GEMINI_API_KEY not set")
    recommendations.append("Set GEMINI_API_KEY in .env file")
elif not api_key.startswith("AI"):
    issues_found.append(f"API key format suspicious (starts with '{api_key[:2]}')")
    recommendations.append("Verify you're using a Google AI Studio API key (should start with 'AI')")

if demo_mode and demo_mode.lower() == "true":
    issues_found.append("DEMO_MODE is enabled")
    recommendations.append("Set DEMO_MODE=false to use real API")

if not model:
    issues_found.append("GEMINI_MODEL not set")
    recommendations.append("Set GEMINI_MODEL in .env (default: gemini-1.5-flash)")

if issues_found:
    print("Issues found:")
    for i, issue in enumerate(issues_found, 1):
        print(f"  {i}. {issue}")
    print("\nRecommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
else:
    print("✓ No major issues detected!")

print("=" * 80)
