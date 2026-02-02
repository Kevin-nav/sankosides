"""
Database Configuration (Convex)

Replaces SQLAlchemy setup with Convex client.
Maintains backward compatibility for imports where possible, but shifts logic to API calls.
"""

from app.core.convex_client import get_convex_client

# Re-export client getter
def get_db():
    """
    Get the Convex client.
    Replaces get_async_session dependency.
    """
    return get_convex_client()

# Re-export for compatibility (though should be refactored out eventually)
async def get_async_session():
    """
    Legacy dependency injection for FastAPI.
    Yields the Convex client.
    """
    yield get_convex_client()

# Legacy models imports check - if other code imports models from here, 
# we might need dummy classes or valid Pydantic models.
# For now, we assume we will refactor the consumers.
