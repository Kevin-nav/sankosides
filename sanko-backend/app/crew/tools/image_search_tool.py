"""
Image Search Tool

Searches for images using multiple sources:
1. Primary: Unsplash (high-quality, free, no API key needed for basic)
2. Fallback: Google Search via Interactions API

This provides better image results than academic APIs which
may return generic or low-quality images.
"""

import httpx
from typing import Optional, List
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from app.config import settings


class ImageSearchResult(BaseModel):
    """A single image search result."""
    url: str = Field(..., description="Direct URL to the image")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL if available")
    title: str = Field(default="", description="Image title/alt text")
    source: str = Field(default="", description="Source website")
    width: Optional[int] = None
    height: Optional[int] = None
    license_info: Optional[str] = Field(None, description="License if known")


class ImageSearchTool:
    """
    Tool for searching images using multiple sources.
    
    Strategy:
    1. Try Unsplash first (high quality, free for commercial use)
    2. Fall back to Google Search via Gemini Interactions API
    
    The Planner agent uses this to find relevant images when
    academic sources don't have good visuals.
    """
    
    # Unsplash Source API (no key needed, limited features)
    UNSPLASH_SOURCE = "https://source.unsplash.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=self.api_key)
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def search_images(
        self,
        query: str,
        max_results: int = 5,
        size: str = "large",  # small, medium, large
    ) -> List[ImageSearchResult]:
        """
        Search for images matching the query.
        
        Args:
            query: Search query (e.g., "neural network diagram")
            max_results: Maximum number of results
            size: Preferred image size
            
        Returns:
            List of ImageSearchResult
        """
        results = []
        
        # Try Unsplash first (simple redirect-based API)
        unsplash_result = await self._get_unsplash_image(query)
        if unsplash_result:
            results.append(unsplash_result)
        
        # If we need more results, use Google Search via Interactions API
        if len(results) < max_results:
            google_results = await self._search_google_images(
                query, 
                max_results - len(results)
            )
            results.extend(google_results)
        
        return results[:max_results]
    
    async def _get_unsplash_image(self, query: str) -> Optional[ImageSearchResult]:
        """
        Get a high-quality image from Unsplash.
        
        Uses the Source API which is free but limited.
        Returns a single random image matching the query.
        """
        try:
            # Unsplash Source API returns a redirect to an image
            url = f"{self.UNSPLASH_SOURCE}/1600x900/?{query.replace(' ', ',')}"
            
            # Follow redirect to get actual image URL
            response = await self._http_client.head(url, follow_redirects=True)
            
            if response.status_code == 200:
                final_url = str(response.url)
                return ImageSearchResult(
                    url=final_url,
                    thumbnail_url=final_url.replace("1600x900", "400x225"),
                    title=f"Unsplash image: {query}",
                    source="unsplash.com",
                    width=1600,
                    height=900,
                    license_info="Unsplash License (free for commercial use)",
                )
        except Exception as e:
            print(f"Unsplash search failed: {e}")
        
        return None
    
    async def _search_google_images(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[ImageSearchResult]:
        """
        Search Google Images using Gemini Interactions API with google_search tool.
        
        The model uses Google Search natively and returns image results.
        """
        try:
            # Use Gemini to search Google for images
            prompt = f"""Search Google Images for: "{query}"

Find {max_results} high-quality, relevant images.

For each image found, provide:
1. The direct image URL
2. The source website
3. A brief description

Format as JSON array:
[
  {{"url": "...", "source": "...", "description": "..."}}
]

Only return images that are:
- High resolution (at least 800px wide)
- Relevant to the query
- From reputable sources"""

            # Call Gemini with google_search tool enabled
            response = self.client.models.generate_content(
                model=settings.model_flash,
                contents=[types.Content(
                    role="user",
                    parts=[types.Part(text=prompt)]
                )],
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    thinking_config=types.ThinkingConfig(
                        thinking_level=settings.thinking_level_low
                    )
                )
            )
            
            # Parse response
            import json
            import re
            
            response_text = response.text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            
            if json_match:
                images = json.loads(json_match.group())
                return [
                    ImageSearchResult(
                        url=img.get("url", ""),
                        title=img.get("description", ""),
                        source=img.get("source", "Google Search"),
                    )
                    for img in images
                    if img.get("url")
                ]
        
        except Exception as e:
            print(f"Google image search failed: {e}")
        
        return []
    
    async def get_image_for_concept(
        self,
        concept: str,
        context: str = "",
    ) -> Optional[ImageSearchResult]:
        """
        Get a single best image for a concept.
        
        This is a convenience method for the Planner agent.
        
        Args:
            concept: The concept to visualize (e.g., "machine learning")
            context: Additional context (e.g., "for academic presentation")
            
        Returns:
            Best matching ImageSearchResult or None
        """
        query = f"{concept} {context}".strip()
        results = await self.search_images(query, max_results=1)
        return results[0] if results else None
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
