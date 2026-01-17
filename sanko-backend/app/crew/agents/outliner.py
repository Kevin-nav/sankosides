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

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.schemas import OrderForm, KnowledgeBase

# Import Skeleton models from schemas.py (canonical source)
from app.models.schemas import Skeleton, SkeletonSlide


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
6. Mark "needs_image: true" for content slides that explain concepts, show examples, or compare things
7. Every slide should have ONE clear purpose

IMAGE GUIDELINES:
- Most content slides SHOULD have needs_image: true
- Exceptions: title slide, overview/agenda, pure equation slides, conclusions
- Images help audience engagement - use liberally

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


def create_outliner_agent(llm=None, tools: Optional[List[BaseTool]] = None, max_iter: int = 5) -> Agent:
    """
    Create the Outliner Agent (The Architect).
    
    This agent:
    - Reads source documents using native Gemini multimodal
    - Builds the structural skeleton for the presentation
    - Marks placeholders for diagrams, equations, citations
    - Enforces density limits (max 5 bullets)
    
    Args:
        llm: The LLM instance (should be Gemini Flash with MEDIUM thinking)
             Defaults to OUTLINER_LLM if not provided
        tools: Optional list of tools (e.g., ListSectionsTool, ReadSectionTool)
        max_iter: Maximum internal iterations to prevent infinite loops (default=5)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        from app.clients.gemini.llm import OUTLINER_LLM
        llm = OUTLINER_LLM()
    
    agent_kwargs = {
        "role": "Presentation Structure Architect",
        "goal": """Read source documents and create a logical slide skeleton.
        Structure the content with clear narrative flow (intro → body → conclusion).
        Mark where diagrams, equations, and citations are needed.
        NEVER exceed 5 bullet points per slide.""",
        "backstory": """You are a PhD-level researcher and presentation expert.
        You've synthesized thousands of academic papers into clear, compelling
        presentations. You understand narrative structure, visual learning,
        and information density. You're ruthless about cutting excess content
        and know exactly when a diagram would explain things better than words.
        You never create slides that look like walls of text.""",
        "llm": llm,
        "verbose": True,
        "allow_delegation": False,
        "memory": True,
        "max_iter": max_iter,  # Limit internal iterations to prevent infinite loops
    }
    
    if tools:
        agent_kwargs["tools"] = tools
    
    return Agent(**agent_kwargs)


def create_outliner_task(
    agent: Agent,
    order_form: "OrderForm",
    knowledge_base: Optional["KnowledgeBase"] = None,
    university_context: Optional["UniversityContext"] = None,
) -> Task:
    """
    Create a task for the Outliner to build a presentation skeleton.
    
    The Outliner will:
    1. Read the KnowledgeBase sections (if provided) to understand actual content
    2. Map sections to logical slides based on user's focus_areas
    3. Identify which slides need diagrams, equations, citations, images
    4. Create a narrative arc with proper flow
    5. Limit to max 5 bullet points per slide
    
    Args:
        agent: The Outliner agent
        order_form: User preferences from Clarifier (title, audience, focus_areas, etc.)
        knowledge_base: Optional extracted content from user documents
        university_context: Optional university context for formatting rules
        
    Returns:
        CrewAI Task configured for skeleton generation
    """
    from app.models.schemas import Skeleton
    
    # Build document context if KnowledgeBase is provided
    document_context = ""
    if knowledge_base and knowledge_base.sections:
        sections_summary = []
        for section in knowledge_base.sections:
            # Include title, content preview, and what visuals exist
            visuals_note = f" (Contains visuals: {', '.join(section.visuals[:3])})" if section.visuals else ""
            page_note = f" [Pages {section.page_range}]" if section.page_range else ""
            
            # Check for equations (LaTeX patterns)
            has_equations = any(marker in section.content for marker in ['$', '\\frac', '\\int', '\\sum', '\\alpha', '\\beta'])
            equation_note = " [CONTAINS EQUATIONS]" if has_equations else ""
            
            # Create a preview (first 300 chars)
            content_preview = section.content[:300].replace('\n', ' ').strip()
            if len(section.content) > 300:
                content_preview += "..."
            
            sections_summary.append(
                f"### {section.title}{page_note}{equation_note}{visuals_note}\n"
                f"{content_preview}"
            )
        
        document_context = f"""
## DOCUMENT CONTENT (Use this to inform your outline)

The user has uploaded documents. Here are the key sections:

{chr(10).join(sections_summary)}

**Your job is to analyze this content and decide:**
- Which sections should become slides
- Which slides need diagrams (complex processes, relationships)
- Which slides need equations (mathematical content marked above)
- Which slides need citations (claims, statistics, research findings)
- How to best organize the narrative flow
"""
    else:
        document_context = """
## NO DOCUMENT PROVIDED

The user has not uploaded any documents. Create a logical outline based on:
- The key_topics they specified
- Their focus_areas
- Standard presentation structure for the topic

Mark slides that would typically need diagrams, equations, or citations.
"""
    
    # Build focus areas guidance
    focus_guidance = ""
    if order_form.focus_areas:
        focus_list = ", ".join(order_form.focus_areas)
        focus_guidance = f"""
## FOCUS AREAS (Give these topics MORE attention)

The user wants to emphasize: **{focus_list}**

For these topics:
- Allocate more slides
- Mark as needing diagrams where helpful
- Add more detailed bullet points
"""
    
    # Build emphasis style guidance
    emphasis_guidance = {
        "detailed": "Use 4-5 bullet points per slide with substantive explanations.",
        "concise": "Use 2-3 tight bullet points per slide. Be brief.",
        "visual-heavy": "Use 1-2 bullets per slide. Prioritize diagrams and images over text.",
    }.get(order_form.emphasis_style, "")
    
    # University context injection
    university_injection = ""
    if university_context:
        university_injection = f"""
## UNIVERSITY CONTEXT

Institution: {university_context.university.name}
Citation style: {university_context.university.default_citation_style}
Apply academic formatting standards appropriate for this institution.
"""

    task_description = f"""Create a structured presentation outline (Skeleton) for this presentation.

## USER REQUIREMENTS

- **Title**: {order_form.presentation_title}
- **Audience**: {order_form.target_audience}
- **Target Slides**: {order_form.target_slides}
- **Key Topics**: {', '.join(order_form.key_topics) if order_form.key_topics else 'Based on document content'}
- **Tone**: {order_form.tone}
- **Emphasis Style**: {order_form.emphasis_style} ({emphasis_guidance})
{focus_guidance}
{document_context}
{university_injection}

## YOUR TASK

1. **Analyze the content** to understand the logical structure
2. **Create {order_form.target_slides} slides** with clear purpose each
3. **Structure as**: Title → Overview (optional) → Body slides → Conclusion
4. **Mark asset needs**:
   - `needs_diagram: true` for processes, architectures, relationships
   - `needs_equation: true` for mathematical content (look for [CONTAINS EQUATIONS] markers)
   - `needs_citation: true` for claims, statistics, research findings
   - `needs_image: true` for concepts that benefit from visual examples
5. **Write a narrative_arc** describing the flow of the presentation
6. **Max 5 bullet points per slide** - split complex topics across slides

## OUTPUT FORMAT

Return a valid Skeleton JSON matching this structure:
```json
{{
  "presentation_title": "...",
  "target_audience": "...",
  "narrative_arc": "Brief description of the story flow",
  "slides": [
    {{
      "order": 1,
      "title": "...",
      "content_type": "title|overview|content|diagram|equation|conclusion",
      "description": "One-sentence purpose of this slide",
      "bullet_points": ["point 1", "point 2"],
      "needs_diagram": false,
      "diagram_description": null,
      "needs_equation": false,
      "equation_description": null,
      "needs_citation": false,
      "citation_topic": null,
      "needs_image": true,
      "image_description": "[Describe what image would enhance this slide]"
    }}
  ]
}}
```
"""

    return Task(
        description=task_description,
        expected_output="""A complete Skeleton JSON with:
- presentation_title, target_audience, narrative_arc
- slides array with all required fields filled
- Appropriate needs_diagram, needs_equation, needs_citation, needs_image flags
- Max 5 bullet points per slide""",
        agent=agent,
        output_pydantic=Skeleton,
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
