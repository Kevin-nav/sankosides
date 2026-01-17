"""
Runner script for seeding UMaT data.
Run this after applying migrations to populate the database.

Usage:
    cd sanko-backend
    .\\venv\\Scripts\\python.exe scripts/run_seed.py
"""

import asyncio
import os
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from scripts.seed_umat import seed_umat_data


def convert_database_url(url: str) -> str:
    """
    Convert a standard PostgreSQL URL to asyncpg-compatible format.
    
    Handles:
    - Changing driver from postgresql:// to postgresql+asyncpg://
    - Removing sslmode and channel_binding parameters (asyncpg handles SSL differently)
    """
    if not url:
        return url
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Change scheme to asyncpg
    scheme = parsed.scheme
    if scheme == "postgresql" or scheme == "postgres":
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
    
    return new_url


async def main():
    """Run the seeding process."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("Please set it in your .env file or environment")
        return
    
    # Convert to asyncpg-compatible URL
    async_url = convert_database_url(database_url)
    
    print(f"🔌 Connecting to database...")
    
    # Create async engine with SSL support for cloud databases
    connect_args = {}
    
    # Check if this is a cloud database that needs SSL
    if any(cloud in async_url for cloud in ["neon", "supabase", "railway", "elephantsql"]):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
        print("  🔒 Using SSL for cloud database")
    
    engine = create_async_engine(async_url, echo=False, connect_args=connect_args)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            await seed_umat_data(session)
        print("✅ Seeding complete!")
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())
