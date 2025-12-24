"""
Database Configuration and Models

SQLAlchemy setup for SankoSlides backend.
Uses asyncpg for async PostgreSQL connection.
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, create_engine, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings

# Base for all models
Base = declarative_base()


# =============================================================================
# Session Models
# =============================================================================

class PlaygroundSession(Base):
    """
    Stores CrewAI Flow state for playground sessions.
    
    This is a temporary table for development - production will use
    proper user-linked sessions with authentication.
    """
    __tablename__ = "playground_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Flow state (stored as JSON for flexibility)
    flow_state = Column(JSONB, nullable=True)
    order_form = Column(JSONB, nullable=True)       # Clarifier output
    skeleton = Column(JSONB, nullable=True)          # Outliner output  
    planned_content = Column(JSONB, nullable=True)   # Planner output
    refined_content = Column(JSONB, nullable=True)   # Refiner output
    generated_slides = Column(JSONB, nullable=True)  # Generator output
    
    # Tracking
    current_stage = Column(String(50), nullable=True)
    qa_loops_count = Column(Integer, default=0)
    helper_retries = Column(Integer, default=0)
    final_qa_score = Column(Float, nullable=True)
    
    # Status: active, completed, failed
    status = Column(String(20), default="active")
    
    # Relationship to failure reports
    failure_reports = relationship("FailureReport", back_populates="session", cascade="all, delete-orphan")


class FailureReport(Base):
    """
    Stores failure reports for admin review.
    
    When the Helper agent exhausts its retry budget, a failure report
    is generated with full context for debugging.
    """
    __tablename__ = "failure_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("playground_sessions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Failure details
    failing_agent = Column(String(50), nullable=False)
    failure_type = Column(String(50), nullable=False)  # qa_loop_exceeded, malformed_output, etc.
    error_message = Column(Text, nullable=True)
    
    # Context for debugging
    agent_input = Column(JSONB, nullable=True)
    agent_output = Column(JSONB, nullable=True)
    helper_attempts = Column(ARRAY(JSONB), nullable=True)  # Array of helper retry attempts
    
    # Relationship
    session = relationship("PlaygroundSession", back_populates="failure_reports")


# =============================================================================
# Database Engine Setup
# =============================================================================

def get_database_url() -> str:
    """Get database URL from settings, converting for asyncpg if needed."""
    url = settings.database_url
    if url.startswith("postgresql://"):
        # Convert to async URL for asyncpg
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_sync_database_url() -> str:
    """Get synchronous database URL for Alembic migrations."""
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


# Async engine for FastAPI
async_engine = None
AsyncSessionLocal = None


def init_async_db():
    """Initialize async database engine - called on app startup."""
    global async_engine, AsyncSessionLocal
    async_engine = create_async_engine(
        get_database_url(),
        echo=settings.debug,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        async_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_async_session() -> AsyncSession:
    """FastAPI dependency for getting async DB session."""
    if AsyncSessionLocal is None:
        init_async_db()
    async with AsyncSessionLocal() as session:
        yield session


# Sync engine for Alembic
def get_sync_engine():
    """Get synchronous engine for Alembic migrations."""
    return create_engine(get_sync_database_url(), echo=True)
