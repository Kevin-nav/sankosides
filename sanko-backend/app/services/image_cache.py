"""
Image Cache Service

Tiered caching for downloaded images:
- Redis: 3-day hot cache for fast lookups
- R2: 14-day cold storage for persistent caching

Reduces external API calls and handles hotlink protection failures.
"""

import hashlib
from typing import Optional, Tuple
import httpx

from app.services.cache import RedisCache
from app.services.storage import get_storage_service
from app.core.logging import get_logger

logger = get_logger(__name__)


# Cache TTLs
REDIS_TTL = 3 * 24 * 3600  # 3 days in seconds
R2_CACHE_PREFIX = "image_cache/"

# Browser-like headers to bypass hotlink protection
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://google.com/",
    "DNT": "1",
}


class ImageCacheService:
    """
    Tiered image caching: Redis (hot) → R2 (cold).
    
    Lookup Flow:
    1. Check Redis (3-day cache) → hit? return R2 URL
    2. Check R2 existence → hit? promote to Redis, return URL
    3. Cache miss → caller should download and store
    
    Store Flow:
    1. Upload to R2 (cold storage, 14+ days)
    2. Store R2 URL in Redis (hot cache, 3 days)
    """
    
    @classmethod
    def _cache_key(cls, url: str) -> str:
        """Generate cache key from URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"img_cache:{url_hash}"
    
    @classmethod
    def _r2_key(cls, url: str) -> str:
        """Generate R2 storage key from URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{R2_CACHE_PREFIX}{url_hash}.jpg"
    
    @classmethod
    async def get(cls, url: str) -> Optional[str]:
        """
        Check cache for a previously downloaded image.
        
        Args:
            url: Original image URL
            
        Returns:
            R2 public URL if cached, None if not found
        """
        cache_key = cls._cache_key(url)
        
        # Check Redis first (hot cache)
        cached_url = RedisCache.get(cache_key)
        if cached_url:
            logger.debug(f"[IMAGE_CACHE] Redis hit for {url[:50]}...")
            return cached_url
        
        # Check R2 (cold cache)
        try:
            storage = get_storage_service()
            r2_key = cls._r2_key(url)
            
            # Check if file exists in R2
            exists = await storage.exists(r2_key)
            if exists:
                r2_url = storage.get_public_url(r2_key)
                if r2_url:
                    # Promote to Redis for faster future lookups
                    RedisCache.set(cache_key, r2_url, ttl=REDIS_TTL)
                    logger.debug(f"[IMAGE_CACHE] R2 hit, promoted to Redis: {url[:50]}...")
                    return r2_url
        except Exception as e:
            logger.warning(f"[IMAGE_CACHE] R2 check failed: {e}")
        
        return None
    
    @classmethod
    async def store(cls, original_url: str, image_data: bytes, content_type: str = "image/jpeg") -> str:
        """
        Store downloaded image in both Redis and R2.
        
        Args:
            original_url: Original image URL (used as cache key)
            image_data: Image bytes
            content_type: MIME type of the image
            
        Returns:
            R2 public URL for the cached image
        """
        storage = get_storage_service()
        
        # Generate filename from URL hash
        url_hash = hashlib.md5(original_url.encode()).hexdigest()
        ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
        filename = f"cached_{url_hash}.{ext}"
        
        # Upload to R2
        _, r2_key, _ = await storage.upload_file(
            file_data=image_data,
            original_filename=filename,
            content_type=content_type,
        )
        
        r2_url = storage.get_public_url(r2_key)
        
        # Store URL in Redis for fast lookup
        cache_key = cls._cache_key(original_url)
        RedisCache.set(cache_key, r2_url, ttl=REDIS_TTL)
        
        logger.info(f"[IMAGE_CACHE] Stored in R2 + Redis: {original_url[:50]}...")
        return r2_url
    
    @classmethod
    async def store_generated(cls, description: str, image_data: bytes) -> str:
        """
        Store an AI-generated image.
        
        Args:
            description: Image description (used as cache key)
            image_data: Image bytes
            
        Returns:
            R2 public URL for the image
        """
        # Use description hash as key for generated images
        desc_hash = hashlib.md5(description.encode()).hexdigest()
        cache_key = f"img_gen:{desc_hash}"
        
        storage = get_storage_service()
        filename = f"generated_{desc_hash}.png"
        
        _, r2_key, _ = await storage.upload_file(
            file_data=image_data,
            original_filename=filename,
            content_type="image/png",
        )
        
        r2_url = storage.get_public_url(r2_key)
        RedisCache.set(cache_key, r2_url, ttl=REDIS_TTL)
        
        return r2_url


async def download_image_with_headers(url: str, timeout: float = 10.0) -> Optional[bytes]:
    """
    Download image with browser-like headers.
    
    Args:
        url: Image URL to download
        timeout: Request timeout in seconds
        
    Returns:
        Image bytes if successful, None if failed
    """
    try:
        async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True) as client:
            response = await client.get(url, timeout=timeout)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type or len(response.content) > 1000:
                    return response.content
            logger.warning(f"[IMAGE_DOWNLOAD] Failed {url}: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"[IMAGE_DOWNLOAD] Error for {url}: {e}")
    
    return None


async def get_or_generate_ai_first(
    description: str,
    style: str = "professional",
) -> str:
    """
    AI-First image strategy: Generate image if not cached.
    
    This is the preferred method for getting images in the AI-first strategy.
    
    Args:
        description: What the image should depict
        style: Style for the image (professional, academic, minimal, etc.)
        
    Returns:
        R2 URL of the image (either cached or newly generated)
    """
    # Check generation cache first (by description hash)
    desc_hash = hashlib.md5(f"{description}::{style}".encode()).hexdigest()
    cache_key = f"img_gen:{desc_hash}"
    
    cached_url = RedisCache.get(cache_key)
    if cached_url:
        logger.info(f"[IMAGE_PIPELINE] AI cache hit for: {description[:50]}...")
        return cached_url
    
    # Generate new image
    logger.info(f"[IMAGE_PIPELINE] Generating AI image for: {description[:50]}...")
    url = await generate_ai_image(description, style)
    
    # Cache the result
    RedisCache.set(cache_key, url, ttl=REDIS_TTL)
    
    return url


async def generate_ai_image(description: str, style: str = "professional") -> str:
    """
    Generate image with AI using optimized prompt.
    
    Args:
        description: Image description
        style: Style preset
        
    Returns:
        R2 URL of generated image
    """
    from app.crew.tools.image_generation_tool import NanoBananaImageTool
    
    # Build optimized prompt
    optimized_prompt = f"""Professional image for presentation slide:

Subject: {description}

Requirements:
- High resolution, suitable for projection
- Clean composition with clear focal point
- No text overlays or watermarks
- Visually engaging but not distracting
- Modern, polished aesthetic"""

    tool = NanoBananaImageTool()
    result = await tool.generate_asset(
        optimized_prompt, 
        style=style,
        upload_to_r2=True
    )
    
    if result.success and result.file_path:
        return result.file_path
    else:
        logger.error(f"[IMAGE_PIPELINE] AI generation failed: {result.error}")
        # Return a styled placeholder instead of raising
        return "https://via.placeholder.com/1600x900/2563eb/ffffff?text=Image+Generation+Failed"


async def download_with_fallbacks(
    urls: list[str], 
    description: str,
    max_attempts: int = 3,
    ai_first: bool = True,
) -> Tuple[str, bool]:
    """
    Get image with AI-first strategy.
    
    Args:
        urls: List of image URLs to try (if ai_first=False)
        description: Image description (for AI generation)
        max_attempts: Maximum URLs to try if not AI-first
        ai_first: If True, generate with AI immediately (default)
        
    Returns:
        Tuple of (image_url, is_ai_generated)
    """
    # AI-First strategy: generate immediately
    if ai_first:
        logger.info(f"[IMAGE_PIPELINE] AI-first: generating image for '{description[:50]}...'")
        url = await get_or_generate_ai_first(description)
        return url, True
    
    # Legacy: Try URLs first, then AI fallback
    for url in urls[:max_attempts]:
        # Check cache first
        cached = await ImageCacheService.get(url)
        if cached:
            logger.info(f"[IMAGE_PIPELINE] Cache hit for {url[:50]}...")
            return cached, False
        
        # Try download with browser headers
        image_data = await download_image_with_headers(url)
        if image_data:
            # Store in cache and return
            r2_url = await ImageCacheService.store(url, image_data)
            return r2_url, False
    
    # All URLs failed, use AI
    logger.info(f"[IMAGE_PIPELINE] URL downloads failed, generating AI image")
    url = await get_or_generate_ai_first(description)
    return url, True

