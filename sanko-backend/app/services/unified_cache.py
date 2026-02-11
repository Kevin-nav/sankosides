"""
Unified Cache Service

Multi-tier caching with:
- L1: In-process TTLCache (fast, ~0.01ms)
- L2: Upstash Redis (distributed, ~5-20ms)

All caches are SHARED across users - first user populates,
everyone benefits from the cached result.
"""

import json
from typing import TypeVar, Callable, Optional, Any, Union
from threading import RLock
from cachetools import TTLCache

from app.services.cache import RedisCache
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class SharedCache:
    """
    2-tier shared cache for global resources.
    
    L1: In-process TTLCache (microseconds, limited memory)
    L2: Upstash Redis (milliseconds, distributed)
    
    Cache keys are resource-based (not user-based), so all users
    benefit from cached data.
    
    Usage:
        cache = SharedCache("templates", l1_maxsize=50, l1_ttl=300, l2_ttl=3600)
        
        # Async fetch with cache
        result = await cache.get_or_fetch(
            key="all",
            fetch_fn=lambda: db.get_all_templates()
        )
        
        # Manual set
        cache.set("theme:modern", theme_data)
        
        # Invalidate on update
        cache.invalidate("all")
    """
    
    def __init__(
        self,
        namespace: str,
        l1_maxsize: int = 100,
        l1_ttl: int = 60,
        l2_ttl: int = 3600,
    ):
        """
        Initialize a shared cache.
        
        Args:
            namespace: Cache namespace (e.g., "templates", "themes")
            l1_maxsize: Max items in L1 memory cache
            l1_ttl: L1 TTL in seconds (shorter = fresher data)
            l2_ttl: L2 Redis TTL in seconds (longer for cross-request benefit)
        """
        self.namespace = namespace
        self.l1 = TTLCache(maxsize=l1_maxsize, ttl=l1_ttl)
        self.l1_lock = RLock()
        self.l2_ttl = l2_ttl
        
        logger.debug(f"SharedCache '{namespace}' initialized: L1={l1_maxsize} items/{l1_ttl}s, L2={l2_ttl}s")
    
    def _l2_key(self, key: str) -> str:
        """Generate Redis key with namespace prefix."""
        return f"{self.namespace}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 → L2).
        
        Returns None if not found in either tier.
        """
        # L1: Memory (fastest)
        with self.l1_lock:
            if key in self.l1:
                logger.debug(f"[{self.namespace}] L1 HIT: {key}")
                return self.l1[key]
        
        # L2: Redis
        l2_key = self._l2_key(key)
        cached = RedisCache.get(l2_key)
        if cached is not None:
            logger.debug(f"[{self.namespace}] L2 HIT: {key}")
            # Populate L1 for next request
            with self.l1_lock:
                self.l1[key] = cached
            return cached
        
        logger.debug(f"[{self.namespace}] MISS: {key}")
        return None
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], T],
        skip_l1: bool = False,
    ) -> Optional[T]:
        """
        Get from cache or fetch using provided function.
        
        Args:
            key: Cache key
            fetch_fn: Async or sync function to fetch data on cache miss
            skip_l1: If True, skip L1 cache (for large objects)
            
        Returns:
            Cached or fetched value, or None if fetch returns None
        """
        # L1: Memory
        if not skip_l1:
            with self.l1_lock:
                if key in self.l1:
                    logger.debug(f"[{self.namespace}] L1 HIT: {key}")
                    return self.l1[key]
        
        # L2: Redis
        l2_key = self._l2_key(key)
        cached = RedisCache.get(l2_key)
        if cached is not None:
            logger.debug(f"[{self.namespace}] L2 HIT: {key}")
            if not skip_l1:
                with self.l1_lock:
                    self.l1[key] = cached
            return cached
        
        # Cache MISS - fetch from source
        logger.debug(f"[{self.namespace}] MISS: {key} - fetching from source")
        
        # Handle both async and sync functions
        import asyncio
        if asyncio.iscoroutinefunction(fetch_fn):
            value = await fetch_fn()
        else:
            value = fetch_fn()
        
        if value is not None:
            self.set(key, value, skip_l1=skip_l1)
        
        return value
    
    def set(self, key: str, value: Any, skip_l1: bool = False) -> None:
        """
        Set value in cache (both L1 and L2).
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable for L2)
            skip_l1: If True, only set in L2 (for large objects)
        """
        if not skip_l1:
            with self.l1_lock:
                self.l1[key] = value
        
        l2_key = self._l2_key(key)
        RedisCache.set(l2_key, value, self.l2_ttl)
        logger.debug(f"[{self.namespace}] SET: {key}")
    
    def invalidate(self, key: str) -> None:
        """
        Remove value from all cache tiers.
        
        Call this when the underlying data changes (e.g., admin update).
        """
        with self.l1_lock:
            self.l1.pop(key, None)
        
        l2_key = self._l2_key(key)
        RedisCache.delete(l2_key)
        logger.info(f"[{self.namespace}] INVALIDATED: {key}")
    
    def invalidate_pattern(self, pattern: str = "*") -> int:
        """
        Invalidate all keys matching pattern in this namespace.
        
        Returns count of keys deleted from L2.
        """
        # Clear all L1
        with self.l1_lock:
            self.l1.clear()
        
        # Clear L2 by pattern
        full_pattern = f"{self.namespace}:{pattern}"
        count = RedisCache.flush_pattern(full_pattern)
        logger.info(f"[{self.namespace}] INVALIDATED PATTERN: {pattern} ({count} keys)")
        return count
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self.l1_lock:
            l1_size = len(self.l1)
            l1_maxsize = self.l1.maxsize
        
        return {
            "namespace": self.namespace,
            "l1_size": l1_size,
            "l1_maxsize": l1_maxsize,
            "l1_ttl": self.l1.ttl,
            "l2_ttl": self.l2_ttl,
            "l2_connected": RedisCache.is_connected(),
        }


# =============================================================================
# Pre-configured Shared Caches
# =============================================================================

# Templates: Static data, rarely changes
# L1: 5 min (300s), L2: 1 hour (3600s)
template_cache = SharedCache(
    namespace="templates",
    l1_maxsize=50,
    l1_ttl=300,
    l2_ttl=3600,
)

# Themes: Static data, rarely changes
# L1: 5 min, L2: 1 hour
theme_cache = SharedCache(
    namespace="themes",
    l1_maxsize=50,
    l1_ttl=300,
    l2_ttl=3600,
)

# Palettes: Static data, rarely changes
# L1: 5 min, L2: 1 hour
palette_cache = SharedCache(
    namespace="palettes",
    l1_maxsize=50,
    l1_ttl=300,
    l2_ttl=3600,
)

# Template Previews: Rendered HTML, expensive to generate
# L1: 1 min (fast expiry for memory), L2: 10 min
preview_cache = SharedCache(
    namespace="preview",
    l1_maxsize=100,
    l1_ttl=60,
    l2_ttl=600,
)

# PDF KnowledgeBase: Large objects, skip L1
# L2 only: 24 hours
pdf_kb_cache = SharedCache(
    namespace="pdf_kb",
    l1_maxsize=20,  # Only store small metadata
    l1_ttl=120,
    l2_ttl=86400,
)

# Layout Presets: Mostly static but admin-editable
# L1: 5 min, L2: 30 min
layout_cache = SharedCache(
    namespace="layout_presets",
    l1_maxsize=100,
    l1_ttl=300,
    l2_ttl=1800,
)
