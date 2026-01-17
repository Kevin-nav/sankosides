"""add_uuid_defaults_to_users_and_projects

Revision ID: a64fcb3d17d3
Revises: 6d4d7b468a6c
Create Date: 2025-12-25 17:43:10.293406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a64fcb3d17d3'
down_revision: Union[str, Sequence[str], None] = '6d4d7b468a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add database-level UUID default for users.id
    op.alter_column(
        'users',
        'id',
        server_default=sa.text('gen_random_uuid()')
    )
    
    # Add database-level UUID default for projects.id
    op.alter_column(
        'projects',
        'id',
        server_default=sa.text('gen_random_uuid()')
    )
    
    # Also add timestamp defaults while we're at it
    op.alter_column(
        'users',
        'created_at',
        server_default=sa.text('now()')
    )
    op.alter_column(
        'users',
        'updated_at',
        server_default=sa.text('now()')
    )
    op.alter_column(
        'users',
        'subscription_tier',
        server_default='free'
    )
    
    op.alter_column(
        'projects',
        'created_at',
        server_default=sa.text('now()')
    )
    op.alter_column(
        'projects',
        'updated_at',
        server_default=sa.text('now()')
    )
    op.alter_column(
        'projects',
        'status',
        server_default='draft'
    )
    op.alter_column(
        'projects',
        'title',
        server_default='Untitled Project'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove defaults
    op.alter_column('users', 'id', server_default=None)
    op.alter_column('users', 'created_at', server_default=None)
    op.alter_column('users', 'updated_at', server_default=None)
    op.alter_column('users', 'subscription_tier', server_default=None)
    
    op.alter_column('projects', 'id', server_default=None)
    op.alter_column('projects', 'created_at', server_default=None)
    op.alter_column('projects', 'updated_at', server_default=None)
    op.alter_column('projects', 'status', server_default=None)
    op.alter_column('projects', 'title', server_default=None)
