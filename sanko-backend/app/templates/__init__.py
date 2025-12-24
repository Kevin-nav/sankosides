from typing import Dict, Type
from app.templates.base import BaseTemplate
from app.templates.layouts import (
    TitleTemplate,
    ContentTemplate,
    SectionTemplate,
    TwoColumnTemplate,
    ConclusionTemplate,
    TwoColImageTemplate,
    FullImageTemplate,
    TwoColMathTemplate,
    DiagramTemplate,
    QuoteTemplate,
    TimelineTemplate,
    ComparisonTemplate,
    CodeTemplate
)
from app.routers.generation.models import EnrichedSlide

# Registry of all available templates
TEMPLATE_REGISTRY: Dict[str, Type[BaseTemplate]] = {
    "title": TitleTemplate,
    "content": ContentTemplate,
    "section": SectionTemplate,
    "two_column": TwoColumnTemplate,
    "conclusion": ConclusionTemplate,
    "two_col_image": TwoColImageTemplate,
    "full_image": FullImageTemplate,
    "two_col_math": TwoColMathTemplate,
    "diagram": DiagramTemplate,
    "quote": QuoteTemplate,
    "timeline": TimelineTemplate,
    "comparison": ComparisonTemplate,
    "code": CodeTemplate,
}

def get_template_by_id(template_id: str) -> BaseTemplate:
    """Get a template instance by its ID."""
    template_cls = TEMPLATE_REGISTRY.get(template_id)
    if not template_cls:
        # Fallback to content template if not found
        return ContentTemplate()
    return template_cls()

def select_template_for_slide(slide: EnrichedSlide) -> BaseTemplate:
    """
    Select the best template for a slide based on its content type and data.
    
    Priority:
    1. Special content (equations, images, diagrams) - detected by data presence
    2. Explicit content_type if it's a specific type (not generic 'content')
    3. Default to ContentTemplate
    """
    # First, apply heuristics for special content based on data presence
    # This allows slides with content_type='content' but special data to use specialized templates
    if slide.equation_latex or slide.equation_svg:
        return TwoColMathTemplate()
    
    if slide.image_url:
        return TwoColImageTemplate()
    
    if slide.diagram_mermaid or slide.diagram_svg:
        return DiagramTemplate()
    
    # Then check for explicit content type mapping
    if slide.content_type in TEMPLATE_REGISTRY:
        return TEMPLATE_REGISTRY[slide.content_type]()
    
    # Default
    return ContentTemplate()
