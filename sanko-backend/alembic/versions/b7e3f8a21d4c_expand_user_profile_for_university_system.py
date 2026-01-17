"""expand_user_profile_for_university_system

Revision ID: b7e3f8a21d4c
Revises: a64fcb3d17d3
Create Date: 2026-01-01 00:50:00.000000

Adds structured fields to users table for university profile system:
- academic_level: undergraduate, masters, phd, faculty
- academic_year: 1-4 for undergrads
- university_id: references university config (e.g., 'umat')
- department_id: references department within university
- faculty_id: references faculty within university  
- programme_id: specific BSc programme
- presentation_context: last used presentation context
- onboarding_completed: whether user completed onboarding

These fields enable agent context injection for university-specific
formatting rules, citation styles, and STEM-specific diagrams/equations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7e3f8a21d4c'
down_revision: Union[str, Sequence[str], None] = 'a64fcb3d17d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add university profile fields to users table."""
    
    # First, recreate the users table if it was dropped
    # Check if table exists first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'users' not in tables:
        # Create users table with all fields including new ones
        op.create_table(
            'users',
            sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('firebase_uid', sa.String(length=128), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('display_name', sa.String(length=255), nullable=True),
            sa.Column('photo_url', sa.Text(), nullable=True),
            
            # Existing JSONB columns
            sa.Column('university_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            
            # Subscription
            sa.Column('subscription_tier', sa.String(length=50), server_default='free', nullable=True),
            
            # NEW: Structured university profile fields
            sa.Column('academic_level', sa.String(length=50), nullable=True),  # undergraduate, masters, phd, faculty
            sa.Column('academic_year', sa.Integer(), nullable=True),  # 1, 2, 3, 4 for undergrads
            sa.Column('university_id', sa.String(length=100), nullable=True),  # e.g., 'umat'
            sa.Column('faculty_id', sa.String(length=100), nullable=True),  # e.g., 'fmmt'
            sa.Column('department_id', sa.String(length=100), nullable=True),  # e.g., 'mining_engineering'
            sa.Column('programme_id', sa.String(length=200), nullable=True),  # e.g., 'bsc_mining_engineering'
            
            # NEW: Presentation context
            sa.Column('presentation_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            
            # NEW: Onboarding status
            sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email'),
        )
        op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)
        op.create_index('ix_users_university_id', 'users', ['university_id'], unique=False)
    else:
        # Table exists, add new columns
        op.add_column('users', sa.Column('academic_level', sa.String(length=50), nullable=True))
        op.add_column('users', sa.Column('academic_year', sa.Integer(), nullable=True))
        op.add_column('users', sa.Column('university_id', sa.String(length=100), nullable=True))
        op.add_column('users', sa.Column('faculty_id', sa.String(length=100), nullable=True))
        op.add_column('users', sa.Column('department_id', sa.String(length=100), nullable=True))
        op.add_column('users', sa.Column('programme_id', sa.String(length=200), nullable=True))
        op.add_column('users', sa.Column('presentation_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False))
        
        # Add index for university queries
        op.create_index('ix_users_university_id', 'users', ['university_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove university profile fields."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'users' in tables:
        # Drop index first
        op.drop_index('ix_users_university_id', table_name='users')
        
        # Drop new columns
        op.drop_column('users', 'onboarding_completed')
        op.drop_column('users', 'presentation_context')
        op.drop_column('users', 'programme_id')
        op.drop_column('users', 'department_id')
        op.drop_column('users', 'faculty_id')
        op.drop_column('users', 'university_id')
        op.drop_column('users', 'academic_year')
        op.drop_column('users', 'academic_level')
