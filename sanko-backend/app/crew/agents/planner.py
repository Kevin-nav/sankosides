"""
Planner Agent

Purpose: Create full slide content with placeholders for assets.
Model: Gemini PRO (high thinking for deep content planning)

This agent is the "Content Architect":
- Takes the approved skeleton and user preferences (OrderForm)
- Generates FULL content for each slide (not just outlines)
- Creates placeholders for equations, diagrams, citations, images
- Respects focus_areas and emphasis_style from OrderForm
- Outputs PlannedContent ready for the Refiner
"""

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List

from app.models.schemas import (
    OrderForm,
    Skeleton,
    PlannedContent,
    PlannedSlide,
    SlideContentType,
)
from app.clients.gemini.llm import PLANNER_LLM


PLANNER_SYSTEM_PROMPT = """You are an expert academic content writer and presentation architect.

YOUR MISSION:
Transform a presentation skeleton into COMPLETE slide content, respecting the user's preferences.

## INPUTS YOU WILL RECEIVE
1. **Skeleton**: Slide structure with titles and flags for what's needed
2. **OrderForm**: User preferences including:
   - focus_areas: Topics to emphasize
   - emphasis_style: "detailed", "concise", or "visual-heavy"
   - tone: academic, casual, technical, or persuasive
   - citation_style: For formatting references
   - references_placement: Where citations go
   - special_requests: Custom requirements

## YOUR RESPONSIBILITIES

### 1. Content Generation (CRITICAL)
For EACH slide, write COMPLETE content:
- Full bullet points with substantive information (not placeholders!)
- Apply the correct emphasis_style:
  - "detailed": 4-5 substantial bullet points with explanations
  - "concise": 2-3 tight bullet points
  - "visual-heavy": 1-2 bullets, prioritize diagram/image needs
- Apply the correct tone throughout

### 2. Academic Elements
When a slide needs citations:
- Add `citation_queries`: Search terms for finding relevant papers
- Example: ["machine learning climate prediction", "neural networks weather forecasting"]

When a slide needs equations:
- Add `equation_placeholder`: Description of what equation is needed
- Example: "Linear regression formula: y = mx + b with explanation"

When a slide needs diagrams:
- Add `diagram_placeholder`: Description of what diagram is needed
- Example: "Flowchart showing data preprocessing pipeline"

When a slide needs images:
- Add `image_query`: Search term for finding relevant images
- Example: "satellite imagery climate change visualization"

### 3. Focus Areas
If focus_areas says ["machine learning", "sustainability"]:
- These topics should be MORE detailed
- Other topics can be briefer
- Explicitly emphasize these in speaker notes

### 4. Template Selection
Based on content, suggest the best template_type:
- "title": Opening slide
- "content": Standard bullet points
- "diagram": Diagram-focused layout
- "equation": Math-focused layout
- "image": Image-focused layout
- "two_column": Split layout
- "quote": Quote slide
- "conclusion": Closing slide

### 5. Speaker Notes
If include_speaker_notes is true:
- Add substantial speaker notes for each slide
- Include talking points not on the slide
- Add timing suggestions if relevant

## OUTPUT FORMAT

Return a PlannedContent object with:
- presentation_title
- target_audience
- theme_id
- citation_style
- slides: List of PlannedSlide, each with:
  - order, title, content_type
  - bullet_points (FULL content!)
  - equation_placeholder (if needed)
  - diagram_placeholder (if needed)
  - citation_queries (if needed)
  - image_query (if needed)
  - template_type
  - speaker_notes (if requested)

## QUALITY STANDARDS

1. NEVER leave bullet points empty or vague
2. Each slide should have a clear, focused purpose
3. Content should flow logically from slide to slide
4. Focus areas should be noticeably more detailed
5. Respect the target slide count from the skeleton
"""


def create_planner_agent(llm=None, tools: Optional[List[BaseTool]] = None) -> Agent:
    """
    Create the Planner Agent (The Content Architect).
    
    This agent uses Gemini PRO with HIGH thinking for deep content generation.
    
    Args:
        llm: The LLM instance (defaults to PLANNER_LLM/PRO if not provided)
        tools: Optional list of tools (e.g., AcademicSearchTool)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = PLANNER_LLM()
    
    agent_kwargs = {
        "role": "Content Architect & Academic Writer",
        "goal": """Transform the presentation skeleton into COMPLETE slide content.
        Write full, substantive bullet points - never placeholders or outlines.
        Respect the user's focus_areas (emphasize these topics more).
        Apply the correct emphasis_style (detailed/concise/visual-heavy).
        Identify where citations, equations, diagrams, and images are needed.
        Output a complete PlannedContent ready for refinement.""",
        "backstory": """You are a PhD-level researcher and professional presentation writer
        with expertise across multiple academic disciplines. You've written thousands of 
        presentations for conferences, lectures, and business meetings. You understand 
        how to transform complex topics into clear, engaging slides. You excel at 
        adapting content for different audiences - from students to executives to 
        expert panels. You know exactly when a diagram would explain better than words,
        and you understand academic citation requirements deeply.""",
        "llm": llm,
        "verbose": True,
        "allow_delegation": False,
        "memory": True,
    }
    
    if tools:
        agent_kwargs["tools"] = tools
    
    return Agent(**agent_kwargs)


def create_planning_task(
    agent: Agent,
    skeleton: Skeleton,
    order_form: OrderForm,
) -> Task:
    """
    Create a task for the Planner to generate content.
    
    Args:
        agent: The Planner agent
        skeleton: Approved presentation structure
        order_form: User preferences from Clarifier
        
    Returns:
        CrewAI Task for content planning
    """
    # Build context from skeleton
    slides_context = "\n".join([
        f"Slide {s.order}: {s.title} ({s.content_type.value})"
        f"\n  - {s.description}"
        f"\n  - Needs diagram: {s.needs_diagram}" + (f" - {s.diagram_description}" if s.diagram_description else "")
        + f"\n  - Needs equation: {s.needs_equation}" + (f" - {s.equation_description}" if s.equation_description else "")
        + f"\n  - Needs citation: {s.needs_citation}" + (f" - {s.citation_topic}" if s.citation_topic else "")
        + f"\n  - Needs image: {s.needs_image}" + (f" - {s.image_description}" if s.image_description else "")
        for s in skeleton.slides
    ])
    
    return Task(
        description=f"""Create COMPLETE slide content for this presentation.

## PRESENTATION SKELETON
Title: {skeleton.presentation_title}
Target Audience: {skeleton.target_audience}
Narrative: {skeleton.narrative_arc}

### Slides to Write:
{slides_context}

## USER PREFERENCES (OrderForm)
- **Tone**: {order_form.tone}
- **Emphasis Style**: {order_form.emphasis_style}
- **Focus Areas**: {', '.join(order_form.focus_areas) if order_form.focus_areas else 'None specified'}
- **Citation Style**: {order_form.citation_style}
- **References Placement**: {order_form.references_placement}
- **Include Speaker Notes**: {order_form.include_speaker_notes}
- **Special Requests**: {order_form.special_requests or 'None'}

## YOUR TASK
1. Write FULL content for EVERY slide (not just outlines!)
2. Apply emphasis_style: {order_form.emphasis_style}
3. Emphasize focus_areas more heavily: {order_form.focus_areas}
4. Add placeholders for assets that the Refiner will fill
5. Suggest template_type for each slide
6. Add speaker_notes if requested

Return a complete PlannedContent object.""",
        expected_output="""A PlannedContent JSON with:
- presentation_title
- target_audience  
- theme_id
- citation_style
- slides: Array of PlannedSlide objects with full content""",
        agent=agent,
        output_pydantic=PlannedContent,
    )


# Agent configuration as YAML-compatible dict
PLANNER_CONFIG = {
    "role": "Content Architect & Academic Writer",
    "goal": "Transform skeleton into complete slide content with asset placeholders.",
    "backstory": "PhD-level researcher with expertise in creating academic presentations.",
    "llm": "gemini/gemini-3-pro-preview",
    "thinking_level": "high",
    "memory": True,
    "verbose": True,
}
