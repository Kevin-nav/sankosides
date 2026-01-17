"""
Template Models for Database Storage

SQLAlchemy models for storing slide templates, themes, and color palettes.
These replace the hardcoded Python templates in app/templates/layouts/.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class SlideTemplate(Base):
    """
    Database-stored slide template.
    
    Replaces hardcoded templates like TitleTemplate, ContentTemplate, etc.
    HTML templates use Jinja2 syntax with variables like:
      {{ slide.title }}, {{ slide.bullet_points }}, etc.
    """
    __tablename__ = "slide_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Template identification
    template_id = Column(String(50), unique=True, nullable=False, index=True)  # 'title', 'content', etc.
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String(50), nullable=False)  # For template selection logic
    category = Column(String(50), default="general")  # academic, business, creative
    
    # Template content
    html_template = Column(Text, nullable=False)  # Jinja2 template
    css_styles = Column(Text, nullable=True)      # Template-specific CSS
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=True)  # System templates can't be deleted by users
    version = Column(String(20), default="1.0.0")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThemePalette(Base):
    """
    Reusable color palettes.
    
    Users can create custom palettes or use preset ones.
    Each palette defines the 8 core colors used in slide rendering.
    """
    __tablename__ = "theme_palettes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Palette identification
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="general")  # academic, business, creative, minimal
    
    # Color values (stored as JSON for flexibility)
    colors = Column(JSONB, nullable=False)
    # Expected structure:
    # {
    #   "primary": "#6366F1",
    #   "secondary": "#EC4899",
    #   "accent": "#14B8A6",
    #   "background": "#FFFFFF",
    #   "surface": "#F8FAFC",
    #   "text_primary": "#0F172A",
    #   "text_secondary": "#64748B",
    #   "border": "#E2E8F0"
    # }
    
    # Flags
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    themes = relationship("ThemeConfig", back_populates="palette")


class ThemeConfig(Base):
    """
    Complete theme configuration.
    
    Combines a color palette with typography, spacing, and border settings.
    This is what gets applied to slides during rendering.
    """
    __tablename__ = "theme_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Theme identification
    theme_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Link to color palette
    palette_id = Column(UUID(as_uuid=True), ForeignKey("theme_palettes.id"), nullable=True)
    
    # Typography settings (JSON)
    typography = Column(JSONB, nullable=True)
    # Expected structure:
    # {
    #   "font_heading": "Inter",
    #   "font_body": "Inter",
    #   "font_size_title": "48px",
    #   "font_size_heading": "32px",
    #   "font_size_body": "18px",
    #   "font_size_caption": "14px",
    #   "font_weight_title": "700",
    #   "font_weight_heading": "600"
    # }
    
    # Spacing settings (JSON)
    spacing = Column(JSONB, nullable=True)
    # Expected structure:
    # {
    #   "xs": "8px",
    #   "sm": "16px",
    #   "md": "24px",
    #   "lg": "32px",
    #   "xl": "48px"
    # }
    
    # Border/shadow settings (JSON)
    borders = Column(JSONB, nullable=True)
    # Expected structure:
    # {
    #   "radius_sm": "4px",
    #   "radius_md": "8px",
    #   "radius_lg": "12px",
    #   "shadow_sm": "0 1px 2px rgba(0,0,0,0.05)",
    #   "shadow_md": "0 4px 6px rgba(0,0,0,0.1)"
    # }
    
    # Theme-specific CSS overrides (layout, positioning, decorations)
    # This CSS is injected after base styles to customize each theme's look
    css_overrides = Column(Text, nullable=True)
    
    # Layout Style (e.g., 'default', 'modern', 'split', 'bold')
    # Determines which HTML template variant to use
    layout_style = Column(String(50), default="default")
    
    # Flags
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    palette = relationship("ThemePalette", back_populates="themes")
