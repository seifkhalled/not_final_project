#!/usr/bin/env python3
"""
Test different OpenRouter models to find a working alternative
to the rate-limited google/gemma-4-31b-it:free model.
"""

import os
import sys
from dotenv import load_dotdev
from openai import OpenAI

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

def test_models():
    """Test various OpenRouter models for availability"""
    print("=" * 60)
    print("Testing OpenRouter Models for Availability")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found")
        return
    
    print("API Key loaded: " + api_key[:10] + "...")
    
    # Initialize client correctly for OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # Test prompt
    test_prompt = "Say 'Hello' in Arabic"
    
    # Models to test (your suggestions + current)
    models_to_test = [
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "arcee-ai/trinity-large-preview:free", 
        "stepfun/step-3.5-flash:free",
        "google/gemma-4-31b-it:free",  # Currently rate-limited
        "mistralai/mistral-7b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "qwen/qwen3-next-80b-a3b-instruct:free"
    ]
    
    working_models = []
    
    for model in models_to_test:
        print("\nTesting: " + model)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=20,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            print("  SUCCESS: " + content)
            working_models.append(model)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate-limited" in error_msg.lower():
                print("  RATE LIMITED: " + error_msg[:100] + "...")
            else:
                print("  ERROR: " + error_msg[:100] + "...")
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if working_models:
        print(str(len(working_models)) + " model(s) working:")
        for model in working_models:
            marker = " (CURRENT)" if model == "google/gemma-4-31b-it:free" else ""
            print("   • " + model + marker)
        
        # Recommend the first working model from your preferred list
        preferred_order = [
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "arcee-ai/trinity-large-preview:free", 
            "stepfun/step-3.5-flash:free"
        ]
        
        recommended = None
        for model in preferred_order:
            if model in working_models:
                recommended = model
                break
        
        if not recommended:
            recommended = working_models[0]  # Fallback to first working
        
        print("\nRECOMMENDED for .env:")
        print("   OPENROUTER_MODEL=\"" + recommended + "\"")
        
        # Show how to update .env
        print("\nTo update your .env file:")
        print("   sed -i 's/OPENROUTER_MODEL=.*/OPENROUTER_MODEL=\"{recommended}\"/' .env".format(recommended=recommended))
        
    else:
        print("No models are currently working")
        print("   Please check your API key and try again later")
    
    return working_models

if __name__ == "__main__":
    test_models()