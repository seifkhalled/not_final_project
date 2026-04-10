#!/usr/bin/env python3
"""
Simple script to test OpenRouter models for trip generation.
Run this to see which models work with your API key.
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

def test_openrouter_models():
    """Test different OpenRouter models"""
    print("=" * 60)
    print("Testing OpenRouter Models for Egypt Trip Generation")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Get OpenRouter API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    print(f"OpenRouter API Key found: {api_key is not None}")
    if api_key:
        print(f"API Key (first 10 chars): {api_key[:10]}...")
    else:
        print("ERROR: OPENROUTER_API_KEY not found in environment variables")
        return
    
    # Initialize OpenRouter client
    base_url = "https://openrouter.ai/api/v1"
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        extra_headers={
            "HTTP-Referer": "https://egypt-trip-planner.com",
            "X-Title": "Egypt Trip Planner Test"
        }
    )
    
    # Define test parameters for a simple trip request
    test_prompt = """Create a 2-day trip plan for Cairo & Giza, Egypt with budget 1500 EGP for 2 people.
    
Include:
- Day 1: Visit Pyramids of Giza
- Day 2: Visit Egyptian Museum

Provide overview and budget breakdown."""

    # Models to test (from your suggestions)
    models_to_test = [
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "arcee-ai/trinity-large-preview:free", 
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-nano-30b-a3b:free"  # Current default
    ]
    
    results = []
    
    for model in models_to_test:
        print(f"\n{'-'*60}")
        print(f"Testing model: {model}")
        print(f"{'-'*60}")
        
        try:
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert Egypt travel planner. Create concise, practical trip plans."},
                    {"role": "user", "content": test_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            content = response.choices[0].message.content
            usage = response.usage
            
            print(f"✅ SUCCESS!")
            print(f"   Response time: {response_time:.2f} seconds")
            print(f"   Tokens - Input: {usage.prompt_tokens}, Output: {usage.completion_tokens}, Total: {usage.total_tokens}")
            print(f"   Response preview: {content[:150]}...")
            
            results.append({
                "model": model,
                "status": "SUCCESS",
                "response_time": response_time,
                "tokens_used": usage.total_tokens,
                "response_preview": content[:150]
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            results.append({
                "model": model,
                "status": "FAILED",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    successful_models = []
    for result in results:
        if result['status'] == 'SUCCESS':
            print(f"✅ {result['model']}")
            print(f"   Time: {result['response_time']:.2f}s | Tokens: {result['tokens_used']}")
            successful_models.append(result['model'])
        else:
            print(f"❌ {result['model']}")
            print(f"   Error: {result['error'][:100]}...")
        print()
    
    if successful_models:
        print(f"🎉 {len(successful_models)} model(s) worked successfully!")
        print(f"Recommended model for .env: OPENROUTER_MODEL=\"{successful_models[0]}\"")
    else:
        print("❌ No models worked. Check your API key and internet connection.")
    
    return results

if __name__ == "__main__":
    test_openrouter_models()