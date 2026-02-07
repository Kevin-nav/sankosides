"""
Database Configuration (Hybrid: Convex + SQLAlchemy)

Maintains both Convex client (for new features) and SQLAlchemy (for legacy support)
until migration is complete.
"""

import ssl
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from app.core.convex_client import get_convex_client

# SQLAlchemy Base for ORM models (required during migration period)
Base = declarative_base()

# Convex Client Getter
def get_db():
    """
    Get the Convex client.
    """
    return get_convex_client()


def _convert_database_url(url: str) -> tuple[str, dict]:
    """
    Convert a standard PostgreSQL URL to asyncpg-compatible format.
    
    asyncpg doesn't support sslmode/channel_binding in the URL - it uses
    a separate ssl context passed via connect_args.
    
    Returns:
        Tuple of (converted_url, connect_args)
    """
    if not url:
        return url, {}
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Change scheme to asyncpg
    scheme = parsed.scheme
    if scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"
    
    # Parse and filter query parameters
    query_params = parse_qs(parsed.query)
    
    # Remove parameters that asyncpg doesn't support
    params_to_remove = ['sslmode', 'channel_binding']
    for param in params_to_remove:
        query_params.pop(param, None)
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    
    # Rebuild URL
    new_url = urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    # Configure SSL for cloud databases
    connect_args = {}
    if any(cloud in url for cloud in ["neon", "supabase", "railway", "elephantsql"]):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
    
    return new_url, connect_args


# SQLAlchemy Setup (Restored for Legacy Support)
database_url, connect_args = _convert_database_url(settings.database_url)

engine = create_async_engine(database_url, echo=settings.debug, connect_args=connect_args)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a SQLAlchemy AsyncSession.
    Required for existing routers/controllers that haven't been migrated to Convex yet.
    """
    async with async_session_factory() as session:
        yield session
