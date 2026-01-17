"""
Layout Models for Database Storage

SQLAlchemy model for storing layout presets.
Users can browse these in a UI and AI can select from them with variety logic.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class LayoutPreset(Base):
    """
    Reusable layout configurations.
    
    Users can browse these in a "Layout Picker" UI.
    AI can select from these based on content type.
    
    The variety_group and variety_weight fields enable the system
    to pick varied layouts and avoid monotonous presentations.
    """
    __tablename__ = "layout_presets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Layout identification
    preset_id = Column(String(50), unique=True, nullable=False, index=True)  # 'two_col_50_50'
    name = Column(String(100), nullable=False)  # "50/50 Two Column"
    description = Column(Text, nullable=True)
    
    # Visual preview (for UI picker)
    thumbnail_url = Column(String(500), nullable=True)
    
    # Layout definition
    css_grid = Column(Text, nullable=True)  # CSS Grid or Flexbox definition
    regions = Column(JSONB, nullable=True)
    # Expected structure:
    # {
    #   "text": "left",
    #   "visual": "right", 
    #   "visual_size": "50%",
    #   "gap": "32px"
    # }
    
    # Categorization
    category = Column(String(50), nullable=True)  # 'two_column', 'full_width', 'split', 'stacked'
    content_types = Column(JSONB, nullable=True)  # ["content", "image", "diagram"] - compatible types
    
    # Variety controls (to avoid monotony)
    variety_group = Column(String(50), nullable=True)  # Layouts in same group are interchangeable
    variety_weight = Column(Float, default=1.0)  # Higher = more likely to be chosen
    
    # Flags
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=True)  # System layouts can't be deleted by users
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
