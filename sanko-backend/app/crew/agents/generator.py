"""
Generator Agent

Purpose: Convert RefinedContent to HTML slides using templates.
Model: Gemini Flash (medium thinking for template-based generation)

This agent is the "HTML Renderer":
- Takes RefinedContent with all assets rendered
- Selects appropriate template for each slide
- Applies theme and color palette
- Outputs complete HTML slides
"""

from crewai import Agent, Task
from typing import Optional

from app.models.schemas import (
    OrderForm,
    RefinedContent,
    GeneratedPresentation,
    GeneratedSlide,
)
from app.clients.gemini.llm import GENERATOR_LLM


GENERATOR_SYSTEM_PROMPT = """You are an expert HTML/CSS developer specializing in presentation design.

YOUR MISSION:
Convert RefinedContent into beautiful, professional HTML slides.

## INPUTS
1. **RefinedContent**: Slides with full content and rendered assets (SVGs)
2. **Theme**: Color palette and styling preferences
3. **Templates**: Available HTML templates for different slide types

## TEMPLATE TYPES

Use the appropriate template based on slide.template_type:
- **title**: Opening slide with large title, minimal content
- **content**: Standard bullet points layout
- **diagram**: Layout optimized for SVG diagrams
- **equation**: Layout optimized for math equations
- **image**: Image-focused with minimal text
- **two_column**: Split layout for comparisons
- **quote**: Quote with attribution
- **section**: Section divider slide
- **conclusion**: Summary/closing slide

## HTML GENERATION RULES

1. **Use Semantic HTML**: Proper heading hierarchy, lists, etc.
2. **Apply Theme**: Use CSS variables for colors
3. **Embed SVGs Inline**: For equations and diagrams
4. **Responsive Design**: Slides should scale properly
5. **Speaker Notes**: Include in data attributes or hidden section
6. **Accessibility**: Alt text for images, proper ARIA labels

## OUTPUT FORMAT

For each slide, generate:
```html
<div class="slide slide-{order}" data-template="{template_type}">
  <div class="slide-header">
    <h1 class="slide-title">{title}</h1>
  </div>
  <div class="slide-content">
    <!-- Content based on template type -->
  </div>
  <div class="slide-footer">
    <!-- Citations if any -->
  </div>
  <aside class="speaker-notes">{speaker_notes}</aside>
</div>
```

## QUALITY STANDARDS

1. Clean, valid HTML5
2. Consistent spacing and layout
3. Properly sized SVGs (equations, diagrams)
4. Citations formatted according to style
5. No broken layouts (test content fit)
"""


def create_generator_agent(llm=None) -> Agent:
    """
    Create the Generator Agent (The HTML Renderer).
    
    Args:
        llm: The LLM instance (defaults to GENERATOR_LLM/Flash)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = GENERATOR_LLM()
    
    return Agent(
        role="HTML Presentation Developer",
        goal="""Convert RefinedContent into beautiful HTML slides.
        Select the best template for each slide based on its content.
        Apply the theme's color palette consistently.
        Embed all SVGs (equations, diagrams) inline.
        Ensure proper accessibility and semantic HTML.""",
        backstory="""You are a frontend developer with 10+ years of experience
        building beautiful presentations and websites. You've mastered HTML5, CSS3,
        and understand accessibility deeply. You know how to make content shine
        through careful layout and typography. You've built presentation systems
        for Fortune 500 companies and top universities.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_generation_task(
    agent: Agent,
    refined_content: RefinedContent,
    order_form: OrderForm,
) -> Task:
    """
    Create a task for the Generator to produce HTML.
    
    Args:
        agent: The Generator agent
        refined_content: Content with all assets rendered
        order_form: User preferences (for theme)
        
    Returns:
        CrewAI Task for HTML generation
    """
    slides_summary = "\n".join([
        f"Slide {s.order}: {s.title} (template: {s.template_type})"
        f"\n  - Has equation SVG: {bool(s.equation_svg)}"
        f"\n  - Has diagram SVG: {bool(s.diagram_svg)}"
        f"\n  - Citations: {len(s.citations)}"
        f"\n  - Image: {bool(s.image_url)}"
        for s in refined_content.slides
    ])
    
    return Task(
        description=f"""Generate HTML slides for this presentation.

## CONTENT SUMMARY
Title: {refined_content.presentation_title}
Theme: {order_form.theme_id}
Slides: {len(refined_content.slides)}

### Slides:
{slides_summary}

## YOUR TASK
1. Generate complete HTML for each slide
2. Use the appropriate template based on template_type
3. Embed SVGs inline for equations and diagrams
4. Apply theme colors: {order_form.theme_id}
5. Include speaker notes if present
6. Format citations at bottom of slides

Return a GeneratedPresentation with HTML for all slides.""",
        expected_output="""A GeneratedPresentation with:
- title
- theme_id
- slides: Array of GeneratedSlide with rendered_html""",
        agent=agent,
        output_pydantic=GeneratedPresentation,
    )


GENERATOR_CONFIG = {
    "role": "HTML Presentation Developer",
    "goal": "Convert refined content into beautiful HTML slides.",
    "backstory": "Expert frontend developer specializing in presentations.",
    "llm": "gemini/gemini-3-flash-preview",
    "thinking_level": "medium",
    "memory": True,
    "verbose": True,
}
