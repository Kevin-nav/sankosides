"""add_university_id_to_slide_templates

Revision ID: e2f1a3b5c7d9
Revises: d667c397dc47
Create Date: 2026-01-14 07:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2f1a3b5c7d9'
down_revision: Union[str, Sequence[str], None] = '3a4b5c6d7e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add university_id column to slide_templates for university-specific templates."""
    op.add_column(
        'slide_templates',
        sa.Column('university_id', sa.String(50), nullable=True)
    )
    op.create_index(
        'ix_slide_templates_university_id',
        'slide_templates',
        ['university_id']
    )


def downgrade() -> None:
    """Remove university_id column from slide_templates."""
    op.drop_index('ix_slide_templates_university_id', table_name='slide_templates')
    op.drop_column('slide_templates', 'university_id')
