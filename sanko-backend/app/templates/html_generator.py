"""
HTML Generator Utilities

Generates HTML slides using the template system.
Wraps template output in complete HTML documents with theme CSS.
Supports university branding (badges, names) and slide numbering.
"""

from typing import TYPE_CHECKING, Union, Optional

from app.core.config import SLIDE_WIDTH, SLIDE_HEIGHT

if TYPE_CHECKING:
    from app.agents.planner import EnrichedSlide as LegacyEnrichedSlide
    from app.routers.generation.models import EnrichedSlide
    from app.themes import SlideTheme, ColorPalette, UniversityBranding


def generate_slide_html_with_branding(
    slide: Union["EnrichedSlide", "LegacyEnrichedSlide"],
    theme: "SlideTheme",
    colors: Optional["ColorPalette"] = None,
    branding: Optional["UniversityBranding"] = None,
    slide_number: int = 1,
    total_slides: int = 1,
) -> str:
    """
    Generate HTML for a slide with university branding and numbering.
    
    Args:
        slide: Enriched slide data
        theme: Theme configuration
        colors: Optional color palette override
        branding: Optional university branding (badge, name)
        slide_number: Current slide number (1-indexed)
        total_slides: Total number of slides
        
    Returns:
        Complete HTML document with branding
    """
    from app.templates import select_template_for_slide
    from app.routers.generation.models import EnrichedSlide as NewEnrichedSlide
    from app.themes import UniversityBranding as UB
    
    # Use default branding if not provided
    if branding is None:
        branding = UB()
    
    # Use theme colors if not overridden
    if colors is None:
        colors = theme.colors
    
    # Convert legacy slide if needed
    if not isinstance(slide, NewEnrichedSlide):
        slide = NewEnrichedSlide(
            order=slide.order,
            title=slide.title,
            bullet_points=slide.bullet_points,
            content_type=slide.content_type,
            citations=list(slide.citations) if hasattr(slide, 'citations') else [],
            image_url=getattr(slide, 'image_url', None),
            image_alt=getattr(slide, 'image_alt', None),
            equation_latex=getattr(slide, 'equation_latex', None),
            diagram_mermaid=getattr(slide, 'diagram_mermaid', None),
            speaker_notes=getattr(slide, 'speaker_notes', None),
            formatted_citations=getattr(slide, 'formatted_citations', []),
        )
    
    # Determine if this is a title slide
    is_title_slide = slide.content_type == "title" or slide.order == 1
    
    # Select and render template
    template = select_template_for_slide(slide)
    slide_content = template.render(slide, theme, colors)
    css_vars = template.get_css(theme, colors)
    
    # Generate branding header HTML
    header_html = _generate_branding_header(
        branding, 
        is_title_slide, 
        slide_number, 
        total_slides
    )
    
    # Generate branding footer HTML (for title slide)
    footer_html = _generate_branding_footer(branding, is_title_slide)
    
    # Combine with branding CSS
    branding_css = _get_branding_css(branding)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
{css_vars}

{theme.css_overrides}

{branding_css}

/* Base slide styles */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

.slide-wrapper {{
    position: relative;
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
}}

.slide {{
    width: 100%;
    height: 100%;
    padding: var(--spacing-lg);
    padding-top: 60px; /* Space for header */
    background: var(--color-background);
    color: var(--color-text-primary);
    font-family: var(--font-body);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}

/* Branding header */
.slide-branding-header {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 48px;
    padding: 8px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
}}

.university-badge {{
    height: 32px;
    width: auto;
    object-fit: contain;
}}

.slide-number {{
    font-family: var(--font-body);
    font-size: 14px;
    color: var(--color-text-secondary);
}}

/* Branding footer (title slide only) */
.slide-branding-footer {{
    position: absolute;
    bottom: 16px;
    left: 24px;
    right: 24px;
    text-align: center;
    font-family: var(--font-body);
    font-size: 16px;
    color: var(--color-text-secondary);
}}

{_get_base_slide_css()}
    </style>
</head>
<body>
    <div class="slide-wrapper">
        {header_html}
        {slide_content}
        {footer_html}
    </div>
</body>
</html>'''
    
    return html


async def generate_slide_html_with_db_template(
    slide: Union["EnrichedSlide", "LegacyEnrichedSlide"],
    theme: "SlideTheme",
    session,  # AsyncSession
    colors: Optional["ColorPalette"] = None,
    branding: Optional["UniversityBranding"] = None,
    slide_number: int = 1,
    total_slides: int = 1,
    layout_style: str = "default",
) -> str:
    """
    Generate HTML for a slide using DATABASE templates with fallback to hardcoded.
    
    This is the preferred function for production slide generation.
    It first tries to fetch the template from the database, and falls back
    to the hardcoded Python templates if not found.
    
    Args:
        slide: Enriched slide data
        theme: Theme configuration  
        session: AsyncSession for database access
        colors: Optional color palette override
        branding: Optional university branding (badge, name)
        slide_number: Current slide number (1-indexed)
        total_slides: Total number of slides
        layout_style: Theme layout style (default, modern, split, etc.)
        
    Returns:
        Complete HTML document with branding
    """
    from app.templates import (
        select_template_for_slide, 
        get_db_template_async,
        render_db_template,
    )
    from app.routers.generation.models import EnrichedSlide as NewEnrichedSlide
    from app.themes import UniversityBranding as UB
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    # Use default branding if not provided
    if branding is None:
        branding = UB()
    
    # Use theme colors if not overridden
    if colors is None:
        colors = theme.colors
    
    # Convert legacy slide if needed
    if not isinstance(slide, NewEnrichedSlide):
        slide = NewEnrichedSlide(
            order=slide.order,
            title=slide.title,
            bullet_points=slide.bullet_points,
            content_type=slide.content_type,
            citations=list(slide.citations) if hasattr(slide, 'citations') else [],
            image_url=getattr(slide, 'image_url', None),
            image_alt=getattr(slide, 'image_alt', None),
            equation_latex=getattr(slide, 'equation_latex', None),
            diagram_mermaid=getattr(slide, 'diagram_mermaid', None),
            speaker_notes=getattr(slide, 'speaker_notes', None),
            formatted_citations=getattr(slide, 'formatted_citations', []),
        )
    
    # Determine template type based on slide content
    template_type = _determine_template_type(slide)
    
    # Try to get database template
    db_template = await get_db_template_async(session, template_type, layout_style)
    
    if db_template:
        # Use database template (Jinja2)
        logger.debug(f"Using DB template: {db_template['template_id']}")
        slide_content = render_db_template(db_template, slide, theme, colors)
        css_styles = db_template.get("css_styles", "")
    else:
        # Fall back to hardcoded Python template
        logger.debug(f"Falling back to hardcoded template for {template_type}")
        template = select_template_for_slide(slide)
        slide_content = template.render(slide, theme, colors)
        css_styles = ""
    
    # Generate CSS variables from theme (consistent with both template types)
    css_vars = _generate_theme_css_vars(theme, colors)
    
    # Generate layout-specific CSS from slide fields
    layout_css = _generate_layout_css(slide)
    css_styles = css_styles + "\n" + layout_css if css_styles else layout_css
    
    # Determine if this is a title slide
    is_title_slide = slide.content_type == "title" or slide.order == 1
    
    # Generate branding header HTML
    header_html = _generate_branding_header(
        branding, 
        is_title_slide, 
        slide_number, 
        total_slides
    )
    
    # Generate branding footer HTML (for title slide)
    footer_html = _generate_branding_footer(branding, is_title_slide)
    
    # Combine with branding CSS
    branding_css = _get_branding_css(branding)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
{css_vars}

{theme.css_overrides}

{css_styles}

{branding_css}

/* Base slide styles */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

.slide-wrapper {{
    position: relative;
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
}}

.slide {{
    width: 100%;
    height: 100%;
    padding: var(--spacing-lg);
    padding-top: 60px; /* Space for header */
    background: var(--color-background);
    color: var(--color-text-primary);
    font-family: var(--font-body);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}

/* Branding header */
.slide-branding-header {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 48px;
    padding: 8px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
}}

.university-badge {{
    height: 32px;
    width: auto;
    object-fit: contain;
}}

.slide-number {{
    font-family: var(--font-body);
    font-size: 14px;
    color: var(--color-text-secondary);
}}

/* Branding footer (title slide only) */
.slide-branding-footer {{
    position: absolute;
    bottom: 16px;
    left: 24px;
    right: 24px;
    text-align: center;
    font-family: var(--font-body);
    font-size: 16px;
    color: var(--color-text-secondary);
}}

{_get_base_slide_css()}
    </style>
</head>
<body>
    <div class="slide-wrapper">
        {header_html}
        {slide_content}
        {footer_html}
    </div>
</body>
</html>'''
    
    return html


def _determine_template_type(slide: "EnrichedSlide") -> str:
    """Determine the template type based on slide content."""
    # Priority: special content detection > explicit content_type
    if slide.equation_latex or getattr(slide, 'equation_svg', None):
        return "two_col_math"
    
    if slide.image_url:
        return "two_col_image"
    
    if slide.diagram_mermaid or getattr(slide, 'diagram_svg', None):
        return "diagram"
    
    return slide.content_type or "content"


def _generate_theme_css_vars(theme: "SlideTheme", colors: "ColorPalette") -> str:
    """Generate CSS variables from theme configuration."""
    # Extract numeric values from theme properties (they might be strings like "48px")
    def extract_px(val: str) -> str:
        """Extract numeric value from px string or return as-is if already numeric."""
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return val.replace('px', '')
        return str(val)
    
    return f''':root {{
  /* Layout */
  --slide-width: {SLIDE_WIDTH}px;
  --slide-height: {SLIDE_HEIGHT}px;

  /* Typography - using flat theme attributes */
  --font-heading: '{theme.font_heading}', sans-serif;
  --font-body: '{theme.font_body}', sans-serif;
  --font-size-title: {theme.font_size_title};
  --font-size-heading: {theme.font_size_heading};
  --font-size-body: {theme.font_size_body};
  --font-size-caption: {theme.font_size_caption};
  --font-weight-title: {theme.font_weight_title};
  --font-weight-heading: {theme.font_weight_heading};

  /* Spacing */
  --spacing-xs: {theme.spacing_xs};
  --spacing-sm: {theme.spacing_sm};
  --spacing-md: {theme.spacing_md};
  --spacing-lg: {theme.spacing_lg};
  --spacing-xl: {theme.spacing_xl};

  /* Colors */
  --color-primary: {colors.primary};
  --color-secondary: {colors.secondary};
  --color-accent: {colors.accent};
  --color-background: {colors.background};
  --color-surface: {colors.surface};
  --color-text-primary: {colors.text_primary};
  --color-text-secondary: {colors.text_secondary};
  --color-border: {colors.border};

  /* Borders */
  --radius-sm: {theme.border_radius_sm};
  --radius-md: {theme.border_radius_md};
  --radius-lg: {theme.border_radius_lg};
}}'''



def _generate_branding_header(
    branding: "UniversityBranding",
    is_title_slide: bool,
    slide_number: int,
    total_slides: int,
) -> str:
    """Generate the branding header with badge and slide number."""
    # Title slide usually doesn't show numbering
    show_header = (is_title_slide and branding.show_on_title_slide) or \
                  (not is_title_slide and branding.show_on_content_slides)
    
    if not show_header and not branding.has_branding():
        return ""
    
    badge_html = ""
    if branding.university_badge_url:
        badge_html = f'<img class="university-badge" src="{branding.university_badge_url}" alt="{branding.university_name} badge">'
    
    # Show slide number on content slides only
    number_html = ""
    if not is_title_slide and total_slides > 1:
        number_html = f'<span class="slide-number">{slide_number} of {total_slides}</span>'
    
    return f'''<div class="slide-branding-header">
        {badge_html}
        {number_html}
    </div>'''


def _generate_branding_footer(branding: "UniversityBranding", is_title_slide: bool) -> str:
    """Generate the branding footer (university name on title slide)."""
    if not is_title_slide or not branding.show_university_name_footer:
        return ""
    
    if not branding.university_name:
        return ""
    
    return f'''<div class="slide-branding-footer">
        {branding.university_name}
    </div>'''


def _get_branding_css(branding: "UniversityBranding") -> str:
    """Generate CSS for branding positioning."""
    position_css = ""
    if branding.badge_position == "top-left":
        position_css = ".slide-branding-header { flex-direction: row; }"
    elif branding.badge_position == "top-right":
        position_css = ".slide-branding-header { flex-direction: row-reverse; }"
    
    return position_css


def _generate_layout_css(slide) -> str:
    """
    Generate CSS based on slide's layout control fields.
    
    Uses:
    - image_size_hint: small (30%), medium (50%), large (80%), fit (auto)
    - visual_position: left, right, top, bottom, center
    - content_balance: text_heavy (70/30), visual_heavy (30/70), balanced (50/50)
    """
    css_rules = []
    
    # Image size hints
    size_hint = getattr(slide, 'image_size_hint', 'auto')
    if size_hint:
        size_map = {
            'small': '30%',
            'medium': '50%',
            'large': '80%',
            'fit': 'auto',
            'auto': '50%',
        }
        max_width = size_map.get(size_hint, '50%')
        css_rules.append(f"""
/* Image size: {size_hint} */
.slide img, .slide .visual-content {{
    max-width: {max_width};
    max-height: 70%;
}}""")
    
    # Visual position
    visual_pos = getattr(slide, 'visual_position', None)
    if visual_pos:
        if visual_pos == 'left':
            css_rules.append("""
/* Visual position: left */
.columns-container { flex-direction: row-reverse; }""")
        elif visual_pos == 'center':
            css_rules.append("""
/* Visual position: center */
.visual-content, .diagram-container, .equation-wrapper {
    margin: 0 auto;
    text-align: center;
}""")
        elif visual_pos in ('top', 'bottom'):
            direction = 'column' if visual_pos == 'top' else 'column-reverse'
            css_rules.append(f"""
/* Visual position: {visual_pos} */
.columns-container {{ 
    flex-direction: {direction}; 
    gap: var(--spacing-md);
}}
.column {{ flex: none; }}""")
    
    # Content balance
    content_balance = getattr(slide, 'content_balance', None)
    if content_balance:
        if content_balance == 'text_heavy':
            css_rules.append("""
/* Content balance: text heavy (70/30) */
.column:first-child { flex: 7; }
.column:last-child { flex: 3; }""")
        elif content_balance == 'visual_heavy':
            css_rules.append("""
/* Content balance: visual heavy (30/70) */
.column:first-child { flex: 3; }
.column:last-child { flex: 7; }""")
        # 'balanced' uses default 50/50
    
    return "\n".join(css_rules)



def _get_base_slide_css() -> str:
    """Get the base CSS for all slide types."""
    return """
/* Title slide layout */
.slide-title {
    justify-content: center;
    text-align: center;
    padding-top: 80px;
}
.slide-title .title-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: var(--spacing-md);
}
.slide-title .main-title {
    font-family: var(--font-heading);
    font-size: var(--font-size-title);
    font-weight: var(--font-weight-title);
    color: var(--color-primary);
}
.slide-title .subtitle {
    font-size: var(--font-size-heading);
    color: var(--color-text-secondary);
}

/* Content slide layout */
.slide-content .header-region {
    margin-bottom: var(--spacing-lg);
}
.slide-content .slide-title {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    font-weight: var(--font-weight-heading);
    color: var(--color-primary);
    text-align: left;
    justify-content: flex-start;
}
.slide-content .content-region {
    flex: 1;
}
.slide-content ul {
    list-style: none;
    padding-left: 0;
}
.slide-content li {
    font-size: var(--font-size-body);
    line-height: 1.7;
    margin-bottom: var(--spacing-sm);
    padding-left: var(--spacing-md);
    position: relative;
}
.slide-content li::before {
    content: '•';
    color: var(--color-primary);
    font-weight: bold;
    position: absolute;
    left: 0;
}

/* Diagram styles - PROJECTOR FRIENDLY (use 60-80% of area) */
.slide-diagram .diagram-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: var(--spacing-md);
}
.diagram-svg, .mermaid, .mermaid-svg {
    min-width: 60%;
    max-width: 90%;
    min-height: 300px;
    max-height: 500px;
}

/* Math/equation styles - LARGER for visibility */
.equation-wrapper, .math-column {
    display: flex;
    justify-content: center;
    align-items: center;
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: var(--spacing-lg);
    min-height: 80px;
}
.equation-wrapper img, .equation-wrapper svg {
    min-height: 50px;
    max-width: 85%;
}

/* Chart/graph styles */
.chart-container {
    display: flex;
    justify-content: center;
    align-items: center;
    flex: 1;
}
.chart-container img, .chart-container svg {
    min-width: 50%;
    max-width: 90%;
    min-height: 250px;
}

/* Caption styling */
.image-caption, .diagram-caption, .chart-caption {
    font-size: var(--font-size-caption);
    color: var(--color-text-secondary);
    text-align: center;
    margin-top: var(--spacing-sm);
    max-width: 80%;
}

/* Thank You slide - centered, prominent */
.slide-thank-you {
    display: flex !important;
    justify-content: center;
    align-items: center;
    text-align: center;
}
.slide-thank-you .thank-you-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-lg);
}
.slide-thank-you .thank-you-message {
    font-family: var(--font-heading);
    font-size: 72px;
    font-weight: var(--font-weight-title);
    color: var(--color-primary);
    margin-bottom: var(--spacing-md);
}
.slide-thank-you .author-info {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
}
.slide-thank-you .presenter-name {
    font-weight: 600;
    font-size: 28px;
    color: var(--color-text-primary);
}
.slide-thank-you .presenter-email {
    font-size: 20px;
    color: var(--color-primary);
}
.slide-thank-you .questions-prompt {
    font-size: 32px;
    color: var(--color-text-secondary);
    font-style: italic;
    margin-top: var(--spacing-lg);
}
.slide-thank-you .thank-you-logo {
    max-height: 80px;
    margin-bottom: var(--spacing-md);
}

/* References slide - two-column, smaller font */
.slide-references {
    padding-top: 60px;
}
.slide-references .references-title {
    font-size: var(--font-size-heading);
    color: var(--color-primary);
    margin-bottom: var(--spacing-md);
}
.slide-references .references-list {
    column-count: 2;
    column-gap: 32px;
    font-size: 14px;
    line-height: 1.6;
}
.slide-references .reference-entry {
    break-inside: avoid;
    margin-bottom: 10px;
    text-indent: -20px;
    padding-left: 20px;
}
.slide-references .reference-title {
    font-style: italic;
}
.slide-references .figure-sources {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-sm);
    border-top: 1px solid var(--color-border);
    font-size: 12px;
}

/* Two-column layouts for image/text */
.columns-container {
    display: flex;
    gap: var(--spacing-lg);
    flex: 1;
    align-items: center;
}
.column {
    flex: 1;
}
.column.visual {
    display: flex;
    justify-content: center;
    align-items: center;
}
.column.visual img {
    max-width: 100%;
    max-height: 400px;
    object-fit: contain;
    border-radius: var(--radius-md);
}
"""


def generate_slide_html_sync(
    slide: Union["EnrichedSlide", "LegacyEnrichedSlide"],
    theme: "SlideTheme",
    colors: "ColorPalette",
) -> str:
    """
    Generate HTML for a single slide using the template system.
    
    Selects the appropriate template based on slide content and wraps
    the rendered output in a complete HTML document with theme CSS.
    
    Args:
        slide: Enriched slide data (from either new or legacy model)
        theme: Theme configuration
        colors: Color palette
        
    Returns:
        Complete HTML document for the slide
    """
    # Deferred import to break circular dependency
    from app.templates import select_template_for_slide
    
    # Convert legacy slide to new model if needed
    from app.routers.generation.models import EnrichedSlide as NewEnrichedSlide
    
    if not isinstance(slide, NewEnrichedSlide):
        # Convert from legacy model
        slide = NewEnrichedSlide(
            order=slide.order,
            title=slide.title,
            bullet_points=slide.bullet_points,
            content_type=slide.content_type,
            citations=list(slide.citations) if hasattr(slide, 'citations') else [],
            image_url=getattr(slide, 'image_url', None),
            image_alt=getattr(slide, 'image_alt', None),
            equation_latex=getattr(slide, 'equation_latex', None),
            diagram_mermaid=getattr(slide, 'diagram_mermaid', None),
            speaker_notes=getattr(slide, 'speaker_notes', None),
            formatted_citations=getattr(slide, 'formatted_citations', []),
        )
    
    # Select the appropriate template
    template = select_template_for_slide(slide)
    
    # Render the slide content
    slide_content = template.render(slide, theme, colors)
    
    # Get CSS variables from theme
    css_vars = template.get_css(theme, colors)
    
    # Wrap in complete HTML document
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
{css_vars}

{theme.css_overrides}

/* Base slide styles */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

.slide {{
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
    padding: var(--spacing-lg);
    background: var(--color-background);
    color: var(--color-text-primary);
    font-family: var(--font-body);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}

/* Title slide layout */
.slide-title {{
    justify-content: center;
    text-align: center;
}}
.slide-title .title-content {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: var(--spacing-md);
}}
.slide-title .main-title {{
    font-family: var(--font-heading);
    font-size: var(--font-size-title);
    font-weight: var(--font-weight-title);
    color: var(--color-primary);
}}
.slide-title .subtitle {{
    font-size: var(--font-size-heading);
    color: var(--color-text-secondary);
}}
.slide-title .title-footer {{
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-caption);
    color: var(--color-text-secondary);
}}

/* Content slide layout */
.slide-content .header-region {{
    margin-bottom: var(--spacing-lg);
}}
.slide-content .slide-title {{
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    font-weight: var(--font-weight-heading);
    color: var(--color-primary);
    text-align: left;
    justify-content: flex-start;
}}
.slide-content .content-region {{
    flex: 1;
}}
.slide-content ul {{
    list-style: none;
    padding-left: 0;
}}
.slide-content li {{
    font-size: var(--font-size-body);
    line-height: 1.7;
    margin-bottom: var(--spacing-sm);
    padding-left: var(--spacing-md);
    position: relative;
}}
.slide-content li::before {{
    content: '•';
    color: var(--color-primary);
    font-weight: bold;
    position: absolute;
    left: 0;
}}

/* Two-column layouts */
.slide-two-col .columns-container,
.slide-two-col-math .columns-container,
.slide-two-col-image .columns-container {{
    display: flex;
    gap: var(--spacing-lg);
    flex: 1;
}}
.column {{
    flex: 1;
    display: flex;
    flex-direction: column;
}}

/* Math/equation styles */
.equation-wrapper, .math-column {{
    display: flex;
    justify-content: center;
    align-items: center;
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
}}
.latex-content {{
    font-family: 'Computer Modern', serif;
    font-size: 24px;
}}

/* Diagram styles */
.slide-diagram .diagram-container {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}
.diagram-svg, .mermaid {{
    max-width: 100%;
    max-height: 80%;
}}

/* Image styles */
.slide-image, .slide-full-image {{
    text-align: center;
}}
.slide-image img, .slide-full-image img {{
    max-width: 100%;
    max-height: 400px;
    object-fit: contain;
    border-radius: var(--radius-md);
}}
.image-caption {{
    margin-top: var(--spacing-sm);
    font-size: var(--font-size-caption);
    color: var(--color-text-secondary);
}}

/* Quote styles */
.slide-quote {{
    justify-content: center;
}}
.quote-content blockquote {{
    font-size: var(--font-size-heading);
    font-style: italic;
    color: var(--color-text-primary);
    border-left: 4px solid var(--color-primary);
    padding-left: var(--spacing-md);
    margin-bottom: var(--spacing-md);
}}
.quote-attribution {{
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
    text-align: right;
}}

/* Section divider */
.slide-section {{
    justify-content: center;
    text-align: center;
}}
.slide-section .section-number {{
    font-size: 72px;
    font-weight: bold;
    color: var(--color-primary);
    opacity: 0.3;
}}
.slide-section .section-title {{
    font-size: var(--font-size-title);
    color: var(--color-primary);
}}

/* Conclusion styles */
.slide-conclusion .takeaways {{
    flex: 1;
}}
.cta-region {{
    background: var(--color-primary);
    color: var(--color-background);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    text-align: center;
}}
    </style>
</head>
<body>
    {slide_content}
</body>
</html>'''
    
    return html
