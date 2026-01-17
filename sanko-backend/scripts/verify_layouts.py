import asyncio
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
import app.core.database as db
from app.core.template_models import SlideTemplate, ThemeConfig
from app.api.routers import templates

async def verify_layouts():
    print("Initializing DB...")
    db.init_async_db()
    
    async with db.AsyncSessionLocal() as session:
        print("Verifying Modern Layout...")
        # 1. Check if we have a modern theme
        query = select(ThemeConfig).where(ThemeConfig.layout_style == "modern")
        result = await session.execute(query)
        modern_theme = result.scalars().first()
        
        if not modern_theme:
            print("❌ No 'modern' theme found!")
            return

        print(f"Found modern theme: {modern_theme.name}")
        
        # 2. Simulate API call logic (call internal logic or just run similar query)
        # We want to ensure 'templates.preview_theme_template' logic works.
        # But calling the router function directly requires mocking a request.
        # Let's just verify the template fetching logic we added.
        
        template_type = "title"
        layout_style = modern_theme.layout_style
        
        target_ids = []
        if layout_style != "default":
            target_ids.append(f"{template_type}_{layout_style}")
        target_ids.append(template_type)
        
        query = select(SlideTemplate).where(SlideTemplate.template_id.in_(target_ids))
        result = await session.execute(query)
        found_templates = {t.template_id: t for t in result.scalars().all()}
        
        template = None
        if layout_style != "default":
            template = found_templates.get(f"{template_type}_{layout_style}")
            
        if not template:
            template = found_templates.get(template_type)
            
        if template and template.template_id == f"title_modern":
            print(f"✅ Successfully resolved to 'title_modern' for theme {modern_theme.name}")
            if "slide-title-modern" in template.html_template:
                print("✅ HTML content verification passed: found 'slide-title-modern'")
            else:
                 print("❌ HTML content mismatch")
        else:
             print(f"❌ Failed to resolve variants. Got: {template.template_id if template else 'None'}")
             
        
        print("\nVerifying Split Layout...")
        # 3. Check split theme
        query = select(ThemeConfig).where(ThemeConfig.layout_style == "split")
        result = await session.execute(query)
        split_theme = result.scalars().first()
        
        if not split_theme:
            print("❌ No 'split' theme found!")
            return
            
        print(f"Found split theme: {split_theme.name}")
        
        layout_style = split_theme.layout_style
        target_ids = [f"{template_type}_{layout_style}", template_type]
        
        query = select(SlideTemplate).where(SlideTemplate.template_id.in_(target_ids))
        result = await session.execute(query)
        found_templates = {t.template_id: t for t in result.scalars().all()}
        
        template = found_templates.get(f"{template_type}_{layout_style}")
        
        if template and template.template_id == f"title_split":
             print(f"✅ Successfully resolved to 'title_split' for theme {split_theme.name}")
             if "slide-title-split" in template.html_template:
                print("✅ HTML content verification passed: found 'slide-title-split'")
        else:
             print(f"❌ Failed to resolve split variant. Found: {template.template_id if template else 'None'}")


if __name__ == "__main__":
    asyncio.run(verify_layouts())
