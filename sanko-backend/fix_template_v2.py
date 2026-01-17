
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.core.database import init_async_db
from app.core.template_models import SlideTemplate
from sqlalchemy import select

async def fix_template():
    init_async_db()
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        stmt = select(SlideTemplate).where(SlideTemplate.template_id == "section_modern")
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        
        if template:
            print(f"Fixing template {template.template_id}...")
            # Use EXACT string matching
            original = "{{ slide.section-subtitle }}"
            replacement = "{{ slide.subtitle }}"
            
            if original in template.html_template:
                new_html = template.html_template.replace(original, replacement)
                template.html_template = new_html
                await session.commit()
                print("Template updated successfully!")
            else:
                print(f"Could not find exact string: {original}")
                # debug print the relevant line
                for line in template.html_template.split('\n'):
                    if "slide.section-subtitle" in line:
                         print(f"DEBUG found line: {line.strip()}")
        else:
            print("Template not found")

if __name__ == "__main__":
    asyncio.run(fix_template())
