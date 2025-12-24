"""
Generation Router Module

Handles the slide generation workflow:
1. Start a new generation session
2. Handle clarification Q&A  
3. Review and approve blueprint
4. Execute generation

Modularized from generation.py for better maintainability.

Note: Router is NOT exported here to avoid circular imports.
Import router directly from generation_legacy or endpoints as needed.
"""

from app.routers.generation.models import (
    GenerationMode,
    StartGenerationRequest,
    StartGenerationResponse,
    ClarifyRequest,
    ClarifyResponse,
    BlueprintSlide,
    BlueprintResponse,
    ApproveRequest,
    ApproveResponse,
    EnrichedContent,
    EnrichedSlide,
    CitationMetadata,
)
from app.routers.generation.session_store import (
    sessions,
    session_events,
    load_sessions,
    save_sessions,
)

__all__ = [
    "GenerationMode",
    "StartGenerationRequest",
    "StartGenerationResponse",
    "ClarifyRequest",
    "ClarifyResponse",
    "BlueprintSlide",
    "BlueprintResponse",
    "ApproveRequest",
    "ApproveResponse",
    "EnrichedContent",
    "EnrichedSlide",
    "CitationMetadata",
    "sessions",
    "session_events",
    "load_sessions",
    "save_sessions",
]
