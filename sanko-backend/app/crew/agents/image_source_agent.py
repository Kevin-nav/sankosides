"""
Image Source Agent

Dedicated agent for generating and sourcing images for slides.
Uses AI-first strategy with Gemini 3 Pro Image for consistent,
watermark-free, high-quality images.

Pipeline (AI-First):
1. Check semantic cache (same description = same image)
2. Generate with Gemini 3 Pro Image
3. Upload to R2 and cache
4. Optional: Fall back to search if generation fails and fallback enabled
"""

import hashlib
import logging
from typing import Optional, Dict
from pydantic import BaseModel, Field

from app.crew.tools.image_generation_tool import NanoBananaImageTool, GeneratedAsset
from app.models.schemas import ImageCitation
from app.core.logging import get_logger
from app.services.cache import RedisCache

logger = get_logger(__name__)


# Style presets for different presentation contexts
STYLE_PRESETS = {
    "academic": "professional, clean, educational illustration, suitable for academic presentation, no text overlays, modern design",
    "corporate": "professional, business-appropriate, clean lines, corporate color palette, modern and polished",
    "creative": "vibrant, artistic, creative illustration, modern design, visually engaging",
    "minimal": "minimalist, clean, simple composition, lots of whitespace, subtle colors",
    "technical": "technical diagram style, clean lines, informative, engineering aesthetic",
    "default": "professional, high quality, clean composition, suitable for presentation slides",
}


class ImageSourceResult(BaseModel):
    """Result from the image sourcing process."""
    image_url: str = Field(..., description="URL of the sourced image")
    image_alt: str = Field(..., description="Alt text describing the image")
    image_caption: Optional[str] = Field(None, description="Caption for the image")
    citation: ImageCitation = Field(..., description="Citation metadata for attribution")
    verification_score: float = Field(default=1.0, ge=0.0, le=1.0)
    source_method: str = Field(..., description="How image was sourced: 'generated', 'search', 'cached', 'placeholder'")
    

class ImageSourceAgent:
    """
    AI-First Image Source Agent.
    
    Strategy:
    1. Check cache for existing image with same description
    2. Generate with Gemini 3 Pro Image (default)
    3. Cache result for reuse
    4. Optional: Fall back to search if needed
    
    Benefits:
    - No 404 errors from broken external URLs
    - No watermarks
    - Consistent visual style
    - Fast (cached images are instant)
    """

    REDIS_TTL_SECONDS = 3 * 24 * 3600
    
    def __init__(self, output_dir: str = "./generated_assets"):
        """
        Initialize the Image Source Agent.
        
        Args:
            output_dir: Directory for generated images (fallback if R2 fails)
        """
        self.generation_tool = NanoBananaImageTool(output_dir=output_dir)
        self._cache: Dict[str, ImageSourceResult] = {}
        self._initialized = True
    
    def _cache_key(self, description: str, style: str) -> str:
        """Generate cache key from description + style."""
        return hashlib.md5(f"{description}::{style}".encode()).hexdigest()
    
    async def find_image(
        self,
        query: str,
        slide_context: str = "",
        style: str = "default",
        allow_search_fallback: bool = False,
    ) -> ImageSourceResult:
        """
        Generate or find the best image for a slide.
        
        Args:
            query: What the image should depict (e.g., "neural network layers")
            slide_context: Additional context about the slide
            style: Style preset (academic, corporate, creative, minimal, technical, default)
            allow_search_fallback: Whether to try web search if generation fails
            
        Returns:
            ImageSourceResult with image URL and citation metadata
        """
        logger.info(f"[IMAGE AGENT] Generating image for: '{query}'")
        
        # Get style from presets or use as-is
        style_prompt = STYLE_PRESETS.get(style, style)
        
        # Build full description for caching
        full_description = f"{query} - {slide_context}".strip(" -") if slide_context else query
        
        # Check cache first (same description = same image)
        cache_key = self._cache_key(full_description, style)
        if cache_key in self._cache:
            logger.info(f"[IMAGE AGENT] Cache hit for: '{query}'")
            cached = self._cache[cache_key]
            # Return cached with updated source_method
            return ImageSourceResult(
                image_url=cached.image_url,
                image_alt=cached.image_alt,
                image_caption=cached.image_caption,
                citation=cached.citation,
                verification_score=cached.verification_score,
                source_method="cached",
            )

        # Shared cache (cross-session/workers)
        shared_cache_key = f"image_agent:{cache_key}"
        cached_shared = RedisCache.get(shared_cache_key)
        if cached_shared:
            logger.info(f"[IMAGE AGENT] Shared cache hit for: '{query}'")
            cached_result = ImageSourceResult(**cached_shared)
            self._cache[cache_key] = cached_result
            return ImageSourceResult(
                image_url=cached_result.image_url,
                image_alt=cached_result.image_alt,
                image_caption=cached_result.image_caption,
                citation=cached_result.citation,
                verification_score=cached_result.verification_score,
                source_method="cached",
            )
        
        # AI Generation (primary strategy)
        result = await self._generate_image(query, slide_context, style_prompt)
        
        # If generation failed and search fallback is allowed, try search
        if result.source_method == "placeholder" and allow_search_fallback:
            logger.info(f"[IMAGE AGENT] Generation failed, attempting search fallback...")
            search_result = await self._search_fallback(query, slide_context)
            if search_result:
                result = search_result
        
        # Cache and return
        self._cache[cache_key] = result
        RedisCache.set(shared_cache_key, result.model_dump(), ttl=self.REDIS_TTL_SECONDS)
        logger.info(f"[IMAGE AGENT] Cached result for: '{query}' (method: {result.source_method})")
        
        return result
    
    async def _generate_image(
        self,
        query: str,
        context: str,
        style_prompt: str,
    ) -> ImageSourceResult:
        """Generate an image using Gemini 3 Pro Image."""
        
        # Build optimized prompt
        prompt_parts = [
            f"Subject: {query}",
            f"Purpose: Professional presentation slide image",
        ]
        
        if context:
            prompt_parts.append(f"Context: {context}")
        
        prompt_parts.extend([
            "Requirements:",
            "- High resolution, suitable for projection",
            "- Clean composition with clear focal point",
            "- No text overlays or watermarks",
            "- Visually engaging but not distracting",
        ])
        
        full_prompt = "\n".join(prompt_parts)
        
        try:
            asset: GeneratedAsset = await self.generation_tool.generate_asset(
                prompt=full_prompt,
                style=style_prompt,
                upload_to_r2=True,  # Always upload to R2 for reliable URLs
            )
            
            if asset.success and asset.file_path:
                logger.info(f"[IMAGE AGENT] Generated image: {asset.file_path[:80]}...")
                
                # Determine URL
                if asset.file_path.startswith(("http://", "https://")):
                    image_url = asset.file_path
                else:
                    # Local path fallback
                    from pathlib import Path
                    logger.warning(f"[IMAGE AGENT] Image saved locally, not R2: {asset.file_path}")
                    image_url = Path(asset.file_path).resolve().as_uri()
                
                return ImageSourceResult(
                    image_url=image_url,
                    image_alt=f"AI-generated illustration: {query}",
                    image_caption=query,
                    citation=ImageCitation(
                        source_type="generated",
                        source_name="AI Generated",
                        license="Original creation",
                    ),
                    verification_score=1.0,  # AI images are always "relevant"
                    source_method="generated",
                )
            else:
                logger.warning(f"[IMAGE AGENT] Generation failed: {asset.error}")
                
        except Exception as e:
            logger.error(f"[IMAGE AGENT] Generation error: {e}")
        
        # Return placeholder on failure
        return ImageSourceResult(
            image_url="https://via.placeholder.com/1600x900/2563eb/ffffff?text=Image+Generation+Failed",
            image_alt=query,
            image_caption=query,
            citation=ImageCitation(source_type="original"),
            verification_score=0.0,
            source_method="placeholder",
        )
    
    async def _search_fallback(
        self,
        query: str,
        context: str,
    ) -> Optional[ImageSourceResult]:
        """
        Search for an image as fallback.
        
        This is only used when:
        1. AI generation fails
        2. allow_search_fallback=True
        
        Currently disabled by default in AI-first strategy.
        """
        try:
            # Lazy import to avoid loading search tools if not needed
            from app.crew.tools.image_search_tool import ImageSearchTool
            
            search_tool = ImageSearchTool()
            results = await search_tool.search_images(query, max_results=1)
            
            if results:
                img = results[0]
                logger.info(f"[IMAGE AGENT] Search found image from: {img.source}")
                
                return ImageSourceResult(
                    image_url=img.url,
                    image_alt=img.title or query,
                    image_caption=query,
                    citation=ImageCitation(
                        source_type="stock",
                        source_name=img.source or "Web",
                        license=img.license_info,
                        url=img.url,
                    ),
                    verification_score=0.5,  # Unverified search result
                    source_method="search",
                )
                
        except Exception as e:
            logger.warning(f"[IMAGE AGENT] Search fallback failed: {e}")
        
        return None
    
    def clear_cache(self):
        """Clear the session cache."""
        self._cache.clear()
        logger.info("[IMAGE AGENT] Cache cleared")
    
    async def close(self):
        """Cleanup resources."""
        logger.info("[IMAGE AGENT] Resources closed")
