"""
HTML Generator Utilities

Generates HTML slides using the template system.
Wraps template output in complete HTML documents with theme CSS.
Supports university branding (badges, names) and slide numbering.
"""

from html import escape
from typing import TYPE_CHECKING, Union, Optional

from app.core.config import SLIDE_WIDTH, SLIDE_HEIGHT, settings
from app.models.slide_elements import SlideElementTree

if TYPE_CHECKING:
    from app.agents.planner import EnrichedSlide as LegacyEnrichedSlide
    from app.routers.generation.models import EnrichedSlide
from pathlib import Path
from app.themes import SlideTheme, ColorPalette, UniversityBranding

ASSETS_DIR = Path(__file__).parent / "assets"
VIEWS_DIR = Path(__file__).parent / "views"


def should_render_element_tree_html(tree: Optional[SlideElementTree]) -> bool:
    """Feature-gated switch for element-tree HTML rendering."""
    return bool(tree is not None and settings.enable_element_tree_pipeline)


def _render_element_content(element) -> str:
    """Render one slide element's content to static html."""
    content = element.content
    content_type = getattr(content, "type", "")

    if content_type == "text":
        runs = getattr(content, "runs", []) or []
        run_html = []
        for run in runs:
            style_parts = []
            if getattr(run, "size", None):
                style_parts.append(f"font-size:{int(run.size)}px")
            if getattr(run, "color", None):
                style_parts.append(f"color:{escape(str(run.color), quote=True)}")
            if getattr(run, "font", None):
                style_parts.append(f"font-family:{escape(str(run.font), quote=True)}")
            if getattr(run, "bold", False):
                style_parts.append("font-weight:700")
            if getattr(run, "italic", False):
                style_parts.append("font-style:italic")
            styles = f' style="{";".join(style_parts)}"' if style_parts else ""
            run_html.append(f"<span{styles}>{escape(str(getattr(run, 'text', '')))}</span>")
        return f'<div class="el-text">{"".join(run_html)}</div>'

    if content_type == "image":
        url = escape(str(getattr(content, "url", "")), quote=True)
        alt = escape(str(getattr(content, "alt", "") or ""), quote=True)
        caption = getattr(content, "caption", None)
        caption_html = f'<div class="el-caption">{escape(str(caption))}</div>' if caption else ""
        return f'<img class="el-image" src="{url}" alt="{alt}" />{caption_html}'

    if content_type == "equation":
        rendered_svg = getattr(content, "rendered_svg", None)
        latex = getattr(content, "latex", "")
        if rendered_svg:
            return f'<div class="el-equation">{rendered_svg}</div>'
        return f'<div class="el-equation"><code>{escape(str(latex))}</code></div>'

    if content_type == "diagram":
        rendered_svg = getattr(content, "rendered_svg", None)
        mermaid_source = getattr(content, "mermaid_source", "")
        if rendered_svg:
            return f'<div class="el-diagram">{rendered_svg}</div>'
        return f'<pre class="el-diagram-fallback">{escape(str(mermaid_source))}</pre>'

    return "<div></div>"


def element_tree_to_html(tree: SlideElementTree, theme: "SlideTheme") -> str:
    """Convert a SlideElementTree into static absolute-positioned html."""
    colors = theme.colors
    theme_css_vars = _generate_theme_css_vars(theme, colors)

    bg = tree.background
    background_style = "background: var(--color-background);"
    if bg.type == "solid" and bg.color:
        background_style = f"background:{escape(str(bg.color), quote=True)};"
    elif bg.type == "gradient" and bg.gradient:
        background_style = f"background:{escape(str(bg.gradient), quote=True)};"
    elif bg.type == "image" and bg.image_url:
        image_url = escape(str(bg.image_url), quote=True)
        background_style = f"background-image:url('{image_url}');background-size:cover;background-position:center;"

    elements_html = []
    for el in tree.elements:
        elements_html.append(
            (
                f'<div class="tree-element" style="position:absolute;left:{el.x}%;top:{el.y}%;'
                f'width:{el.width}%;height:{el.height}%;z-index:{el.z_index};">'
                f"{_render_element_content(el)}"
                "</div>"
            )
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
{theme_css_vars}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #111; display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
.slide-wrapper {{
  position: relative;
  width: {SLIDE_WIDTH}px;
  height: {SLIDE_HEIGHT}px;
  overflow: hidden;
  color: var(--color-text-primary);
  font-family: var(--font-body);
  {background_style}
}}
.tree-element {{ overflow: hidden; }}
.el-image {{ width: 100%; height: 100%; object-fit: contain; }}
.el-caption {{ font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }}
.el-text {{ width: 100%; height: 100%; white-space: pre-wrap; line-height: 1.3; }}
.el-equation, .el-diagram {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }}
.el-diagram-fallback {{ width: 100%; height: 100%; overflow: auto; }}
  </style>
</head>
<body>
  <div class="slide-wrapper">
    {''.join(elements_html)}
  </div>
</body>
</html>"""

def _load_sdk_asset(filename: str) -> str:
    """Load a static asset from the SDK directory."""
    path = ASSETS_DIR / filename
    if not path.exists():
        return f"/* Asset not found: {filename} */"
    return path.read_text(encoding="utf-8")


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
    colors: Optional["ColorPalette"] = None,
    branding: Optional["UniversityBranding"] = None,
    slide_number: int = 1,
    total_slides: int = 1,
    layout_style: str = "default",
) -> str:
    """
    Generate HTML for a slide using DATABASE templates (or local file fallback).
    
    This uses the new "Slide SDK" architecture:
    1. Loads the base.html Jinja2 template
    2. Injects CSS Grid, Typography, and KaTeX assets
    3. Renders the content template (from DB or file) into the base frame
    """
    from app.templates import get_db_template_async, render_db_template
    from app.routers.generation.models import EnrichedSlide as NewEnrichedSlide
    from app.themes import UniversityBranding as UB
    from app.models.schemas import SlideContentType
    from app.core.logging import get_logger
    from jinja2 import Template
    
    logger = get_logger(__name__)
    
    # Defaults
    branding = branding or UB()
    colors = colors or theme.colors
    
    # Convert legacy slide
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
            # Add new fields support
            left_column=getattr(slide, 'left_column', None),
            right_column=getattr(slide, 'right_column', None),
            big_stat_number=getattr(slide, 'big_stat_number', None),
            big_stat_label=getattr(slide, 'big_stat_label', None),
        )
    
    # 1. Determine Template Type
    template_type_raw = _determine_template_type(slide)
    # Ensure we use the string value, not enum repr
    template_type = template_type_raw.value if hasattr(template_type_raw, 'value') else str(template_type_raw)
    
    # 2. Get the Content Template (HTML string)
    # Try DB first
    db_template = await get_db_template_async(template_type, layout_style)
    
    if db_template:
        content_template_str = db_template["html_template"]
        custom_css = db_template.get("css_styles", "")
    else:
        # Fallback to local file in app/templates/views/
        # Map types to filenames
        filename_map = {
            "content": "content.html",
            "two_column": "two_column.html",
            "two_col_image": "two_column.html",  # Reuse split
            "two_col_math": "two_column.html",   # Reuse split
            "title": "title.html",
            "timeline": "timeline.html",
            "big_stat": "big_stat.html",
            "grid_gallery": "grid_gallery.html",
            "comparison": "comparison.html",
            "quote": "quote.html",
            "diagram": "diagram.html",
            "references": "references.html",
            "thank_you": "thank_you.html",
            "section": "content.html",      # Reuse content layout
            "conclusion": "content.html",   # Reuse content layout
            "overview": "content.html",     # Reuse content layout
            "image": "two_column.html",     # Reuse split for image slides
            "equation": "two_column.html",  # Reuse split for equation slides
        }
        
        fname = filename_map.get(template_type, "content.html")
        file_path = VIEWS_DIR / fname
        
        if file_path.exists():
            content_template_str = file_path.read_text(encoding="utf-8")
        else:
            logger.error(f"Template fallback failed for {fname}, using content.html")
            content_template_str = (VIEWS_DIR / "content.html").read_text(encoding="utf-8")
        custom_css = ""
            
    # 3. Load SDK Assets
    slide_layout_css = _load_sdk_asset("slide-layout.css")
    slide_typography_css = _load_sdk_asset("slide-typography.css")
    katex_loader_js = _load_sdk_asset("katex-loader.js")
    
    # 4. Generate Theme CSS Variables
    theme_css_vars = _generate_theme_css_vars(theme, colors)
    
    # 5. Render Final HTML
    # We use Jinja2 to render the content_template which EXTENDS base.html
    # So we need to set up a loader that can find base.html
    from jinja2 import Environment, FileSystemLoader
    
    env = Environment(loader=FileSystemLoader(str(VIEWS_DIR)))
    
    # Create the template from string (but with ability to extend base.html from loader)
    # Note: Jinja's 'extends' works by path. Since content_template_str starts with {% extends "base.html" %},
    # it will look for base.html in VIEWS_DIR.
    # We can't use from_string() directly if we want inheritance from files unless we set up the env right.
    # Strategy: If it's a file fallback, just load via env.get_template.
    # If it's a DB string, utilize env.from_string().
    
    if db_template:
        template = env.from_string(content_template_str)
    else:
        template = env.get_template(fname)
        
    # Prepare Context
    context = {
        "slide": slide,
        "theme_css_vars": theme_css_vars,
        "slide_layout_css": slide_layout_css,
        "slide_typography_css": slide_typography_css,
        "katex_loader_js": katex_loader_js,
        "custom_css": custom_css,
        "branding": branding,
        "show_header": (slide_number > 1) or branding.show_on_title_slide,
        "show_number": (slide_number > 1),
        "total_slides": total_slides,
        "template_id": template_type,
        "slide_classes": f"slide-{template_type}",
        "content_classes": ""
    }
    
    try:
        final_html = template.render(**context)
        return final_html
    except Exception as e:
        logger.error(f"Jinja2 Rendering Failed: {e}", exc_info=True)
        return f"<h1>Error rendering slide {slide.order}</h1><pre>{e}</pre>"


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



# Legacy CSS Generator Removed
def _get_base_slide_css() -> str:
    """DEPRECATED: Using slide-layout.css from SDK instead."""
    return ""


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
