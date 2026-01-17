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
    knowledge_base = Column(JSONB, nullable=True)   # Synthesis output (NEW)
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


class BetaSignup(Base):
    """
    Beta program signup records.
    
    This table is managed by the beta-landing frontend (Next.js/Drizzle).
    We define it here so Alembic is aware of it and won't drop it
    during autogenerate migrations.
    """
    __tablename__ = "beta_signups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Contact Info (Step 1)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    whatsapp = Column(String(50), nullable=True)
    
    # University Info (Step 2)
    university = Column(String(100), nullable=False)
    campus = Column(String(100), nullable=True)
    other_university = Column(String(255), nullable=True)
    academic_level = Column(String(50), nullable=False)
    department = Column(String(255), nullable=True)
    
    # Preferences (Step 3)
    frequency = Column(String(50), nullable=True)
    tools = Column(Text, nullable=True)  # JSON array stored as text
    pain_points = Column(Text, nullable=True)
    expectations = Column(Text, nullable=True)
    referral = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    email_sent_at = Column(DateTime, nullable=True)  # Track when welcome email was sent


class PDFCache(Base):
    """
    Cache PDF file hash → KnowledgeBase mappings.
    
    This is session-independent: the same file produces the same
    KnowledgeBase regardless of which user/session uploads it.
    This saves API costs by avoiding duplicate Gemini processing.
    """
    __tablename__ = "pdf_cache"
    
    # SHA-256 hash of file content (primary key)
    file_hash = Column(String(64), primary_key=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Original filename (for reference only)
    original_filename = Column(String(255), nullable=True)
    
    # R2 storage key for the PDF file
    r2_key = Column(String(500), nullable=False)
    
    # Cached KnowledgeBase (the extraction result)
    knowledge_base = Column(JSONB, nullable=False)
    
    # Processing metadata
    sections_count = Column(Integer, default=0)
    file_size_bytes = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Model used for extraction (for cache invalidation if we upgrade)
    model_version = Column(String(50), default="gemini-3-flash-preview")


class CachedCitation(Base):
    """
    Permanent cache for academic citations.
    
    Stores citations by normalized query and DOI to avoid repeated API calls.
    Part of the 2-tier cache system (Redis for hot cache, PostgreSQL for permanent).
    """
    __tablename__ = "cached_citations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Search/lookup keys
    normalized_query = Column(String(500), nullable=False, index=True)
    doi = Column(String(255), nullable=True, index=True, unique=True)
    arxiv_id = Column(String(50), nullable=True, index=True)
    
    # Full citation data as JSON
    citation_data = Column(JSONB, nullable=False)
    
    # Source tracking
    provider = Column(String(50), nullable=False)  # crossref, openalex, semantic_scholar
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# Frontend-Shared Models (managed here, used by both frontend and backend)
# =============================================================================

class User(Base):
    """
    User accounts linked to Firebase Authentication.
    
    This table is used by the frontend for user profile management
    and authentication state sync.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    photo_url = Column(Text, nullable=True)
    
    # Profile extensions
    university_profile = Column(JSONB, nullable=True)  # {university, major, year, etc.}
    preferences = Column(JSONB, nullable=True)  # User preferences/settings
    
    # Subscription
    subscription_tier = Column(String(50), default="free")  # free, pro, enterprise
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """
    User projects/presentations.
    
    Each project contains the configuration and generated content
    for a single presentation.
    """
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Project metadata
    title = Column(String(255), nullable=False, default="Untitled Project")
    description = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # Project state
    status = Column(String(50), default="draft")  # draft, generating, completed, archived
    
    # Flow state (references PlaygroundSession or inline)
    session_id = Column(UUID(as_uuid=True), ForeignKey("playground_sessions.id"), nullable=True)
    
    # Generated content snapshot
    slides_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="projects")


# =============================================================================
# Database Engine Setup
# =============================================================================

def get_database_url() -> str:
    """Get database URL from settings, converting for asyncpg if needed."""
    url = settings.database_url
    if url.startswith("postgresql://"):
        # Convert to async URL for asyncpg
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # asyncpg doesn't support 'sslmode' parameter - convert to 'ssl'
    # Also remove 'channel_binding' as asyncpg doesn't support it
    if "sslmode=require" in url:
        url = url.replace("sslmode=require", "ssl=require")
    if "sslmode=prefer" in url:
        url = url.replace("sslmode=prefer", "ssl=prefer")
    if "&channel_binding=require" in url:
        url = url.replace("&channel_binding=require", "")
    if "?channel_binding=require&" in url:
        url = url.replace("?channel_binding=require&", "?")
    if "?channel_binding=require" in url:
        url = url.replace("?channel_binding=require", "")
    
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


def get_async_session_local():
    """
    Get the async session factory, initializing if needed.
    
    This is the SAFE way to access AsyncSessionLocal from other modules.
    It avoids the import-time binding issue where the variable is captured
    as None before init_async_db() is called.
    
    Returns:
        async_sessionmaker: The async session factory for creating sessions.
    """
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        init_async_db()
    return AsyncSessionLocal


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
