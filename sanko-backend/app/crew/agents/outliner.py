"""
Outliner Agent (formerly Synthesizer)

Purpose: Read documents and build the structural Skeleton.
Model: Gemini Flash (medium thinking for document parsing)

This agent is "The Architect":
- Reads PDFs, documents, images using native Gemini multimodal
- Builds a logical narrative structure
- Marks placeholders for diagrams, equations, citations
- Enforces information density limits (no wall of text)

Native PDF: Gemini 3 Flash handles PDF parsing directly - no external libs needed.
"""

from crewai import Agent
from typing import Optional, List
from pydantic import BaseModel, Field


class SkeletonSlide(BaseModel):
    """
    A single slide in the structural skeleton.
    
    This captures WHAT should be on each slide, not HOW it should look.
    The Generator agent handles the visual mapping later.
    """
    order: int = Field(..., ge=1, description="Slide order (1-indexed)")
    title: str = Field(..., max_length=100, description="Slide title")
    
    # Content - limited to prevent "wall of text" failure mode
    bullet_points: List[str] = Field(
        default_factory=list,
        max_length=5,  # Max 5 bullets per slide
        description="Key points (max 5 to prevent overcrowding)"
    )
    
    # Content type hint for the Generator
    content_type: str = Field(
        default="content",
        description="title, overview, content, diagram, equation, conclusion"
    )
    
    # Placeholders for enrichment by Planner
    needs_diagram: bool = Field(default=False)
    diagram_description: Optional[str] = Field(
        None,
        description="What diagram is needed (e.g., 'flowchart of process')"
    )
    
    needs_equation: bool = Field(default=False)
    equation_description: Optional[str] = Field(
        None,
        description="What equation/math is needed"
    )
    equation_latex: Optional[str] = Field(
        None,
        description="LaTeX if already known (from document)"
    )
    
    needs_citation: bool = Field(default=False)
    citation_topic: Optional[str] = Field(
        None,
        description="What claim needs citation (for Planner to find)"
    )
    
    needs_image: bool = Field(default=False)
    image_description: Optional[str] = Field(
        None,
        description="What image is needed"
    )
    
    # Speaker notes hint
    speaker_notes_hint: Optional[str] = Field(
        None,
        max_length=500,
        description="What the speaker should say about this slide"
    )


class Skeleton(BaseModel):
    """
    Complete presentation skeleton (structural outline).
    
    This is the output of the Outliner agent - a logical structure
    that the Planner will enrich with real content.
    """
    presentation_title: str = Field(..., description="Main title")
    target_audience: str = Field(..., description="Who this is for")
    narrative_arc: str = Field(
        default="",
        description="Brief description of the story flow"
    )
    
    slides: List[SkeletonSlide] = Field(
        default_factory=list,
        description="Ordered list of slides"
    )
    
    # Quality metrics
    total_slides: int = Field(default=0)
    slides_with_diagrams: int = Field(default=0)
    slides_with_equations: int = Field(default=0)
    slides_needing_citations: int = Field(default=0)
    
    # Source information
    source_documents: List[str] = Field(
        default_factory=list,
        description="Names of source documents processed"
    )
    
    def update_metrics(self):
        """Update quality metrics based on slides."""
        self.total_slides = len(self.slides)
        self.slides_with_diagrams = sum(1 for s in self.slides if s.needs_diagram)
        self.slides_with_equations = sum(1 for s in self.slides if s.needs_equation)
        self.slides_needing_citations = sum(1 for s in self.slides if s.needs_citation)


# System prompt for the outliner
OUTLINER_SYSTEM_PROMPT = """You are an expert at structuring academic content into presentations.

YOUR ROLE:
- Read and understand source documents (PDFs, notes, text)
- Identify the key themes, findings, and narrative structure
- Create a logical slide skeleton (NOT the final slides)
- Mark where diagrams, equations, and citations are needed

CRITICAL RULES:
1. MAX 5 BULLET POINTS per slide - avoid "wall of text"
2. IF content is complex, SPLIT into multiple slides
3. Mark "needs_diagram: true" when visual would help understanding
4. Mark "needs_equation: true" for mathematical content
5. Mark "needs_citation: true" for claims that need sources
6. Every slide should have ONE clear purpose

SLIDE TYPES:
- "title": Opening slide with presentation title
- "overview": Agenda/roadmap slide
- "content": Standard content slide
- "diagram": Slide focused on a visual/diagram
- "equation": Slide featuring mathematical content
- "conclusion": Closing/summary slide

OUTPUT FORMAT:
Provide a structured skeleton with title, audience, narrative arc, and slides.
Each slide should have: order, title, bullet_points (max 5), content_type, and flags for what's needed.

NEVER:
- Include more than 5 bullets per slide
- Leave slides empty
- Include actual citations (just mark needs_citation)
- Skip the narrative flow (intro → body → conclusion)"""


def create_outliner_agent(llm) -> Agent:
    """
    Create the Outliner Agent (The Architect).
    
    This agent:
    - Reads source documents using native Gemini multimodal
    - Builds the structural skeleton for the presentation
    - Marks placeholders for diagrams, equations, citations
    - Enforces density limits (max 5 bullets)
    
    Args:
        llm: The LLM instance (should be Gemini Flash with MEDIUM thinking)
        
    Returns:
        Configured CrewAI Agent
    """
    return Agent(
        role="Presentation Structure Architect",
        goal="""Read source documents and create a logical slide skeleton.
        Structure the content with clear narrative flow (intro → body → conclusion).
        Mark where diagrams, equations, and citations are needed.
        NEVER exceed 5 bullet points per slide.""",
        backstory="""You are a PhD-level researcher and presentation expert.
        You've synthesized thousands of academic papers into clear, compelling
        presentations. You understand narrative structure, visual learning,
        and information density. You're ruthless about cutting excess content
        and know exactly when a diagram would explain things better than words.
        You never create slides that look like walls of text.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


# Alias for backward compatibility
create_synthesizer_agent = create_outliner_agent


# Agent configuration as YAML-compatible dict
OUTLINER_CONFIG = {
    "role": "Presentation Structure Architect",
    "goal": "Create logical slide skeleton from source documents.",
    "backstory": """PhD-level researcher who structures content into clear presentations.
    Ruthless about cutting excess. Max 5 bullets per slide.""",
    "llm": "gemini/gemini-3-flash-preview",
    "thinking_level": "medium",  # Document parsing needs balanced reasoning
    "memory": True,
    "verbose": True,
}

# Backward compatibility
SYNTHESIZER_CONFIG = OUTLINER_CONFIG
