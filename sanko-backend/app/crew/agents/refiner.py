"""
Refiner Agent

Purpose: Verify content alignment and render all assets (equations, diagrams, citations).
Model: Gemini PRO (high thinking for quality verification)

This agent is the "Quality Controller":
- Takes PlannedContent from Planner
- Verifies alignment with user's OrderForm preferences
- Calls RenderService to convert LaTeX → SVG, Mermaid → SVG
- Searches for and validates citations
- Fixes broken citations or content issues
- Outputs RefinedContent ready for Generator
"""

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List

from app.models.schemas import (
    OrderForm,
    Skeleton,
    PlannedContent,
    RefinedContent,
    RefinedSlide,
    CitationMetadata,
)
from app.clients.gemini.llm import REFINER_LLM


REFINER_SYSTEM_PROMPT = """You are an expert academic editor and quality assurance specialist.

YOUR MISSION:
Take the Planner's draft content and REFINE it:
1. Verify it matches the user's preferences (OrderForm)
2. Render all assets (LaTeX equations, Mermaid diagrams)
3. Search for and validate all citations
4. Fix any content issues
5. Output publication-ready RefinedContent

## VERIFICATION CHECKLIST

### 1. Alignment with User Preferences
Check against OrderForm:
- Does the tone match what the user requested?
- Are focus_areas given more emphasis than other topics?
- Does emphasis_style match (detailed/concise/visual-heavy)?
- Are references placed correctly (distributed/last_slide)?

If misaligned, FIX IT. Don't just note it.

### 2. Citation Processing
For each slide with citation_queries:
1. Use the AcademicSearchTool to find real papers
2. Verify DOIs are valid
3. Format using the user's citation_style (APA/IEEE/Harvard/Chicago)
4. Call RenderService to get formatted citation strings
5. Store raw CitationMetadata for each citation

If a citation is broken:
- Try re-searching with different keywords
- If still broken, note it in removed_claims

### 3. Equation Rendering
For each slide with equation_placeholder:
1. Convert the description to valid LaTeX
2. Call RenderService render_latex endpoint
3. Store both equation_latex (source) and equation_svg (rendered)

### 4. Diagram Rendering
For each slide with diagram_placeholder:
1. Convert the description to valid Mermaid syntax
2. Call RenderService render_mermaid endpoint
3. Store both diagram_mermaid (source) and diagram_svg (rendered)

### 5. Image Verification
For each slide with image_query:
1. Search for appropriate images
2. Use VisionTool to verify the image matches the description
3. Store verified image_url and image_alt

### 6. Content Polish
- Fix any grammatical errors
- Ensure logical flow between slides
- Verify all bullet points are substantive
- Mark all_claims_verified when appropriate

## TOOLS YOU SHOULD USE

1. **RenderServiceTool**: 
   - render_latex(latex_code) → SVG
   - render_mermaid(mermaid_code) → SVG
   - format_citations(citations, style) → formatted strings

2. **AcademicSearchTool**: Search for papers by topic

3. **VisionTool**: Verify images match descriptions

## OUTPUT FORMAT

Return a RefinedContent object with:
- presentation_title, target_audience, theme_id, citation_style
- slides: List of RefinedSlide, each with:
  - order, title, content_type, bullet_points
  - equation_svg, equation_latex (if applicable)
  - diagram_svg, diagram_mermaid (if applicable)
  - citations: List[CitationMetadata]
  - formatted_citations: List[str]
  - image_url, image_alt, image_caption
  - template_type
  - speaker_notes
  - all_claims_verified
  - removed_claims (if any claims couldn't be verified)

- Quality metrics at the end:
  - total_citations
  - verified_images
  - equations_rendered
  - diagrams_rendered
"""


def create_refiner_agent(llm=None, tools: Optional[List[BaseTool]] = None) -> Agent:
    """
    Create the Refiner Agent (The Quality Controller).
    
    This agent uses Gemini PRO with HIGH thinking for quality verification.
    
    Args:
        llm: The LLM instance (defaults to REFINER_LLM/PRO if not provided)
        tools: Required tools (RenderServiceTool, AcademicSearchTool, VisionTool)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = REFINER_LLM()
    
    agent_kwargs = {
        "role": "Academic Editor & Quality Controller",
        "goal": """Verify and refine the Planner's content.
        Ensure it matches user preferences (focus_areas, emphasis_style, tone).
        Render all equations to SVG using RenderService.
        Render all diagrams to SVG using RenderService.
        Search for and validate all citations.
        Fix any content issues or misalignments.
        Output publication-ready RefinedContent.""",
        "backstory": """You are a meticulous academic editor with 20+ years of experience
        in scholarly publishing. You've edited papers for Nature, Science, and IEEE.
        You have an eagle eye for detail and never let errors slip through.
        You understand citation formats deeply and can spot a broken DOI instantly.
        You're also a skilled technical writer who can polish any content to perfection.
        You take pride in ensuring every presentation you touch is of the highest quality.""",
        "llm": llm,
        "verbose": True,
        "allow_delegation": False,
        "memory": True,
    }
    
    if tools:
        agent_kwargs["tools"] = tools
    
    return Agent(**agent_kwargs)


def create_refining_task(
    agent: Agent,
    planned_content: PlannedContent,
    order_form: OrderForm,
    skeleton: Skeleton,
) -> Task:
    """
    Create a task for the Refiner to verify and render assets.
    
    Args:
        agent: The Refiner agent
        planned_content: Content from Planner
        order_form: User preferences
        skeleton: Original structure (for context)
        
    Returns:
        CrewAI Task for content refinement
    """
    # Build slides context
    slides_summary = "\n".join([
        f"Slide {s.order}: {s.title}"
        f"\n  - Has equation placeholder: {bool(s.equation_placeholder)}"
        f"\n  - Has diagram placeholder: {bool(s.diagram_placeholder)}"
        f"\n  - Citation queries: {len(s.citation_queries)}"
        f"\n  - Has image query: {bool(s.image_query)}"
        for s in planned_content.slides
    ])
    
    return Task(
        description=f"""Refine and render all assets for this presentation.

## PLANNED CONTENT SUMMARY
Title: {planned_content.presentation_title}
Slides: {len(planned_content.slides)}

### Slides requiring asset rendering:
{slides_summary}

## USER PREFERENCES TO VERIFY AGAINST
- **Tone**: {order_form.tone}
- **Emphasis Style**: {order_form.emphasis_style}
- **Focus Areas**: {', '.join(order_form.focus_areas) if order_form.focus_areas else 'None'}
- **Citation Style**: {order_form.citation_style}
- **References Placement**: {order_form.references_placement}

## YOUR TASKS

1. **Verify Alignment**: Check that content matches preferences
2. **Render Equations**: For each equation_placeholder:
   - Write valid LaTeX
   - Call RenderService to get SVG
3. **Render Diagrams**: For each diagram_placeholder:
   - Write valid Mermaid syntax
   - Call RenderService to get SVG
4. **Process Citations**: For each citation query:
   - Search using AcademicSearchTool
   - Validate DOIs
   - Format using {order_form.citation_style}
5. **Verify Images**: For each image_query:
   - Search for images
   - Verify with VisionTool
6. **Polish Content**: Fix any issues

Return a complete RefinedContent object.""",
        expected_output="""A RefinedContent JSON with:
- All slides with rendered SVGs for equations/diagrams
- Validated and formatted citations
- Verified image URLs
- Quality metrics (total_citations, verified_images, etc.)""",
        agent=agent,
        output_pydantic=RefinedContent,
    )


# Agent configuration as YAML-compatible dict
REFINER_CONFIG = {
    "role": "Academic Editor & Quality Controller",
    "goal": "Verify content alignment and render all assets to publication quality.",
    "backstory": "Meticulous editor with 20+ years in scholarly publishing.",
    "llm": "gemini/gemini-3-pro-preview",
    "thinking_level": "high",
    "memory": True,
    "verbose": True,
    "tools": ["RenderServiceTool", "AcademicSearchTool", "VisionTool"],
}
