"""
Survey Models for Database Storage
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class SurveyResponse(Base):
    """
    Beta User Survey Responses.
    """
    __tablename__ = "survey_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User Identification
    email = Column(String(255), nullable=True, index=True)
    
    # Survey Data
    operating_system = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    citation_style = Column(String(100), nullable=True)
    content_source = Column(String(255), nullable=True)
    visual_style = Column(String(255), nullable=True)
    
    # Optional / Future
    additional_feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
