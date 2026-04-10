import sys
sys.path.append('src')
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv('OPENROUTER_API_KEY')

if not api_key:
    print("ERROR: No OPENROUTER_API_KEY found")
    exit(1)

print("API Key loaded successfully")
print("Key preview:", api_key[:15] + "...")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

# Test these models (including the ones you mentioned)
models = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free", 
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "arcee-ai/trinity-large-preview:free",
    "stepfun/step-3.5-flash:free",
    "google/gemma-4-31b-it:free"
]

print("\nTesting models:")
print("-" * 50)

working = []
for model in models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("SUCCESS: " + model)
        working.append(model)
    except Exception as e:
        if "429" in str(e):
            print("RATE LIMITED: " + model)
        else:
            print("FAILED: " + model + " (" + str(e)[:50] + "...)")

print("\n" + "="*50)
print("SUMMARY")
print("="*50)

if working:
    print("Working models:")
    for model in working:
        print("  • " + model)
    
    # Recommend best option
    priority = [
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "arcee-ai/trinity-large-preview:free",
        "stepfun/step-3.5-flash:free"
    ]
    
    recommended = None
    for model in priority:
        if model in working:
            recommended = model
            break
    
    if not recommended:
        recommended = working[0]
    
    print("\nRECOMMENDED: " + recommended)
    print("Update your .env: OPENROUTER_MODEL=\"" + recommended + "\"")
else:
    print("ERROR: No models are currently working")
    print("Please check your API key or try again later")