import { PexelsResponse, PexelsPhoto } from '@/types/pexels';

const PEXELS_API_KEY = process.env.NEXT_PUBLIC_PEXELS_API_KEY;

if (!PEXELS_API_KEY) {
  console.warn('PEXELS_API_KEY is not set in environment variables');
}

/**
 * Fetch photos from Pexels API based on search query
 */
export async function fetchPexelsPhotos(query: string, perPage = 1): Promise<PexelsPhoto[]> {
  if (!PEXELS_API_KEY) {
    // Return empty array if no API key
    return [];
  }

  try {
    const response = await fetch(
      `https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&per_page=${perPage}`,
      {
        headers: {
          Authorization: PEXELS_API_KEY,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Pexels API error: ${response.status}`);
    }

    const data: PexelsResponse = await response.json();
    return data.photos;
  } catch (error) {
    console.error('Error fetching from Pexels:', error);
    return [];
  }
}

/**
 * Get a single photo URL for a place
 */
export async function getPlaceImageUrl(placeName: string, destination: string = ''): Promise<string> {
  if (!PEXELS_API_KEY) {
    // Fallback to Unsplash if no Pexels key
    const searchQuery = encodeURIComponent(`${placeName} ${destination} Egypt`.trim());
    return `https://source.unsplash.com/600x400/?${searchQuery}`;
  }

  try {
    const searchQuery = `${placeName} ${destination} Egypt`.trim();
    const photos = await fetchPexelsPhotos(searchQuery, 1);
    
    if (photos.length > 0 && photos[0].src?.medium) {
      return photos[0].src.medium;
    }
    
    // Fallback to Unsplash if no results
    const fallbackQuery = encodeURIComponent(`${placeName} ${destination} Egypt`.trim());
    return `https://source.unsplash.com/600x400/?${fallbackQuery}`;
  } catch (error) {
    console.error('Error getting place image URL:', error);
    // Fallback to Unsplash on error
    const fallbackQuery = encodeURIComponent(`${placeName} ${destination} Egypt`.trim());
    return `https://source.unsplash.com/600x400/?${fallbackQuery}`;
  }
}