
import asyncio
import sys
import os
sys.path.append(os.getcwd())

import app.core.database as db
from app.core.template_models import SlideTemplate
from sqlalchemy import select

async def check_template():
    db.init_async_db()
    # Access via module to get the updated value
    async with db.AsyncSessionLocal() as session:
        result = await session.execute(select(SlideTemplate).where(SlideTemplate.template_id == "section"))
        template = result.scalar_one_or_none()
        if template:
            print(f"--- START TEMPLATE: {template.template_id} ---")
            print(template.html_template)
            print("--- END TEMPLATE ---")
        else:
            print("Template 'section' not found!")

if __name__ == "__main__":
    try:
        # On Windows + Python 3.8+, Proactor is default and needed for asyncpg usually?
        # Actually sqlalchemy asyncpg works fine with default loop on modern python
        # verify logs in run.py show: Windows ProactorEventLoop policy set
        pass 
        asyncio.run(check_template())
    except Exception as e:
        import traceback
        traceback.print_exc()
