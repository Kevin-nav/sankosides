"""
Citation Cache Service - Convex Backend

2-tier cache (Redis + Convex) for academic citations.
Reduces API calls and prevents rate limiting.

Features:
- Query normalization for cache hits
- Per-provider rate limiting (1s for Semantic Scholar)
- Smart provider rotation on rate limits
- TTL-based expiration in Convex
"""

import json
import re
import time
import hashlib
import asyncio
from typing import Optional, List, Dict, Any

import redis

from app.core.config import settings
from app.core.convex_client import get_convex_client
from app.core.logging import get_logger
from app.models.schemas import CitationMetadata

logger = get_logger(__name__)


class CitationCacheService:
    """
    2-tier citation cache with smart features.
    
    Tier 1: Redis (hot cache, 6 hour TTL)
    Tier 2: Convex (permanent storage with TTL)
    
    Features:
    - Query normalization
    - Per-provider rate limiting
    - Provider rotation on rate limits
    """
    
    # Cache configuration
    REDIS_TTL_SECONDS = 6 * 3600  # 6 hours
    CONVEX_TTL_HOURS = 168  # 7 days
    STALE_THRESHOLD_HOURS = 24  # Refresh in background if older than this
    
    # Rate limiting per provider (seconds between requests)
    RATE_LIMITS = {
        "semantic_scholar": 1.1,  # 1 req/s rate limit
        "crossref": 0.1,  # Very generous
        "openalex": 0.1,  # Very generous
    }
    
    # Track last request time per provider
    _last_request_time: Dict[str, float] = {}
    _rate_limited_providers: Dict[str, float] = {}  # provider -> until timestamp
    
    _redis_client: Optional[redis.Redis] = None
    _memory_cache: Dict[str, Any] = {}  # Fallback if no Redis
    
    @classmethod
    def _get_redis(cls) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if cls._redis_client is not None:
            return cls._redis_client
        
        if settings.redis_url:
            try:
                cls._redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                cls._redis_client.ping()
                logger.info("CitationCache connected to Redis")
                return cls._redis_client
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                return None
        return None
    
    @classmethod
    def normalize_query(cls, query: str) -> str:
        """
        Normalize query for consistent cache keys.
        
        - Lowercase
        - Remove punctuation
        - Sort words (order-independent matching)
        - Remove extra whitespace
        """
        # Lowercase
        query = query.lower()
        
        # Remove punctuation except hyphens in words
        query = re.sub(r'[^\w\s-]', ' ', query)
        
        # Split, sort, and rejoin (order-independent)
        words = sorted(set(query.split()))
        
        # Limit to reasonable length
        normalized = ' '.join(words)[:450]
        
        return normalized
    
    @classmethod
    def _cache_key(cls, normalized_query: str) -> str:
        """Generate cache key (hash) for a query."""
        return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]
    
    @classmethod
    def _redis_cache_key(cls, query_hash: str) -> str:
        """Generate Redis-specific cache key."""
        return f"citations:{query_hash}"
    
    @classmethod
    async def get_from_redis(cls, query: str) -> Optional[List[CitationMetadata]]:
        """Check Redis for cached results."""
        normalized = cls.normalize_query(query)
        query_hash = cls._cache_key(normalized)
        redis_key = cls._redis_cache_key(query_hash)
        
        client = cls._get_redis()
        if client:
            try:
                data = client.get(redis_key)
                if data:
                    citations = json.loads(data)
                    logger.debug(f"Redis cache hit for '{query[:30]}...' ({len(citations)} results)")
                    return [CitationMetadata(**c) for c in citations]
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory cache
        if redis_key in cls._memory_cache:
            logger.debug(f"Memory cache hit for '{query[:30]}...'")
            return [CitationMetadata(**c) for c in cls._memory_cache[redis_key]]
        
        return None
    
    @classmethod
    async def get_from_convex(cls, query: str) -> List[CitationMetadata]:
        """Check Convex for cached citations matching this query."""
        normalized = cls.normalize_query(query)
        query_hash = cls._cache_key(normalized)
        
        try:
            convex = get_convex_client()
            cached = await asyncio.wait_for(
                asyncio.to_thread(
                    convex.query,
                    "citations:getCachedCitations",
                    {"queryHash": query_hash}
                ),
                timeout=10.0
            )
            
            if cached and cached.get("citationData"):
                citation_data = cached["citationData"]
                logger.debug(f"Convex cache hit for '{query[:30]}...' ({len(citation_data)} results)")
                
                # Convert to CitationMetadata
                citations = [CitationMetadata(**c) for c in citation_data]
                
                # Also populate Redis for next time
                await cls.store_in_redis(query, citations)
                
                return citations
                
        except asyncio.TimeoutError:
            logger.warning(f"Convex cache lookup timed out for '{query[:30]}...'")
        except Exception as e:
            logger.warning(f"Convex cache lookup failed: {e}")
        
        return []
    
    @classmethod
    async def store_in_redis(cls, query: str, citations: List[CitationMetadata]) -> None:
        """Store results in Redis cache."""
        normalized = cls.normalize_query(query)
        query_hash = cls._cache_key(normalized)
        redis_key = cls._redis_cache_key(query_hash)
        
        # Convert to JSON-serializable format
        data = [c.model_dump() for c in citations]
        
        client = cls._get_redis()
        if client:
            try:
                client.setex(redis_key, cls.REDIS_TTL_SECONDS, json.dumps(data, default=str))
                logger.debug(f"Stored {len(citations)} citations in Redis for '{query[:30]}...'")
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Always update memory cache as fallback
        cls._memory_cache[redis_key] = data
    
    @classmethod
    async def store_in_convex(
        cls,
        query: str,
        citations: List[CitationMetadata],
        provider: str,
    ) -> None:
        """Store results in Convex for permanent cache."""
        normalized = cls.normalize_query(query)
        query_hash = cls._cache_key(normalized)
        
        # Convert to JSON-serializable format
        citation_data = [c.model_dump() for c in citations]
        
        try:
            convex = get_convex_client()
            await asyncio.wait_for(
                asyncio.to_thread(
                    convex.mutation,
                    "citations:storeCitations",
                    {
                        "queryHash": query_hash,
                        "normalizedQuery": normalized,
                        "citationData": citation_data,
                        "provider": provider,
                        "ttlHours": cls.CONVEX_TTL_HOURS,
                    }
                ),
                timeout=10.0
            )
            logger.debug(f"Stored {len(citations)} citations in Convex for '{query[:30]}...'")
            
        except asyncio.TimeoutError:
            logger.warning(f"Convex store timed out for '{query[:30]}...'")
        except Exception as e:
            logger.warning(f"Convex store failed: {e}")
    
    @classmethod
    def should_rate_limit(cls, provider: str) -> bool:
        """Check if we should delay request to this provider."""
        now = time.time()
        
        # Check if provider is temporarily blocked
        blocked_until = cls._rate_limited_providers.get(provider, 0)
        if now < blocked_until:
            logger.debug(f"{provider} is rate-limited for {blocked_until - now:.1f}s more")
            return True
        
        # Check time since last request
        last_time = cls._last_request_time.get(provider, 0)
        min_interval = cls.RATE_LIMITS.get(provider, 0.1)
        
        if now - last_time < min_interval:
            wait_time = min_interval - (now - last_time)
            logger.debug(f"Rate limiting {provider}: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        cls._last_request_time[provider] = time.time()
        return False
    
    @classmethod
    def mark_rate_limited(cls, provider: str, duration_seconds: int = 60) -> None:
        """Mark a provider as temporarily rate-limited."""
        cls._rate_limited_providers[provider] = time.time() + duration_seconds
        logger.warning(f"Marked {provider} as rate-limited for {duration_seconds}s")
    
    @classmethod
    def get_available_providers(cls, preferred: List[str]) -> List[str]:
        """Get list of available providers, excluding rate-limited ones."""
        now = time.time()
        available = []
        
        for provider in preferred:
            blocked_until = cls._rate_limited_providers.get(provider, 0)
            if now >= blocked_until:
                available.append(provider)
        
        if not available:
            # All blocked - return all and let them handle it
            logger.warning("All providers rate-limited, returning full list anyway")
            return preferred
        
        return available
    
    @classmethod
    async def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics from Convex."""
        try:
            convex = get_convex_client()
            stats = await asyncio.wait_for(
                asyncio.to_thread(
                    convex.query,
                    "citations:getCacheStats",
                    {}
                ),
                timeout=10.0
            )
            return stats
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
