
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.core.database import init_async_db, AsyncSessionLocal
from app.core.template_models import SlideTemplate, ThemeConfig
from sqlalchemy import select

async def inspect_db():
    init_async_db()
    # Import locally to ensure initialization
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        print("Checking pro_modern theme...")
        # Check pro_modern theme config
        stmt = select(ThemeConfig).where(ThemeConfig.theme_id == "pro_modern")
        result = await session.execute(stmt)
        theme = result.scalar_one_or_none()
        if theme:
            print(f"Theme 'pro_modern' layout_style: '{theme.layout_style}'")
        else:
            print("Theme 'pro_modern' not found!")
            
        print("Checking section_modern template...")
        # Check for section_modern template
        stmt = select(SlideTemplate).where(SlideTemplate.template_id == "section_modern")
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            print(f"--- START TEMPLATE: {template.template_id} ---")
            print(template.html_template)
            print("--- END TEMPLATE ---")
        else:
            print("Template 'section_modern' not found!")

if __name__ == "__main__":
    try:
        asyncio.run(inspect_db())
    except Exception as e:
        import traceback
        traceback.print_exc()
