"""Script to create the layout_presets table manually"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
import app.core.database as db


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS layout_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preset_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR(500),
    css_grid TEXT,
    regions JSONB,
    category VARCHAR(50),
    content_types JSONB,
    variety_group VARCHAR(50),
    variety_weight FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT true,
    is_system BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_layout_presets_preset_id ON layout_presets(preset_id)
"""

SEED_DATA_SQL = """
INSERT INTO layout_presets (id, preset_id, name, category, content_types, variety_group, variety_weight, regions)
VALUES
    (gen_random_uuid(), 'two_col_50_50', '50/50 Two Column', 'two_column', 
     '["content", "image", "diagram", "equation"]'::jsonb, 'two_column', 1.0,
     '{"text": "left", "visual": "right", "visual_size": "50%"}'::jsonb),
    
    (gen_random_uuid(), 'two_col_60_40', '60/40 Two Column', 'two_column',
     '["content", "image"]'::jsonb, 'two_column', 1.0,
     '{"text": "left", "visual": "right", "visual_size": "40%"}'::jsonb),
    
    (gen_random_uuid(), 'two_col_40_60', '40/60 Two Column', 'two_column',
     '["image", "diagram"]'::jsonb, 'two_column', 0.8,
     '{"text": "left", "visual": "right", "visual_size": "60%"}'::jsonb),
    
    (gen_random_uuid(), 'stacked', 'Stacked Content', 'stacked',
     '["content", "equation"]'::jsonb, 'single_column', 1.0,
     '{"text": "top", "visual": "bottom", "visual_size": "40%"}'::jsonb),
    
    (gen_random_uuid(), 'full_bleed_image', 'Full Bleed Image', 'full_width',
     '["image"]'::jsonb, 'visual_focus', 0.6,
     '{"visual": "full", "visual_size": "100%"}'::jsonb),
    
    (gen_random_uuid(), 'centered_visual', 'Centered Visual', 'centered',
     '["diagram", "equation"]'::jsonb, 'visual_focus', 1.0,
     '{"text": "top", "visual": "center", "visual_size": "60%"}'::jsonb),
    
    (gen_random_uuid(), 'text_only', 'Text Only', 'text',
     '["content", "quote"]'::jsonb, 'text_focus', 1.0,
     '{"text": "full"}'::jsonb)
ON CONFLICT (preset_id) DO NOTHING;
"""


async def create_layout_presets_table():
    print("Initializing DB...")
    db.init_async_db()
    
    async with db.AsyncSessionLocal() as session:
        try:
            print("Creating layout_presets table...")
            await session.execute(text(CREATE_TABLE_SQL))
            await session.execute(text(CREATE_INDEX_SQL))
            await session.commit()
            print("Table created successfully!")
        except Exception as e:
            print(f"Error creating table: {e}")
            await session.rollback()
            return
    
    async with db.AsyncSessionLocal() as session:
        try:
            print("Seeding default layout presets...")
            await session.execute(text(SEED_DATA_SQL))
            await session.commit()
            print("Seed data inserted successfully!")
        except Exception as e:
            print(f"Error seeding data: {e}")
            await session.rollback()
            return
        
        # Verify
        result = await session.execute(text("SELECT COUNT(*) FROM layout_presets"))
        count = result.scalar()
        print(f"Layout presets table now has {count} rows.")


if __name__ == "__main__":
    asyncio.run(create_layout_presets_table())
