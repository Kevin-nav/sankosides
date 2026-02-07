
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.convex_client import get_convex_client

TEMPLATES_DIR = Path(__file__).parent.parent / "app" / "templates" / "views"

TEMPLATES_TO_SEED = [
    {
        "templateId": "content",
        "name": "Standard Content",
        "contentType": "content",
        "category": "general",
        "file": "content.html"
    },
    {
        "templateId": "two_column",
        "name": "Split Layout",
        "contentType": "two_column",
        "category": "general",
        "file": "two_column.html"
    },
    {
        "templateId": "title",
        "name": "Cover Slide",
        "contentType": "title",
        "category": "general",
        "file": "title.html"
    },
    {
        "templateId": "timeline",
        "name": "Process Timeline",
        "contentType": "timeline",
        "category": "visual",
        "file": "timeline.html"
    },
    {
        "templateId": "big_stat",
        "name": "Big Statistic",
        "contentType": "big_stat",
        "category": "visual",
        "file": "big_stat.html"
    },
    {
        "templateId": "grid_gallery",
        "name": "Image Grid",
        "contentType": "grid_gallery",
        "category": "visual",
        "file": "grid_gallery.html"
    },
    {
        "templateId": "comparison",
        "name": "Pro/Con Comparison",
        "contentType": "comparison",
        "category": "visual",
        "file": "comparison.html"
    }
]

def seed_templates():
    client = get_convex_client()
    print("🚀 Seeding templates to Convex...")
    
    for tmpl in TEMPLATES_TO_SEED:
        file_path = TEMPLATES_DIR / tmpl["file"]
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        print(f"Uploading {tmpl['templateId']}...")
        
        # Check if exists
        existing = client.query("templates:getTemplateById", {"templateId": tmpl["templateId"]})
        
        args = {
            "templateId": tmpl["templateId"],
            "name": tmpl["name"],
            "contentType": tmpl["contentType"],
            "category": tmpl["category"],
            "htmlTemplate": html_content,
            "isActive": True,
            "isSystem": True,
            "version": "2.0",
        }
        
        if existing:
            # Update
            client.mutation("templates:updateTemplate", {
                "id": existing["_id"],
                "updates": args
            })
            print(f"✅ Updated {tmpl['templateId']}")
        else:
            # Create
            client.mutation("templates:createTemplate", args)
            print(f"✅ Created {tmpl['templateId']}")
            
    print("✨ Seeding complete!")

if __name__ == "__main__":
    seed_templates()
