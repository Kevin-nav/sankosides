"""
Generation Router Endpoints

This module is a placeholder for future endpoint migration.
Endpoints will be gradually moved here from generation_legacy.py.

Note: Do NOT import router from generation_legacy here - it causes circular imports.
Access router directly from generation_legacy where needed.
"""

# Re-export models from the models module for convenience
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
]
