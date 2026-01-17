
import asyncio
import sys
import os
import re
sys.path.append(os.getcwd())

from app.core.database import init_async_db
from app.core.template_models import SlideTemplate
from sqlalchemy import select

async def check_vars():
    init_async_db()
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        stmt = select(SlideTemplate).where(SlideTemplate.template_id == "section_modern")
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            print(f"Template ID: {template.template_id}")
            lines = template.html_template.split('\n')
            for i, line in enumerate(lines):
                if "{{" in line:
                    print(f"Line {i+1}: {line.strip()}")
        else:
            print("Template not found")

if __name__ == "__main__":
    asyncio.run(check_vars())
