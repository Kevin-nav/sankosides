"""
Generation Router Models

Pydantic models for request/response validation.
Extracted from generation.py for better modularity.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class GenerationMode(str, Enum):
    """The three generation engines from the plan."""
    REPLICA = "replica"          # Image of existing slide -> recreate
    SYNTHESIS = "synthesis"      # Documents -> extract and structure
    DEEP_RESEARCH = "deep_research"  # Topic -> research and create


class StartGenerationRequest(BaseModel):
    """Request to start a new generation session."""
    mode: GenerationMode
    topic: Optional[str] = None  # For DEEP_RESEARCH mode
    project_id: Optional[str] = None  # Link to existing project
    university_profile: Optional[Dict[str, Any]] = None  # User's university settings
    prompt_overrides: Optional[Dict[str, str]] = None  # For Playground


class StartGenerationResponse(BaseModel):
    """Response after starting generation."""
    session_id: str
    interaction_id: Optional[str] = None
    status: str
    clarification_question: Optional[str] = None
    message: str


class ClarifyRequest(BaseModel):
    """User's answer to a clarification question."""
    session_id: str
    answer: str


class ClarifyResponse(BaseModel):
    """Response after processing clarification."""
    session_id: str
    status: str
    next_question: Optional[str] = None
    blueprint_ready: bool = False
    message: str
    thinking: Optional[str] = None  # Agent's thought process (observability)


class BlueprintSlide(BaseModel):
    """A single slide in the blueprint."""
    order: int
    title: str
    content_type: str  # "title", "overview", "content", "conclusion", etc.
    key_points: List[str]
    has_equation: bool = False
    has_diagram: bool = False


class BlueprintResponse(BaseModel):
    """The slide blueprint for user approval."""
    session_id: str
    title: str
    slide_count: int
    slides: List[BlueprintSlide]
    estimated_generation_time_seconds: int


class ApproveRequest(BaseModel):
    """Request to approve the blueprint and start generation."""
    session_id: str
    modifications: Optional[Dict[str, Any]] = None  # Optional user tweaks


class ApproveResponse(BaseModel):
    """Response after approving blueprint."""
    session_id: str
    status: str
    message: str

# =============================================================================
# ENRICHED CONTENT MODELS (Moved from planner.py / academic_search_tool.py)
# =============================================================================

class CitationMetadata(BaseModel):
    """
    Structured citation metadata.
    
    This is the data format - actual string formatting is done by
    the render service using citation-js (APA, IEEE, etc).
    """
    # Core fields (all optional/with defaults for LLM flexibility)
    title: str = Field(default="", description="Title of the work")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    year: str = Field(default="", description="Publication year")
    
    # Source information
    source_type: str = Field(default="article", description="article, book, webpage, etc.")
    source_name: Optional[str] = Field(None, description="Journal/book/website name")
    
    # Identifiers (at least one should be present)
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    url: Optional[str] = Field(None, description="URL to the source")
    arxiv_id: Optional[str] = Field(None, description="ArXiv identifier")
    
    # Additional metadata
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = Field(None, description="Abstract if available")
    
    # Verification
    verified: bool = Field(default=False, description="Whether DOI/URL was verified")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance to query")
    
    @field_validator('year', mode='before')
    @classmethod
    def coerce_year_to_str(cls, v):
        """Handle dict, int, or other types by converting to string."""
        if v is None:
            return ""
        if isinstance(v, dict):
            # LLM might return nested dict - try to extract a year value
            if 'year' in v:
                return str(v['year'])
            # Return empty string if can't extract
            return ""
        if isinstance(v, int):
            return str(v)
        return str(v)


class EnrichedSlide(BaseModel):
    """
    A slide enriched with verified content.
    
    This is the skeleton slide + verified citations, images, and equations.
    """
    order: int = Field(..., ge=1)
    title: str
    bullet_points: List[str] = Field(default_factory=list)
    content_type: str = Field(default="content")
    
    # Verified citations (from AcademicSearchTool)
    citations: List[CitationMetadata] = Field(
        default_factory=list,
        description="Verified citations with DOIs"
    )
    
    # Verified images
    image_url: Optional[str] = Field(
        None,
        description="Verified image URL (passed VisionTool check)"
    )
    image_alt: Optional[str] = Field(
        None,
        description="Image alt text/description"
    )
    
    image_caption: Optional[str] = Field(
        None,
        description="Caption for the image"
    )
    
    # Equations (from source or converted)
    equation_latex: Optional[str] = Field(
        None,
        description="LaTeX equation if needed"
    )
    equation_svg: Optional[str] = Field(
        None,
        description="Pre-rendered SVG for the equation"
    )
    
    # Diagrams (Mermaid code)
    diagram_mermaid: Optional[str] = Field(
        None,
        description="Mermaid diagram code if needed"
    )
    diagram_svg: Optional[str] = Field(
        None,
        description="Pre-rendered SVG for the diagram"
    )
    
    # Speaker notes
    speaker_notes: Optional[str] = Field(None)
    
    # Formatted citations (after render service processing)
    formatted_citations: List[str] = Field(
        default_factory=list,
        description="Pre-formatted citation strings in the selected style (APA, IEEE, etc)"
    )
    
    # Verification status
    all_claims_verified: bool = Field(
        default=False,
        description="Whether all factual claims have sources"
    )
    removed_claims: List[str] = Field(
        default_factory=list,
        description="Claims removed due to lack of verification"
    )


class EnrichedContent(BaseModel):
    """
    Complete presentation content after enrichment.
    
    This is the Planner's output - fully verified content ready
    for the Generator to map to visual components.
    """
    presentation_title: str
    target_audience: str
    
    # From OrderForm
    theme_id: str = Field(default="modern")
    citation_style: str = Field(default="apa")
    
    slides: List[EnrichedSlide] = Field(default_factory=list)
    
    # Quality metrics
    total_citations: int = Field(default=0)
    verified_images: int = Field(default=0)
    removed_claims_count: int = Field(default=0)
    
    def update_metrics(self):
        """Update quality metrics."""
        self.total_citations = sum(len(s.citations) for s in self.slides)
        self.verified_images = sum(1 for s in self.slides if s.image_url)
        self.removed_claims_count = sum(len(s.removed_claims) for s in self.slides)
