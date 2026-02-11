"""
Shared Redis Cache Service

Centralized cache utility using Upstash Redis.
Falls back to in-memory cache if Redis is not configured.
"""

import json
from typing import Optional, Any, Dict
import time
import fnmatch
from uuid import uuid4
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
    _memory_cache: Dict[str, Dict[str, Any]] = {}  # key -> {"value": Any, "expires_at": float}
    _memory_locks: Dict[str, Dict[str, Any]] = {}  # lock_key -> {"token": str, "expires_at": float}
    _connected: bool = False

    @classmethod
    def _memory_get(cls, key: str) -> Optional[Any]:
        entry = cls._memory_cache.get(key)
        if not entry:
            return None
        expires_at = entry.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            cls._memory_cache.pop(key, None)
            return None
        return entry.get("value")

    @classmethod
    def _memory_set(cls, key: str, value: Any, ttl: int) -> None:
        cls._memory_cache[key] = {
            "value": value,
            "expires_at": time.time() + max(1, ttl),
        }
    
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
        return cls._memory_get(key)
    
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
        cls._memory_set(key, value, ttl)
    
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
        cls._memory_locks.pop(key, None)
    
    @classmethod
    def flush_pattern(cls, pattern: str = "*") -> int:
        """Flush keys matching pattern. Returns count deleted."""
        client = cls._get_client()
        count = 0
        
        if client:
            try:
                keys = []
                for redis_key in client.scan_iter(match=pattern, count=200):
                    keys.append(redis_key)
                    if len(keys) >= 500:
                        count += client.delete(*keys)
                        keys = []
                if keys:
                    count += client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis flush error: {e}")
        
        memory_keys = list(cls._memory_cache.keys())
        lock_keys = list(cls._memory_locks.keys())
        deleted_memory = 0

        for key in memory_keys:
            if pattern == "*" or fnmatch.fnmatch(key, pattern):
                cls._memory_cache.pop(key, None)
                deleted_memory += 1

        for key in lock_keys:
            if pattern == "*" or fnmatch.fnmatch(key, pattern):
                cls._memory_locks.pop(key, None)

        count += deleted_memory
        
        return count
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if Redis is connected."""
        cls._get_client()  # Ensure we've tried to connect
        return cls._connected

    @classmethod
    def acquire_lock(cls, lock_key: str, ttl: int = 300, token: Optional[str] = None) -> Optional[str]:
        """
        Acquire a distributed lock.

        Returns lock token on success, None if lock is already held.
        """
        lock_token = token or uuid4().hex
        client = cls._get_client()

        if client:
            try:
                acquired = client.set(lock_key, lock_token, nx=True, ex=ttl)
                return lock_token if acquired else None
            except Exception as e:
                logger.warning(f"Redis lock acquire error: {e}")

        # Fallback in-memory lock
        existing = cls._memory_locks.get(lock_key)
        now = time.time()
        if existing and existing.get("expires_at", 0) > now:
            return None

        cls._memory_locks[lock_key] = {
            "token": lock_token,
            "expires_at": now + max(1, ttl),
        }
        return lock_token

    @classmethod
    def release_lock(cls, lock_key: str, token: str) -> bool:
        """
        Release a distributed lock only if token matches.
        """
        client = cls._get_client()

        if client:
            try:
                release_script = """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('del', KEYS[1])
                else
                    return 0
                end
                """
                deleted = client.eval(release_script, 1, lock_key, token)
                return bool(deleted)
            except Exception as e:
                logger.warning(f"Redis lock release error: {e}")

        existing = cls._memory_locks.get(lock_key)
        if existing and existing.get("token") == token:
            cls._memory_locks.pop(lock_key, None)
            return True
        return False
