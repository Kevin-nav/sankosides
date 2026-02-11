"""
University API Router - Convex Backend.

Single `/hierarchy` endpoint returns ALL university data in one response.
Uses Convex for data storage and Redis for L1 caching.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import redis
import asyncio

from app.core.convex_client import get_convex_client
from app.core.config import settings
from app.core.logging import get_logger
from app.services.cache import RedisCache


router = APIRouter(prefix="/universities", tags=["universities"])
logger = get_logger(__name__)


# =============================================================================
# REDIS CACHE CLIENT
# =============================================================================

class UniversityCache:
    """
    Redis-backed cache for university hierarchy data.
    
    Uses Upstash Redis for persistent, distributed caching.
    Falls back to in-memory if Redis is not configured.
    """
    _redis_client: Optional[redis.Redis] = None
    _memory_cache: Dict[str, Any] = {}  # Fallback if no Redis
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
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
                logger.info("Connected to Upstash Redis for caching")
                return cls._redis_client
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
                return None
        return None
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get cached value from Redis or memory."""
        return RedisCache.get(key)
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis or memory cache."""
        ttl = ttl or cls.CACHE_TTL_SECONDS
        RedisCache.set(key, value, ttl=ttl)
    
    @classmethod
    def delete(cls, key: str) -> None:
        """Delete key from cache."""
        RedisCache.delete(key)
    
    @classmethod
    def flush_pattern(cls, pattern: str = "*") -> int:
        """Flush keys matching pattern. Returns count deleted."""
        return RedisCache.flush_pattern(pattern)


# =============================================================================
# Response Models
# =============================================================================

class DepartmentHierarchy(BaseModel):
    """Department in the hierarchy."""
    department_id: str
    name: str
    is_stem: bool


class FacultyHierarchy(BaseModel):
    """Faculty with nested departments."""
    faculty_id: str
    name: str
    short_name: str
    departments: List[DepartmentHierarchy]


class UniversityHierarchy(BaseModel):
    """Complete university hierarchy."""
    university_id: str
    name: str
    short_name: str
    country: str
    default_citation_style: str
    spelling_variant: str
    unit_system: str
    faculties: List[FacultyHierarchy]


class HierarchyResponse(BaseModel):
    """Full hierarchy response - everything in one call."""
    universities: List[UniversityHierarchy]
    cached: bool
    cache_ttl_seconds: int


# =============================================================================
# MAIN ENDPOINT: Single call for all data
# =============================================================================

CACHE_KEY = "universities:hierarchy:full"


@router.get("/hierarchy", response_model=HierarchyResponse)
async def get_full_hierarchy():
    """
    Get the complete university hierarchy in ONE call.
    
    Returns all universities with their faculties and departments nested.
    Data is fetched from Convex and cached in Redis for 1 hour.
    
    This eliminates:
    - Multiple API calls for cascading dropdowns
    - N+1 database queries
    - Redundant fetches per user
    """
    # Check cache first
    cached_data = UniversityCache.get(CACHE_KEY)
    if cached_data is not None:
        logger.info("Serving university hierarchy from cache")
        return HierarchyResponse(
            universities=[UniversityHierarchy(**u) for u in cached_data],
            cached=True,
            cache_ttl_seconds=UniversityCache.CACHE_TTL_SECONDS,
        )
    
    logger.info("Cache miss - fetching university hierarchy from Convex")
    
    try:
        # Get Convex client and query the full hierarchy
        convex = get_convex_client()
        
        # Execute the Convex query (synchronous call in thread)
        hierarchy = await asyncio.wait_for(
            asyncio.to_thread(convex.query, "universities:getFullHierarchy", {}),
            timeout=30.0
        )
        
        # Transform Convex response to match our API schema
        # Convex returns camelCase, we need snake_case for API compatibility
        universities_list = []
        for uni in hierarchy:
            faculties_list = []
            for fac in uni.get("faculties", []):
                departments_list = []
                for dept in fac.get("departments", []):
                    departments_list.append({
                        "department_id": dept.get("departmentId"),
                        "name": dept.get("name"),
                        "is_stem": dept.get("isStem", False),
                    })
                
                faculties_list.append({
                    "faculty_id": fac.get("facultyId"),
                    "name": fac.get("name"),
                    "short_name": fac.get("shortName"),
                    "departments": departments_list,
                })
            
            universities_list.append({
                "university_id": uni.get("universityId"),
                "name": uni.get("name"),
                "short_name": uni.get("shortName"),
                "country": uni.get("country"),
                "default_citation_style": uni.get("defaultCitationStyle"),
                "spelling_variant": uni.get("spellingVariant"),
                "unit_system": uni.get("unitSystem"),
                "faculties": faculties_list,
            })
        
        # Cache the result
        UniversityCache.set(CACHE_KEY, universities_list)
        logger.info(f"Cached {len(universities_list)} universities from Convex")
        
        return HierarchyResponse(
            universities=[UniversityHierarchy(**u) for u in universities_list],
            cached=False,
            cache_ttl_seconds=UniversityCache.CACHE_TTL_SECONDS,
        )
        
    except asyncio.TimeoutError:
        logger.error("Convex query timed out")
        raise HTTPException(status_code=504, detail="Database query timed out")
    except Exception as e:
        logger.error(f"Failed to fetch hierarchy from Convex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

@router.post("/cache/invalidate")
async def invalidate_cache():
    """
    Invalidate the university cache.
    Call after updating university data in Convex.
    """
    count = UniversityCache.flush_pattern("universities:*")
    logger.info(f"Invalidated {count} cache entries")
    return {
        "message": "Cache invalidated",
        "entries_cleared": count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/cache/status")
async def cache_status():
    """Check cache status and Redis connection."""
    client = UniversityCache._get_client()
    cached = UniversityCache.get(CACHE_KEY)
    
    return {
        "redis_connected": client is not None,
        "hierarchy_cached": cached is not None,
        "university_count": len(cached) if cached else 0,
        "data_source": "convex",
    }
