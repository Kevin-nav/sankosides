"""
Citation Cache Service

2-tier cache (Redis + PostgreSQL) for academic citations.
Reduces API calls and prevents rate limiting.

Features:
- Query normalization for cache hits
- Per-provider rate limiting (1s for Semantic Scholar)
- Stale-while-revalidate for background refresh
- Smart provider rotation on rate limits
"""

import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import CachedCitation, get_async_session
from app.core.logging import get_logger
from app.models.schemas import CitationMetadata

logger = get_logger(__name__)


class CitationCacheService:
    """
    2-tier citation cache with smart features.
    
    Tier 1: Redis (hot cache, 6 hour TTL)
    Tier 2: PostgreSQL (permanent storage)
    
    Features:
    - Query normalization
    - Per-provider rate limiting
    - Provider rotation on rate limits
    """
    
    # Cache configuration
    REDIS_TTL_SECONDS = 6 * 3600  # 6 hours
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
        """Generate Redis cache key for a query."""
        # Use hash for long queries
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:16]
        return f"citations:{query_hash}"
    
    @classmethod
    async def get_from_redis(cls, query: str) -> Optional[List[CitationMetadata]]:
        """Check Redis for cached results."""
        normalized = cls.normalize_query(query)
        key = cls._cache_key(normalized)
        
        client = cls._get_redis()
        if client:
            try:
                data = client.get(key)
                if data:
                    citations = json.loads(data)
                    logger.debug(f"Redis cache hit for '{query[:30]}...' ({len(citations)} results)")
                    return [CitationMetadata(**c) for c in citations]
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory cache
        if key in cls._memory_cache:
            logger.debug(f"Memory cache hit for '{query[:30]}...'")
            return [CitationMetadata(**c) for c in cls._memory_cache[key]]
        
        return None
    
    @classmethod
    async def get_from_postgres(
        cls,
        query: str,
        session: AsyncSession,
    ) -> List[CitationMetadata]:
        """Check PostgreSQL for cached citations matching this query."""
        normalized = cls.normalize_query(query)
        
        try:
            result = await session.execute(
                select(CachedCitation)
                .where(CachedCitation.normalized_query == normalized)
                .limit(10)
            )
            rows = result.scalars().all()
            
            if rows:
                logger.debug(f"PostgreSQL cache hit for '{query[:30]}...' ({len(rows)} results)")
                
                # Update last_accessed_at
                await session.execute(
                    update(CachedCitation)
                    .where(CachedCitation.normalized_query == normalized)
                    .values(last_accessed_at=datetime.utcnow())
                )
                await session.commit()
                
                # Convert to CitationMetadata
                citations = [CitationMetadata(**row.citation_data) for row in rows]
                
                # Also populate Redis for next time
                await cls.store_in_redis(query, citations)
                
                return citations
        except Exception as e:
            logger.warning(f"PostgreSQL cache lookup failed: {e}")
        
        return []
    
    @classmethod
    async def store_in_redis(cls, query: str, citations: List[CitationMetadata]) -> None:
        """Store results in Redis cache."""
        normalized = cls.normalize_query(query)
        key = cls._cache_key(normalized)
        
        # Convert to JSON-serializable format
        data = [c.model_dump() for c in citations]
        
        client = cls._get_redis()
        if client:
            try:
                client.setex(key, cls.REDIS_TTL_SECONDS, json.dumps(data, default=str))
                logger.debug(f"Stored {len(citations)} citations in Redis for '{query[:30]}...'")
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Always update memory cache as fallback
        cls._memory_cache[key] = data
    
    @classmethod
    async def store_in_postgres(
        cls,
        query: str,
        citations: List[CitationMetadata],
        provider: str,
        session: AsyncSession,
    ) -> None:
        """Store results in PostgreSQL for permanent cache."""
        normalized = cls.normalize_query(query)
        
        for citation in citations:
            try:
                # Check if DOI already exists
                if citation.doi:
                    existing = await session.execute(
                        select(CachedCitation).where(CachedCitation.doi == citation.doi)
                    )
                    if existing.scalar():
                        continue  # Skip duplicates
                
                # Insert new citation
                cached = CachedCitation(
                    normalized_query=normalized,
                    doi=citation.doi,
                    arxiv_id=citation.arxiv_id,
                    citation_data=citation.model_dump(),
                    provider=provider,
                )
                session.add(cached)
                
            except Exception as e:
                logger.warning(f"Failed to cache citation: {e}")
        
        try:
            await session.commit()
            logger.debug(f"Stored {len(citations)} citations in PostgreSQL for '{query[:30]}...'")
        except Exception as e:
            await session.rollback()
            logger.warning(f"PostgreSQL commit failed: {e}")
    
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
