"""add_layout_style_to_themes

Revision ID: 3a4b5c6d7e8f
Revises: bd7829c63554
Create Date: 2026-01-09 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a4b5c6d7e8f'
down_revision: Union[str, Sequence[str], None] = 'bd7829c63554'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('theme_configs', sa.Column('layout_style', sa.String(length=50), nullable=True, server_default='default'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('theme_configs', 'layout_style')
