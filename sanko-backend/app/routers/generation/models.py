# Backwards compatibility shim
# Redirects old import paths to new locations

from app.models import (
    EnrichedSlide,
    EnrichedContent,
    CitationMetadata,
)

__all__ = [
    "EnrichedSlide",
    "EnrichedContent",
    "CitationMetadata",
]
