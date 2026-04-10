import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from pexels_service import get_place_image_url

load_dotenv()

def test_pexels():
    test_cases = [
        ("The Great Pyramids", "Cairo"),
        ("Khan el-Khalili", "Cairo"),
        ("Karnak Temple", "Luxor")
    ]
    
    for name, city in test_cases:
        url = get_place_image_url(name, city)
        print(f"Name: {name}, City: {city} -> URL: {url}")

if __name__ == "__main__":
    test_pexels()
