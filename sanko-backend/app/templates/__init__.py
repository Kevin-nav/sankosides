from typing import Dict, Type, Optional, Any
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
    CodeTemplate,
    ReferencesTemplate,
    ThankYouTemplate,
)
from app.routers.generation.models import EnrichedSlide
from app.core.logging import get_logger

logger = get_logger(__name__)

# Registry of all available HARDCODED templates (fallback)
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
    "references": ReferencesTemplate,
    "thank_you": ThankYouTemplate,
}


def get_template_by_id(template_id: str) -> BaseTemplate:
    """Get a HARDCODED template instance by its ID (legacy/fallback)."""
    template_cls = TEMPLATE_REGISTRY.get(template_id)
    if not template_cls:
        # Fallback to content template if not found
        return ContentTemplate()
    return template_cls()


def select_template_for_slide(slide: EnrichedSlide) -> BaseTemplate:
    """
    Select the best HARDCODED template for a slide based on its content type and data.
    
    NOTE: This is the fallback when database templates are not available.
    For database templates, use get_db_template_html_async() instead.
    
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


# =============================================================================
# DATABASE TEMPLATE FUNCTIONS
# =============================================================================

# =============================================================================
# DATABASE TEMPLATE FUNCTIONS
# =============================================================================

async def get_db_template_async(
    template_type: str,
    layout_style: str = "default",
) -> Optional[Dict[str, Any]]:
    """
    Fetch a template from the database (Convex) with caching.
    
    Priority:
    1. Variant specific: {template_type}_{layout_style}
    2. Standard/Default: {template_type}
    3. Returns None (caller should fall back to hardcoded)
    
    Args:
        template_type: Base template type (title, content, section, etc.)
        layout_style: Theme layout style (default, modern, split, etc.)
        
    Returns:
        Dict with template data or None if not found
    """
    from app.services.unified_cache import template_cache
    from app.core.convex_client import get_convex_client
    
    # Build cache key
    cache_key = f"db:{template_type}:{layout_style}"
    
    # Check cache first
    cached = template_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"DB template cache hit: {cache_key}")
        return cached
    
    client = get_convex_client()
    
    # Build list of template IDs to try
    target_ids = []
    if layout_style and layout_style != "default":
        target_ids.append(f"{template_type}_{layout_style}")
    target_ids.append(template_type)
    
    try:
        # Fetch templates from Convex
        # We fetch explicitly by ID
        found_templates = {}
        for tid in target_ids:
            tmpl = client.query("templates:getTemplateById", {"templateId": tid})
            if tmpl:
                found_templates[tmpl["templateId"]] = tmpl
        
        # Pick the best match
        template = None
        
        # Try specific variant first
        if layout_style and layout_style != "default":
            template = found_templates.get(f"{template_type}_{layout_style}")
        
        # Fall back to base type
        if not template:
            template = found_templates.get(template_type)
        
        if not template:
            logger.debug(f"No DB template found for {template_type}/{layout_style}")
            template_cache.set(cache_key, None)  # Cache the miss
            return None
        
        # Convert to dict for caching and return
        template_dict = {
            "id": template.get("_id"),
            "template_id": template.get("templateId"),
            "name": template.get("name"),
            "html_template": template.get("htmlTemplate"),
            "css_styles": template.get("cssStyles", ""),
            "content_type": template.get("contentType"),
        }
        
        template_cache.set(cache_key, template_dict)
        logger.debug(f"DB template cached: {cache_key}")
        
        return template_dict
        
    except Exception as e:
        logger.error(f"Failed to fetch template from Convex: {e}")
        return None


def render_db_template(
    template_dict: Dict[str, Any],
    slide: EnrichedSlide,
    theme: Any,
    colors: Any,
) -> str:
    """
    Render a database template (Jinja2) with slide data.
    
    Args:
        template_dict: Template data from get_db_template_async()
        slide: EnrichedSlide with content to render
        theme: SlideTheme for styling
        colors: ColorPalette for colors
        
    Returns:
        Rendered HTML content (slide inner content, not full document)
    """
    from jinja2 import Template
    
    # Prepare slide data for template
    slide_data = {
        "order": slide.order,
        "title": slide.title,
        "bullet_points": slide.bullet_points or [],
        "content_type": slide.content_type,
        "image_url": slide.image_url,
        "image_alt": slide.image_alt,
        "image_caption": getattr(slide, 'image_caption', None),
        "equation_latex": slide.equation_latex,
        "equation_svg": slide.equation_svg,
        "diagram_mermaid": slide.diagram_mermaid,
        "diagram_svg": slide.diagram_svg,
        "speaker_notes": slide.speaker_notes,
        "formatted_citations": slide.formatted_citations or [],
        "quote_text": getattr(slide, 'quote_text', None),
        "quote_author": getattr(slide, 'quote_author', None),
    }
    
    # Also provide left/right column data for two_column templates
    if hasattr(slide, 'bullet_points') and slide.bullet_points:
        mid = len(slide.bullet_points) // 2 + len(slide.bullet_points) % 2
        slide_data["left_column"] = {
            "title": "Key Points",
            "content": slide.bullet_points[:mid]
        }
        slide_data["right_column"] = {
            "title": "Details", 
            "content": slide.bullet_points[mid:]
        }
    
    # Render Jinja2 template
    try:
        jinja_template = Template(template_dict["html_template"])
        rendered = jinja_template.render(slide=slide_data)
        return rendered
    except Exception as e:
        logger.error(f"Failed to render DB template: {e}")
        # Return a basic fallback
        return f'<div class="slide slide-{slide.content_type}"><h2>{slide.title}</h2></div>'

