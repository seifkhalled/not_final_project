import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# In-memory cache: key = "place_name|destination"
_image_cache: dict = {}


def fetch_pexels_photos(query: str, per_page: int = 1):
    """Fetch photos from Pexels API based on search query."""
    if not PEXELS_API_KEY:
        logger.warning("[Pexels] No PEXELS_API_KEY found in .env - image search disabled")
        return []

    try:
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": per_page}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"[Pexels] API error: {response.status_code}")
            return []

        data = response.json()
        return data.get("photos", [])

    except Exception as e:
        logger.error(f"[Pexels] Error fetching photos: {e}")
        return []


def get_place_image_url(place_name: str, destination: str = "") -> str | None:
    """Get a single photo URL for a place, with in-memory caching."""
    if not PEXELS_API_KEY:
        return None

    cache_key = f"{place_name}|{destination}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    try:
        search_query = f"{place_name} {destination} Egypt".strip()
        photos = fetch_pexels_photos(search_query, 1)

        result = None
        if photos and len(photos) > 0 and "src" in photos[0]:
            result = photos[0]["src"].get("medium")

        _image_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"[Pexels] Error getting place image URL: {e}")
        _image_cache[cache_key] = None
        return None