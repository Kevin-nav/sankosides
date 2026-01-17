"""
Shared Redis Cache Service

Centralized cache utility using Upstash Redis.
Falls back to in-memory cache if Redis is not configured.
"""

import json
from typing import Optional, Any, Dict
import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Shared Redis cache for all services.
    
    Uses Upstash Redis for persistent, distributed caching.
    Falls back to in-memory if Redis is not configured.
    """
    _redis_client: Optional[redis.Redis] = None
    _memory_cache: Dict[str, Any] = {}  # Fallback if no Redis
    _connected: bool = False
    
    @classmethod
    def _get_client(cls) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if cls._redis_client is not None:
            return cls._redis_client
        
        if settings.redis_url:
            try:
                cls._redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                # Test connection
                cls._redis_client.ping()
                cls._connected = True
                logger.info("Connected to Upstash Redis")
                return cls._redis_client
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
                cls._connected = False
                return None
        return None
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get cached value from Redis or memory."""
        client = cls._get_client()
        
        if client:
            try:
                data = client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory
        return cls._memory_cache.get(key)
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in Redis or memory cache. TTL in seconds."""
        client = cls._get_client()
        
        if client:
            try:
                client.setex(key, ttl, json.dumps(value, default=str))
                logger.debug(f"Cached {key} in Redis (TTL: {ttl}s)")
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Fallback to memory
        cls._memory_cache[key] = value
    
    @classmethod
    def delete(cls, key: str) -> None:
        """Delete key from cache."""
        client = cls._get_client()
        
        if client:
            try:
                client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        cls._memory_cache.pop(key, None)
    
    @classmethod
    def flush_pattern(cls, pattern: str = "*") -> int:
        """Flush keys matching pattern. Returns count deleted."""
        client = cls._get_client()
        count = 0
        
        if client:
            try:
                keys = client.keys(pattern)
                if keys:
                    count = client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis flush error: {e}")
        
        if pattern == "*":
            count += len(cls._memory_cache)
            cls._memory_cache.clear()
        
        return count
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if Redis is connected."""
        cls._get_client()  # Ensure we've tried to connect
        return cls._connected
