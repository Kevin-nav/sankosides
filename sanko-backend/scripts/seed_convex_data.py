import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.convex_client import get_convex_client

# Import data sources
# We need to act carefully here as these scripts might try to import DB modules
# that we want to avoid initializing fully if they try to connect to Postgres
# However, for simply importing the lists (TEMPLATES, PALETTES, THEMES), it should be fine
# provided we wrap imports in try/except or if the files are safe.
# Let's inspect them - they seemed to import db.AsyncSessionLocal but only use it in functions.
# So importing the module should be safe.

from scripts.seed_templates import TEMPLATES, PALETTES, THEMES
from scripts.seed_layouts import (
    MODERN_TITLE, MODERN_CONTENT, SPLIT_TITLE, SPLIT_CONTENT
)

# Define Layout Presets (migrated from layout_selector.py DEFAULT_LAYOUTS)
# We redefine them here or import them if we can access them easily.
# Accessing them from layout_selector.py is safe as it doesn't do side-effects on import.
from app.services.layout_selector import DEFAULT_LAYOUTS

async def seed_convex():
    client = get_convex_client()
    print("🚀 Starting Convex Data Migration...")

    # 1. Seed Layout Presets
    print(f"\n📦 Seeding {len(DEFAULT_LAYOUTS)} Layout Presets...")
    for preset in DEFAULT_LAYOUTS:
        try:
            # Upsert layout preset
            await client.mutation("layoutPresets:upsert", {
                "presetId": preset["preset_id"],
                "name": preset["name"],
                "description": preset.get("description", f"{preset['name']} Layout"),
                "config": {
                    "category": preset["category"],
                    "content_types": preset["content_types"],
                    "variety_group": preset["variety_group"],
                    "variety_weight": preset["variety_weight"],
                    "regions": preset["regions"],
                },
                "isSystem": True
            })
            print(f"  ✅ Upserted preset: {preset['preset_id']}")
        except Exception as e:
            print(f"  ❌ Failed to upsert preset {preset['preset_id']}: {e}")

    # 2. Seed Templates
    print(f"\n📄 Seeding {len(TEMPLATES)} Templates...")
    for tmpl in TEMPLATES:
        try:
            await client.mutation("templates:upsertTemplate", {
                "templateId": tmpl["template_id"],
                "name": tmpl["name"],
                "description": tmpl["description"],
                "contentType": tmpl["content_type"],
                "category": "general", # Default category
                "htmlTemplate": tmpl["html_template"],
                "cssStyles": tmpl.get("css_styles", ""),
                "isActive": True,
                "isSystem": True,
                "version": "1.0",
            })
            print(f"  ✅ Upserted template: {tmpl['template_id']}")
        except Exception as e:
            print(f"  ❌ Failed to upsert template {tmpl['template_id']}: {e}")

    # 3. Seed Layout-Specific Templates (from seed_layouts.py)
    # These are variants like title_modern, title_split, etc.
    layout_templates = [
        {
            "template_id": "title_modern",
            "name": "Modern Title",
            "content_type": "title",
            "category": "modern",
            "html_template": MODERN_TITLE,
        },
        {
            "template_id": "content_modern",
            "name": "Modern Content",
            "content_type": "content",
            "category": "modern",
            "html_template": MODERN_CONTENT,
        },
        {
            "template_id": "title_split",
            "name": "Split Title",
            "content_type": "title",
            "category": "split",
            "html_template": SPLIT_TITLE,
        },
        {
            "template_id": "content_split",
            "name": "Split Content",
            "content_type": "content",
            "category": "split",
            "html_template": SPLIT_CONTENT,
        },
        # Section variants
        {
            "template_id": "section_modern",
            "name": "Modern Section",
            "content_type": "section",
            "category": "modern",
            "html_template": MODERN_TITLE.replace("slide-title-modern", "slide-section-modern").replace("subtitle", "section-subtitle"),
        },
        {
            "template_id": "section_split",
            "name": "Split Section",
            "content_type": "section",
            "category": "split",
            "html_template": SPLIT_TITLE,
        }
    ]

    print(f"\n📄 Seeding {len(layout_templates)} Layout Variant Templates...")
    for tmpl in layout_templates:
        try:
            await client.mutation("templates:upsertTemplate", {
                "templateId": tmpl["template_id"],
                "name": tmpl["name"],
                "description": f"{tmpl['name']} Layout Variant",
                "contentType": tmpl["content_type"],
                "category": tmpl["category"],
                "htmlTemplate": tmpl["html_template"],
                "cssStyles": "",
                "isActive": True,
                "isSystem": True,
                "version": "1.0",
            })
            print(f"  ✅ Upserted template variant: {tmpl['template_id']}")
        except Exception as e:
            print(f"  ❌ Failed to upsert template variant {tmpl['template_id']}: {e}")


    # 4. Seed Theme Palettes
    print(f"\n🎨 Seeding {len(PALETTES)} Theme Palettes...")
    palette_map = {} # map name -> id for config linking
    
    for pal in PALETTES:
        try:
            pal_id = await client.mutation("templates:upsertThemePalette", {
                "name": pal["name"],
                "category": pal["category"],
                "colors": pal["colors"],
                "isDefault": pal["is_default"],
                "isSystem": True,
            })
            palette_map[pal["name"]] = pal_id
            print(f"  ✅ Upserted palette: {pal['name']}")
        except Exception as e:
            print(f"  ❌ Failed to upsert palette {pal['name']}: {e}")

    # 5. Seed Theme Configs
    print(f"\n⚙️ Seeding {len(THEMES)} Theme Configs...")
    for theme in THEMES:
        try:
            palette_id = palette_map.get(theme["palette_name"])
            
            # Determine layout style (logic from seed_layouts.py)
            layout_style = "default"
            theme_name = theme["name"].lower()
            if "modern" in theme_name: # modern is redundant check if included in name logic below but safe
                 layout_style = "modern"
            elif "ocean" in theme_name or "azure" in theme_name or "modern" in theme_name:
                layout_style = "modern"
            elif "dark" in theme_name or "night" in theme_name or "bold" in theme_name:
                layout_style = "split"
            
            await client.mutation("templates:upsertThemeConfig", {
                "themeId": theme["theme_id"],
                "name": theme["name"],
                "description": theme["description"],
                "paletteId": palette_id,
                "typography": theme["typography"],
                "spacing": theme["spacing"],
                "borders": theme["borders"],
                "cssOverrides": theme["css_overrides"],
                "layoutStyle": layout_style,
                "isActive": True,
                "isSystem": True,
            })
            print(f"  ✅ Upserted theme: {theme['theme_id']} (Style: {layout_style})")
        except Exception as e:
            print(f"  ❌ Failed to upsert theme {theme['theme_id']}: {e}")

    print("\n✨ Migration Complete!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(seed_convex())
