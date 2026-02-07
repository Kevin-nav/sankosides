"""
Export Templates, Themes, and Palettes from Neon PostgreSQL to JSON.

This script exports all template system data from Neon
in a format that can be directly seeded into Convex.

Usage:
    cd sanko-backend
    python scripts/export_templates_to_convex.py

Output:
    Creates 'templates_export.json' with data ready for Convex seeding.
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Please check your .env file.")
    exit(1)


async def export_templates():
    """Export all template system data from Neon PostgreSQL."""
    import asyncpg
    
    # Convert standard PostgreSQL URL to asyncpg format
    url = DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgres://", 1)
    
    print(f"Connecting to database...")
    
    try:
        conn = await asyncpg.connect(url)
        print("Connected successfully!")
        
        # =====================================================================
        # Export Templates
        # =====================================================================
        print("\n📄 Exporting templates...")
        templates_rows = await conn.fetch("""
            SELECT 
                template_id, name, description, content_type, category,
                html_template, css_styles, is_active, is_system, version
            FROM slide_templates
            WHERE is_active = true
            ORDER BY template_id
        """)
        
        templates = [
            {
                "templateId": row['template_id'],
                "name": row['name'],
                "description": row['description'],
                "contentType": row['content_type'],
                "category": row['category'],
                "htmlTemplate": row['html_template'],
                "cssStyles": row['css_styles'],
                "isActive": row['is_active'],
                "isSystem": row['is_system'],
                "version": row['version'],
            }
            for row in templates_rows
        ]
        print(f"   Found {len(templates)} templates")
        
        # =====================================================================
        # Export Palettes
        # =====================================================================
        print("\n🎨 Exporting palettes...")
        palettes_rows = await conn.fetch("""
            SELECT 
                id, name, category, colors, is_default, is_system
            FROM theme_palettes
            ORDER BY name
        """)
        
        # Build a mapping of palette UUID -> index for theme references
        palette_uuid_to_index = {}
        palettes = []
        
        for idx, row in enumerate(palettes_rows):
            palette_uuid_to_index[str(row['id'])] = idx
            
            # Colors is already JSONB, should be a dict
            colors = row['colors']
            if isinstance(colors, str):
                colors = json.loads(colors)
            
            palettes.append({
                "name": row['name'],
                "category": row['category'],
                "colors": colors,
                "isDefault": row['is_default'],
                "isSystem": row['is_system'],
            })
        
        print(f"   Found {len(palettes)} palettes")
        
        # =====================================================================
        # Export Themes
        # =====================================================================
        print("\n🎭 Exporting themes...")
        themes_rows = await conn.fetch("""
            SELECT 
                theme_id, name, description, palette_id,
                typography, spacing, borders, css_overrides,
                layout_style, is_active, is_system
            FROM theme_configs
            WHERE is_active = true
            ORDER BY theme_id
        """)
        
        themes = []
        for row in themes_rows:
            # Get palette index for reference
            palette_index = None
            if row['palette_id']:
                palette_index = palette_uuid_to_index.get(str(row['palette_id']))
            
            # Parse JSONB fields
            typography = row['typography']
            spacing = row['spacing']
            borders = row['borders']
            
            if isinstance(typography, str):
                typography = json.loads(typography)
            if isinstance(spacing, str):
                spacing = json.loads(spacing)
            if isinstance(borders, str):
                borders = json.loads(borders)
            
            themes.append({
                "themeId": row['theme_id'],
                "name": row['name'],
                "description": row['description'],
                "paletteIndex": palette_index,  # Will be resolved during seeding
                "typography": typography,
                "spacing": spacing,
                "borders": borders,
                "cssOverrides": row['css_overrides'],
                "layoutStyle": row['layout_style'],
                "isActive": row['is_active'],
                "isSystem": row['is_system'],
            })
        
        print(f"   Found {len(themes)} themes")
        
        await conn.close()
        
        # Save to JSON file
        export_data = {
            "templates": templates,
            "palettes": palettes,
            "themes": themes,
        }
        
        output_path = Path(__file__).parent.parent / "templates_export.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Exported to: {output_path}")
        print(f"   Templates: {len(templates)}")
        print(f"   Palettes: {len(palettes)}")
        print(f"   Themes: {len(themes)}")
        
        return export_data
        
    except Exception as e:
        print(f"ERROR: Failed to connect or query database: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(export_templates())
