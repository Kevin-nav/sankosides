"""
Pydantic Schemas for SankoSlides

All data models used for API request/response validation
and inter-agent communication.
"""

from typing import Optional, List, Dict, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime


# =============================================================================
# Enums
# =============================================================================

class GenerationMode(str, Enum):
    """The three generation engines."""
    REPLICA = "replica"          # Image of existing slide -> recreate
    SYNTHESIS = "synthesis"      # Documents -> extract and structure
    DEEP_RESEARCH = "deep_research"  # Topic -> research and create


class SlideContentType(str, Enum):
    """Types of slides in a presentation."""
    TITLE = "title"
    OVERVIEW = "overview"
    CONTENT = "content"
    DIAGRAM = "diagram"
    EQUATION = "equation"
    IMAGE = "image"
    QUOTE = "quote"
    TWO_COLUMN = "two_column"
    SECTION = "section"
    CONCLUSION = "conclusion"
    REFERENCES = "references"   # Dedicated references slide
    THANK_YOU = "thank_you"     # Simple thank you slide
    TIMELINE = "timeline"
    BIG_STAT = "big_stat"
    GRID_GALLERY = "grid_gallery"
    COMPARISON = "comparison"


# =============================================================================
# Color & Theme Schemas
# =============================================================================

class ColorPalette(BaseModel):
    """Custom color palette for theme overrides."""
    primary: str = Field(default="#3B82F6", description="Primary brand color")
    secondary: str = Field(default="#10B981", description="Secondary accent")
    background: str = Field(default="#FFFFFF", description="Slide background")
    text: str = Field(default="#1F2937", description="Main text color")
    accent: str = Field(default="#F59E0B", description="Highlight/accent color")


# =============================================================================
# Knowledge Base (Synthesis Engine)
# =============================================================================

class DocumentSection(BaseModel):
    """A specific section of the uploaded document."""
    title: str = Field(..., description="Section header or topic")
    content: str = Field(..., description="Full text and latex content")
    visuals: List[str] = Field(default_factory=list, description="Visual descriptions in this section")
    page_range: str = Field(default="", description="e.g., '1-3'")
    section_id: str = Field(
        default="",
        description="Stable section identifier for deterministic retrieval and citations",
    )
    document_id: str = Field(
        default="",
        description="Stable document identifier (typically file hash)",
    )
    document_name: str = Field(
        default="",
        description="Original source filename",
    )
    page_start: Optional[int] = Field(default=None, ge=1, description="First page in section")
    page_end: Optional[int] = Field(default=None, ge=1, description="Last page in section")
    chunk_index: Optional[int] = Field(default=None, ge=0, description="Extraction chunk index")
    content_hash: str = Field(
        default="",
        description="Hash of section content for traceability",
    )

    @model_validator(mode="after")
    def _validate_page_start_end(self):
        if self.page_start is not None and self.page_end is not None and self.page_start > self.page_end:
            raise ValueError("Invalid page range: page_start must be <= page_end")
        return self


class KnowledgeBase(BaseModel):
    """Structured knowledge extracted from user documents."""
    summary: str = Field(..., description="High-level overview of the entire document set")
    sections: List[DocumentSection] = Field(default_factory=list, description="Detailed content chunks")
    
    def get_section_titles(self) -> List[str]:
        return [s.title for s in self.sections]


# =============================================================================
# Clarification Conversation Tracking
# =============================================================================

class ClarificationMessage(BaseModel):
    """A single message in the clarification conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GatheredInfo(BaseModel):
    """
    Track what information has been gathered during clarification.
    
    This model progressively tracks what the user has provided,
    preventing the agent from asking for the same info twice.
    """
    # Flags for what we have
    has_title: bool = Field(default=False, description="Title/topic provided")
    has_audience: bool = Field(default=False, description="Target audience provided")
    has_slide_count: bool = Field(default=False, description="Number of slides provided")
    has_focus_areas: bool = Field(default=False, description="Focus areas provided")
    has_emphasis_style: bool = Field(default=False, description="Emphasis style provided")
    has_tone: bool = Field(default=False, description="Tone preference provided")
    has_citation_style: bool = Field(default=False, description="Citation style provided")
    has_references_placement: bool = Field(default=False, description="Reference placement provided")
    has_theme: bool = Field(default=False, description="Theme preference provided")
    # Note: speaker notes not currently supported, field removed
    
    # Partial values gathered so far (before final OrderForm)
    title: Optional[str] = Field(default=None, description="Presentation title/topic")
    audience: Optional[str] = Field(default=None, description="Target audience")
    slide_count: Optional[int] = Field(default=None, description="Requested slide count")
    focus_areas: List[str] = Field(default_factory=list, description="Topics to emphasize")
    key_topics: List[str] = Field(default_factory=list, description="Main topics to cover")
    emphasis_style: Optional[Literal["detailed", "concise", "visual-heavy"]] = None
    tone: Optional[Literal["academic", "casual", "technical", "persuasive"]] = None
    citation_style: Optional[Literal["apa", "ieee", "harvard", "chicago"]] = None
    references_placement: Optional[Literal["distributed", "last_slide"]] = None
    theme: Optional[str] = Field(default=None, description="Theme preference")
    # Note: speaker notes not currently supported
    special_requests: Optional[str] = Field(default=None, description="Any special requirements")
    
    # User preferences for agent autonomy
    let_agent_decide_title: bool = Field(default=False, description="User said to decide title")
    let_agent_decide_theme: bool = Field(default=False, description="User said to decide theme")
    let_agent_decide_citation: bool = Field(default=False, description="User said to decide citation style")
    
    # Confirmation tracking
    confirmation_sent: bool = Field(default=False, description="Whether confirmation was sent to user")
    user_confirmed: bool = Field(default=False, description="Whether user confirmed the details")
    
    # Document acknowledgment tracking
    document_acknowledged: bool = Field(default=False, description="Whether document has been acknowledged")
    
    # Source preference tracking (PDF-only vs hybrid vs research-only)
    source_type: Optional[Literal["pdf_only", "pdf_plus_research", "research_only"]] = Field(
        default=None,
        description="Where content should come from: pdf_only, pdf_plus_research, or research_only"
    )
    has_source_preference: bool = Field(
        default=False,
        description="Whether user has specified their source preference"
    )
    
    def get_missing_required(self) -> List[str]:
        """Get list of required fields that are still missing."""
        missing = []
        if not self.has_title and not self.let_agent_decide_title:
            missing.append("presentation title or topic")
        if not self.has_audience:
            missing.append("target audience")
        if not self.has_slide_count:
            missing.append("number of slides")
        if not self.has_focus_areas:
            missing.append("key focus areas or topics to cover")
        return missing
    
    def get_missing_optional(self) -> List[str]:
        """Get list of optional fields that could be gathered."""
        missing = []
        if not self.has_emphasis_style:
            missing.append("emphasis style (detailed/concise/visual-heavy)")
        if not self.has_tone:
            missing.append("tone (academic/casual/technical/persuasive)")
        if not self.has_citation_style:
            missing.append("citation style (APA/IEEE/Harvard/Chicago)")
        if not self.has_references_placement:
            missing.append("references placement (distributed/last slide)")
        if not self.has_theme and not self.let_agent_decide_theme:
            missing.append("theme preference")
        return missing
    
    def is_complete_enough(self) -> bool:
        """Check if we have enough info to proceed (all required fields)."""
        return len(self.get_missing_required()) == 0
    
    def is_ready_for_confirmation(self) -> bool:
        """Check if we should ask for confirmation (has most info)."""
        required_complete = len(self.get_missing_required()) == 0
        optional_missing = len(self.get_missing_optional())
        # Ready for confirmation if required is complete and at most 2 optional missing
        return required_complete and optional_missing <= 2
    
    def needs_confirmation(self) -> bool:
        """Check if we need to send confirmation before completing."""
        return self.is_ready_for_confirmation() and not self.confirmation_sent
    
    def is_fully_confirmed(self) -> bool:
        """Check if user has confirmed and we can output JSON."""
        return self.confirmation_sent and self.user_confirmed


# =============================================================================
# Clarifier Output - Enhanced OrderForm
# =============================================================================


class OrderForm(BaseModel):
    """
    Enhanced Contract from Clarifier agent.
    
    Captures ALL user preferences for slide generation,
    including new fields for focus, emphasis, and references.
    """
    # Theme selection
    theme_id: str = Field(
        default="modern",
        description="Theme ID: academic, modern, minimal, dark"
    )
    color_overrides: Optional[ColorPalette] = Field(
        None,
        description="Optional custom colors to override theme defaults"
    )
    
    # Academic settings
    citation_style: Literal["apa", "ieee", "harvard", "chicago"] = Field(
        default="apa",
        description="Citation formatting style"
    )
    
    # Presentation settings
    tone: Literal["academic", "casual", "technical", "persuasive"] = Field(
        default="academic",
        description="Overall presentation tone"
    )
    target_audience: str = Field(
        default="General academic",
        description="Who will view this presentation"
    )
    target_slides: int = Field(
        default=10,
        ge=3,
        le=50,
        description="Target number of slides"
    )
    
    # Content scope
    presentation_title: str = Field(
        default="",
        description="Main title for the presentation"
    )
    key_topics: List[str] = Field(
        default_factory=list,
        description="Main topics to cover"
    )
    
    # NEW: Enhanced fields from clarification
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Key topics the user wants to emphasize"
    )
    emphasis_style: Literal["detailed", "concise", "visual-heavy"] = Field(
        default="detailed",
        description="How content should be presented"
    )
    references_placement: Literal["distributed", "last_slide"] = Field(
        default="distributed",
        description="Where to place citation references"
    )
    special_requests: str = Field(
        default="",
        description="Free-form notes from clarification"
    )
    template_preferences: Dict[int, str] = Field(
        default_factory=dict,
        description="Per-slide template preferences (slide_order -> template_type)"
    )
    
    # Special requirements
    include_speaker_notes: bool = Field(
        default=False,
        description="Whether to generate speaker notes (not currently supported)"
    )
    
    # Session tracking
    is_complete: bool = Field(
        default=False,
        description="Whether negotiation is complete"
    )
    clarification_notes: str = Field(
        default="",
        description="Full notes from clarification conversation"
    )


# =============================================================================
# Outliner Output - Skeleton
# =============================================================================

class SkeletonSlide(BaseModel):
    """A single slide in the structural skeleton."""
    order: int = Field(..., ge=1, description="Slide order (1-indexed)")
    title: str = Field(..., max_length=100, description="Slide title")
    
    # Brief description for user review
    description: str = Field(
        default="",
        max_length=200,
        description="One-sentence description of what this slide covers"
    )
    
    # Content type
    content_type: SlideContentType = Field(
        default=SlideContentType.CONTENT
    )
    
    # Flags for what's needed
    needs_diagram: bool = Field(default=False)
    diagram_description: Optional[str] = None
    
    needs_equation: bool = Field(default=False)
    equation_description: Optional[str] = None
    
    needs_citation: bool = Field(default=False)
    citation_topic: Optional[str] = None
    
    needs_image: bool = Field(default=False)
    image_description: Optional[str] = None


class Skeleton(BaseModel):
    """Complete presentation skeleton from Outliner."""
    presentation_title: str
    target_audience: str
    narrative_arc: str = Field(default="", description="Brief story flow")
    slides: List[SkeletonSlide] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)


# =============================================================================
# Planner Output - PlannedContent
# =============================================================================

class CitationMetadata(BaseModel):
    """Citation metadata for academic references."""
    title: str = Field(default="", description="Title of the work")
    authors: List[str] = Field(default_factory=list)
    year: str = Field(default="")
    source_type: str = Field(default="article")
    source_name: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    arxiv_id: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = None
    verified: bool = Field(default=False)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    @field_validator('year', mode='before')
    @classmethod
    def coerce_year_to_str(cls, v):
        if v is None:
            return ""
        if isinstance(v, dict):
            return str(v.get('year', ''))
        return str(v)


class ImageCitation(BaseModel):
    """Citation metadata specifically for images."""
    source_type: Literal["original", "adapted", "screenshot", "generated", "stock", "creative_commons"] = Field(
        default="original",
        description="Type of image source"
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Where the image came from (e.g., 'NASA', 'Author's own')"
    )
    creator: Optional[str] = Field(
        default=None,
        description="Original creator/photographer"
    )
    year: Optional[str] = Field(default=None)
    license: Optional[str] = Field(
        default=None,
        description="License type (CC BY 4.0, Public Domain, etc.)"
    )
    url: Optional[str] = Field(default=None)
    adapted_from: Optional[str] = Field(
        default=None,
        description="If adapted, original source citation"
    )
    
    def to_citation_string(self, style: str = "harvard") -> str:
        """Generate formatted citation string."""
        if self.source_type == "original":
            return "Author's own work"
        elif self.source_type == "generated":
            return "AI-generated image"
        elif self.source_type == "adapted":
            return f"Adapted from {self.adapted_from}" if self.adapted_from else "Adapted"
        else:
            parts = []
            if self.creator:
                parts.append(self.creator)
            if self.year:
                parts.append(f"({self.year})")
            if self.source_name:
                parts.append(self.source_name)
            if self.license:
                parts.append(f"[{self.license}]")
            return " ".join(parts) if parts else "Unknown source"


class ResearchNeed(BaseModel):
    """A claim or fact that needs academic backing."""
    claim: str = Field(..., description="The claim or statement needing support")
    query: str = Field(..., description="Search query to find supporting papers")
    intent: Literal["statistic", "definition", "methodology", "finding", "common_fact", "fact"] = Field(
        default="finding",
        description="What type of support is needed"
    )
    is_common_knowledge: bool = Field(
        default=False,
        description="If True, this is common knowledge and can be stated without deep research"
    )


class ResearchFact(BaseModel):
    """A fact extracted from a research paper and used in slide content."""
    fact: str = Field(..., description="The extracted fact or finding")
    source: "CitationMetadata" = Field(..., description="The paper this fact came from")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Confidence that this fact supports the claim"
    )
    extraction_source: Literal["abstract", "tldr", "full_text", "user_upload"] = Field(
        default="abstract",
        description="Where in the paper this fact was extracted from"
    )
    used_in_bullet: Optional[int] = Field(
        default=None,
        description="Index of the bullet point where this fact was integrated"
    )
    evidence_ref: Optional[str] = Field(
        default=None,
        description="Evidence reference id tied to the supporting source section",
    )


class EvidenceRef(BaseModel):
    """Deterministic evidence pointer for zero-hallucination claim grounding."""
    evidence_id: str = Field(
        default="",
        description="Unique id for this evidence record",
    )
    section_id: str = Field(
        default="",
        description="KnowledgeBase section_id that supports the claim",
    )
    page_range: str = Field(
        default="",
        description="Page range used as evidence (e.g., '12-13')",
    )
    quote_excerpt: str = Field(
        default="",
        description="Short supporting excerpt from source content",
    )
    quote_hash: str = Field(
        default="",
        description="Hash of quote excerpt to make evidence deterministic",
    )
    claim: str = Field(
        default="",
        description="Claim supported by this evidence",
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Confidence score for claim-evidence match",
    )
    source_type: Literal["document", "external"] = Field(
        default="document",
        description="Whether evidence came from uploaded documents or external research",
    )


class PlannedSlide(BaseModel):
    """Slide after Planner processing - with full content and placeholders."""
    order: int = Field(..., ge=1)
    title: str
    content_type: SlideContentType = Field(default=SlideContentType.CONTENT)
    
    # Full content (written by Planner)
    bullet_points: List[str] = Field(default_factory=list)
    
    # Placeholders for Refiner to fill
    equation_placeholder: Optional[str] = Field(
        None, description="Description of equation needed (e.g., 'Quadratic formula')"
    )
    diagram_placeholder: Optional[str] = Field(
        None, description="Description of diagram needed"
    )
    citation_queries: List[str] = Field(
        default_factory=list, description="Search queries for citations"
    )
    image_query: Optional[str] = Field(
        None, description="Image search query"
    )
    
    speaker_notes: Optional[str] = None
    template_type: Optional[str] = Field(
        None, description="Which layout template to use"
    )
    
    # Research-driven content generation
    research_needs: List["ResearchNeed"] = Field(
        default_factory=list,
        description="Claims that need academic backing with search queries"
    )
    claims: List[str] = Field(
        default_factory=list,
        description="Atomic factual claims extracted from bullet points",
    )
    evidence_refs: List[EvidenceRef] = Field(
        default_factory=list,
        description="Evidence pointers that must back each factual claim",
    )


class PlannedContent(BaseModel):
    """Complete content after Planner - ready for Refiner."""
    presentation_title: str
    target_audience: str
    theme_id: str = Field(default="modern")
    citation_style: str = Field(default="apa")
    slides: List[PlannedSlide] = Field(default_factory=list)


# =============================================================================
# Refiner Output - RefinedContent
# =============================================================================

class RefinedSlide(BaseModel):
    """Slide after Refiner - with all assets rendered."""
    order: int = Field(..., ge=1)
    title: str
    content_type: SlideContentType = Field(default=SlideContentType.CONTENT)
    
    # Final content
    bullet_points: List[str] = Field(default_factory=list)
    
    # Rendered assets
    equation_svg: Optional[str] = Field(None, description="Rendered LaTeX SVG")
    equation_latex: Optional[str] = Field(None, description="Original LaTeX source")
    diagram_svg: Optional[str] = Field(None, description="Rendered Mermaid SVG")
    diagram_mermaid: Optional[str] = Field(None, description="Original Mermaid source")
    
    # Citations
    citations: List[CitationMetadata] = Field(default_factory=list)
    formatted_citations: List[str] = Field(
        default_factory=list, description="Pre-formatted citation strings"
    )
    
    # Images
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
    image_caption: Optional[str] = None
    image_citation: Optional["ImageCitation"] = Field(
        default=None,
        description="Citation/attribution for the slide's image"
    )
    
    # Layout
    template_type: str = Field(default="content")
    speaker_notes: Optional[str] = None
    
    # Quality tracking
    all_claims_verified: bool = Field(default=False)
    removed_claims: List[str] = Field(default_factory=list)
    
    # Layout control fields (for Visual QA feedback loop)
    layout_preset_id: Optional[str] = Field(
        default=None,
        description="ID of layout preset (e.g., 'two_col_50_50', 'full_bleed_image')"
    )
    image_size_hint: Optional[Literal["small", "medium", "large", "fit", "auto"]] = Field(
        default="auto",
        description="Size hint for images"
    )
    visual_position: Optional[Literal["left", "right", "top", "bottom", "center"]] = Field(
        default="right",
        description="Position for visual elements (images, diagrams, formulas)"
    )
    content_balance: Optional[Literal["text_heavy", "visual_heavy", "balanced"]] = Field(
        default="balanced",
        description="Content weight distribution"
    )
    
    # Title slide specific metadata
    author: Optional[str] = None
    supervisor: Optional[str] = None
    degree: Optional[str] = None
    date: Optional[str] = None
    
    # Research-driven content tracking
    research_facts: List["ResearchFact"] = Field(
        default_factory=list,
        description="Facts extracted from papers and used in this slide's content"
    )
    claims: List[str] = Field(
        default_factory=list,
        description="Atomic factual claims present in final bullet points",
    )
    evidence_refs: List[EvidenceRef] = Field(
        default_factory=list,
        description="Verified evidence pointers for all factual claims",
    )
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Claims rejected due to missing supporting evidence",
    )


class RefinedContent(BaseModel):
    """Complete content after Refiner - ready for Generator."""
    presentation_title: str
    target_audience: str
    theme_id: str = Field(default="modern")
    citation_style: str = Field(default="apa")
    slides: List[RefinedSlide] = Field(default_factory=list)
    
    # Quality metrics
    total_citations: int = Field(default=0)
    verified_images: int = Field(default=0)
    equations_rendered: int = Field(default=0)
    diagrams_rendered: int = Field(default=0)
    
    def update_metrics(self):
        """Update quality metrics from slides."""
        self.total_citations = sum(len(s.citations) for s in self.slides)
        self.verified_images = sum(1 for s in self.slides if s.image_url)
        self.equations_rendered = sum(1 for s in self.slides if s.equation_svg)
        self.diagrams_rendered = sum(1 for s in self.slides if s.diagram_svg)


# =============================================================================
# Generator Output - GeneratedSlides
# =============================================================================

class GeneratedSlide(BaseModel):
    """A single generated HTML slide."""
    order: int
    title: str
    theme_id: str
    color_palette: Optional[ColorPalette] = None
    rendered_html: str = Field(..., description="Complete HTML for this slide")
    speaker_notes: Optional[str] = None


class GeneratedPresentation(BaseModel):
    """Complete presentation with HTML slides."""
    title: str
    slides: List[GeneratedSlide] = Field(default_factory=list)
    theme_id: str
    
    # Metadata
    total_slides: int = Field(default=0)
    generation_time_ms: int = Field(default=0)


# =============================================================================
# Visual QA Output
# =============================================================================

class QAResult(BaseModel):
    """Result from Visual QA evaluation of a slide."""
    slide_order: int
    score: float = Field(..., ge=0, le=100)
    issues: List[str] = Field(default_factory=list)
    screenshot_base64: Optional[str] = None
    passed: bool = Field(default=False)
    iterations: int = Field(default=1)


class QAReport(BaseModel):
    """Complete QA report for a presentation."""
    session_id: str
    slides: List[QAResult] = Field(default_factory=list)
    average_score: float = Field(default=0.0)
    all_passed: bool = Field(default=False)
    total_iterations: int = Field(default=0)


# =============================================================================
# Beta Survey
# =============================================================================

class SurveySubmission(BaseModel):
    """Beta survey submission data."""
    email: Optional[str] = Field(None, description="User email for linkage")
    university: Optional[str] = None
    course: Optional[str] = None
    citation_style: Optional[str] = None
    slide_frequency: Optional[str] = None
    pain_points: Optional[str] = None
    additional_feedback: Optional[str] = None

