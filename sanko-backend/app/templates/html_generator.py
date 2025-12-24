"""
HTML Generator Utilities

Generates HTML slides using the template system.
Wraps template output in complete HTML documents with theme CSS.
"""

from typing import TYPE_CHECKING, Union

from app.config import SLIDE_WIDTH, SLIDE_HEIGHT

if TYPE_CHECKING:
    from app.agents.planner import EnrichedSlide as LegacyEnrichedSlide
    from app.routers.generation.models import EnrichedSlide
    from app.themes import SlideTheme, ColorPalette


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
