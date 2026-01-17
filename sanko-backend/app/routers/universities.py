"""
University API Router - Optimized with Redis Caching.

Single `/hierarchy` endpoint returns ALL university data in one response.
Cached in Upstash Redis for 1 hour - eliminates DB queries for every user.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import redis

from app.core.database import get_async_session
from app.core.config import settings
from app.core.logging import get_logger


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
    def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis or memory cache."""
        ttl = ttl or cls.CACHE_TTL_SECONDS
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
async def get_full_hierarchy(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get the complete university hierarchy in ONE call.
    
    Returns all universities with their faculties and departments nested.
    Cached in Redis for 1 hour - shared across all users.
    
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
    
    logger.info("Cache miss - fetching university hierarchy from database")
    
    # Single optimized query to get everything
    query = """
        SELECT 
            u.university_id, u.name as uni_name, u.short_name as uni_short,
            u.country, u.default_citation_style, u.spelling_variant, u.unit_system,
            f.faculty_id, f.name as fac_name, f.short_name as fac_short,
            d.department_id, d.name as dept_name, d.is_stem
        FROM universities u
        LEFT JOIN faculties f ON f.university_id = u.id AND f.is_active = true
        LEFT JOIN departments d ON d.faculty_id = f.id AND d.is_active = true
        WHERE u.is_active = true
        ORDER BY u.name, f.display_order, f.name, d.display_order, d.name
    """
    
    result = await session.execute(text(query))
    rows = result.fetchall()
    
    # Build hierarchical structure
    universities_map: Dict[str, dict] = {}
    faculties_map: Dict[str, Dict[str, dict]] = {}
    
    for row in rows:
        uni_id = row.university_id
        
        # Create university if not exists
        if uni_id not in universities_map:
            universities_map[uni_id] = {
                "university_id": uni_id,
                "name": row.uni_name,
                "short_name": row.uni_short,
                "country": row.country,
                "default_citation_style": row.default_citation_style,
                "spelling_variant": row.spelling_variant,
                "unit_system": row.unit_system,
                "faculties": [],
            }
            faculties_map[uni_id] = {}
        
        # Add faculty if exists
        if row.faculty_id and row.faculty_id not in faculties_map[uni_id]:
            faculty = {
                "faculty_id": row.faculty_id,
                "name": row.fac_name,
                "short_name": row.fac_short,
                "departments": [],
            }
            faculties_map[uni_id][row.faculty_id] = faculty
            universities_map[uni_id]["faculties"].append(faculty)
        
        # Add department if exists
        if row.department_id and row.faculty_id:
            faculty = faculties_map[uni_id].get(row.faculty_id)
            if faculty:
                # Avoid duplicates
                if not any(d["department_id"] == row.department_id for d in faculty["departments"]):
                    faculty["departments"].append({
                        "department_id": row.department_id,
                        "name": row.dept_name,
                        "is_stem": row.is_stem,
                    })
    
    universities_list = list(universities_map.values())
    
    # Cache the result
    UniversityCache.set(CACHE_KEY, universities_list)
    logger.info(f"Cached {len(universities_list)} universities in Redis")
    
    return HierarchyResponse(
        universities=[UniversityHierarchy(**u) for u in universities_list],
        cached=False,
        cache_ttl_seconds=UniversityCache.CACHE_TTL_SECONDS,
    )


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

@router.post("/cache/invalidate")
async def invalidate_cache():
    """
    Invalidate the university cache.
    Call after updating university data in the database.
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
    }
