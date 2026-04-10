import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://egypt-trip-planner.com",
        "X-Title": "Egypt Trip Planner"
    }
)

model = "nvidia/nemotron-3-nano-30b-a3b:free"

print(f"Testing model: {model}")

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a travel planner."},
            {"role": "user", "content": "Tell me a very long story about Egypt. " + "Egypt is great. " * 500}
        ],
        max_tokens=2500
    )
    print("Success!")
    print(response.choices[0].message.content[:100])
except Exception as e:
    print(f"Error occurred: {e}")
