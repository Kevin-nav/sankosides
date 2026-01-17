"""Add layout_presets table

Revision ID: f1a2b3c4d5e6
Revises: fb85f344a4ea
Create Date: 2026-01-17

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '30249cf41c0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create layout_presets table
    op.create_table(
        'layout_presets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('preset_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('css_grid', sa.Text, nullable=True),
        sa.Column('regions', JSONB, nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('content_types', JSONB, nullable=True),
        sa.Column('variety_group', sa.String(50), nullable=True),
        sa.Column('variety_weight', sa.Float, server_default='1.0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_system', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Seed default layout presets
    op.execute("""
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
    """)


def downgrade() -> None:
    op.drop_table('layout_presets')
