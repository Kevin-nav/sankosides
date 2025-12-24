"""
SankoSlides Tools Package

Tools for agents:
- VisionTool: Image verification using Gemini 3 Flash Vision
- NanoBananaImageTool: Asset generation using Gemini 3 Pro Image
- AcademicSearchTool: Citation finding with DOI verification
- ImageSearchTool: Image search (Unsplash + Google fallback)

CrewAI Wrappers (for agent function calling):
- VisionVerificationTool, ImageGenerationTool, ImageSearchCrewTool, AcademicSearchCrewTool
"""

from app.tools.vision_tool import VisionTool, VisionVerification
from app.tools.image_generation_tool import NanoBananaImageTool, GeneratedAsset
from app.tools.academic_search_tool import AcademicSearchTool, CitationMetadata
from app.tools.image_search_tool import ImageSearchTool, ImageSearchResult

# CrewAI-compatible wrappers
from app.tools.crewai_tools import (
    VisionVerificationTool,
    ImageGenerationTool,
    ImageSearchCrewTool,
    AcademicSearchCrewTool,
    create_crewai_tools,
)

__all__ = [
    # Core tools
    "VisionTool",
    "VisionVerification",
    "NanoBananaImageTool",
    "GeneratedAsset",
    "AcademicSearchTool",
    "CitationMetadata",
    "ImageSearchTool",
    "ImageSearchResult",
    # CrewAI wrappers
    "VisionVerificationTool",
    "ImageGenerationTool",
    "ImageSearchCrewTool",
    "AcademicSearchCrewTool",
    "create_crewai_tools",
]

