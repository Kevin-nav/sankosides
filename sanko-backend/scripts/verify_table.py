"""Verify layout_presets table exists"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
import app.core.database as db


async def verify():
    db.init_async_db()
    async with db.AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM layout_presets"))
            count = result.scalar()
            print(f"SUCCESS: layout_presets table exists with {count} rows")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(verify())
