"""university_configuration_tables

Revision ID: c8f2a1b3e5d7
Revises: b7e3f8a21d4c
Create Date: 2026-01-01 01:10:00.000000

Creates database tables for the university configuration system:
- universities: Core institution data and formatting rules
- faculties: Academic divisions within universities
- departments: Departments within faculties
- programmes: Degree programmes within departments

This database-driven approach enables:
- Easy addition of new universities without code changes
- Admin panel management in the future
- Efficient querying for frontend dropdowns
- Clean separation of data and code
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8f2a1b3e5d7'
down_revision: Union[str, Sequence[str], None] = 'b7e3f8a21d4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create university configuration tables."""
    
    # =========================================================================
    # UNIVERSITIES TABLE
    # =========================================================================
    op.create_table(
        'universities',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('university_id', sa.String(length=100), nullable=False),  # e.g., 'umat'
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=50), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        
        # Academic standards
        sa.Column('default_citation_style', sa.String(length=50), nullable=False),  # harvard, apa, ieee, chicago
        sa.Column('spelling_variant', sa.String(length=20), nullable=False),  # british, american
        sa.Column('unit_system', sa.String(length=20), server_default='si', nullable=False),  # si, imperial
        
        # Branding
        sa.Column('primary_color', sa.String(length=20), server_default='#1E3A5F', nullable=True),
        sa.Column('secondary_color', sa.String(length=20), server_default='#D4AF37', nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        
        # Formatting rules as JSONB for flexibility
        sa.Column('formatting_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Example: {"figure_caption_position": "below", "table_caption_position": "above", ...}
        
        # Feature flags
        sa.Column('compliance_checking_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('custom_templates_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_universities_university_id', 'universities', ['university_id'], unique=True)
    op.create_index('ix_universities_country', 'universities', ['country'], unique=False)
    op.create_index('ix_universities_is_active', 'universities', ['is_active'], unique=False)
    
    # =========================================================================
    # FACULTIES TABLE
    # =========================================================================
    op.create_table(
        'faculties',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('university_id', sa.UUID(), nullable=False),  # FK to universities
        sa.Column('faculty_id', sa.String(length=100), nullable=False),  # e.g., 'fmmt'
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=50), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_faculties_university_id', 'faculties', ['university_id'], unique=False)
    op.create_index('ix_faculties_faculty_id', 'faculties', ['faculty_id'], unique=False)
    # Composite unique: faculty_id must be unique within a university
    op.create_index('ix_faculties_university_faculty', 'faculties', ['university_id', 'faculty_id'], unique=True)
    
    # =========================================================================
    # DEPARTMENTS TABLE
    # =========================================================================
    op.create_table(
        'departments',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('faculty_id', sa.UUID(), nullable=False),  # FK to faculties
        sa.Column('department_id', sa.String(length=100), nullable=False),  # e.g., 'mining_engineering'
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_stem', sa.Boolean(), server_default='true', nullable=False),
        
        # STEM-specific metadata for agent steering (JSONB arrays)
        sa.Column('common_diagram_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Example: ["mine_layout", "geological_cross_section", "drilling_pattern"]
        sa.Column('common_equation_domains', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Example: ["rock_mechanics", "mine_ventilation", "thermodynamics"]
        sa.Column('preferred_journals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Example: ["Ghana Mining Journal", "Mining Engineering"]
        
        # Optional override
        sa.Column('citation_style_override', sa.String(length=50), nullable=True),
        
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculties.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_departments_faculty_id', 'departments', ['faculty_id'], unique=False)
    op.create_index('ix_departments_department_id', 'departments', ['department_id'], unique=False)
    # Composite unique: department_id must be unique within a faculty
    op.create_index('ix_departments_faculty_department', 'departments', ['faculty_id', 'department_id'], unique=True)
    
    # =========================================================================
    # PROGRAMMES TABLE
    # =========================================================================
    op.create_table(
        'programmes',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),  # FK to departments
        sa.Column('programme_id', sa.String(length=200), nullable=False),  # e.g., 'bsc_mining_engineering'
        sa.Column('name', sa.String(length=255), nullable=False),  # e.g., 'BSc Mining Engineering'
        sa.Column('level', sa.String(length=50), nullable=False),  # undergraduate, masters, phd, diploma, certificate
        sa.Column('duration_years', sa.Integer(), nullable=True),  # e.g., 4 for BSc
        sa.Column('is_fee_paying', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_programmes_department_id', 'programmes', ['department_id'], unique=False)
    op.create_index('ix_programmes_programme_id', 'programmes', ['programme_id'], unique=False)
    op.create_index('ix_programmes_level', 'programmes', ['level'], unique=False)
    # Composite unique: programme_id must be unique within a department
    op.create_index('ix_programmes_department_programme', 'programmes', ['department_id', 'programme_id'], unique=True)


def downgrade() -> None:
    """Drop university configuration tables."""
    op.drop_table('programmes')
    op.drop_table('departments')
    op.drop_table('faculties')
    op.drop_table('universities')
