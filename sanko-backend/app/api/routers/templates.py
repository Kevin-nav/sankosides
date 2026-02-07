"""
Template System API Router - Convex Backend

Endpoints for managing slide templates, themes, and color palettes.
Also provides enhanced preview rendering for the frontend editor.

Data is stored in Convex and cached in Redis for performance.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncio

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.convex_client import get_convex_client
from app.services.unified_cache import template_cache, theme_cache, palette_cache, preview_cache
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Response Models
# =============================================================================

class TemplateResponse(BaseModel):
    id: str
    template_id: str
    name: str
    description: Optional[str]
    content_type: str
    category: str
    html_template: str
    css_styles: Optional[str]
    version: str

    class Config:
        from_attributes = True


class PaletteResponse(BaseModel):
    id: str
    name: str
    category: str
    colors: Dict[str, str]
    is_default: bool

    class Config:
        from_attributes = True


class ThemeResponse(BaseModel):
    id: str
    theme_id: str
    name: str
    description: Optional[str]
    palette: Optional[PaletteResponse]
    typography: Optional[Dict[str, str]]
    spacing: Optional[Dict[str, str]]
    borders: Optional[Dict[str, str]]

    class Config:
        from_attributes = True


router = APIRouter()


# =============================================================================
# CONVEX QUERY HELPERS
# =============================================================================

async def convex_query(fn_name: str, args: dict = None) -> Any:
    """Execute a Convex query with async wrapper and timeout."""
    convex = get_convex_client()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(convex.query, fn_name, args or {}),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.error(f"Convex query {fn_name} timed out")
        raise HTTPException(status_code=504, detail="Database query timed out")
    except Exception as e:
        logger.error(f"Convex query {fn_name} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def transform_template(t: dict) -> dict:
    """Transform Convex template to API response format."""
    return {
        "id": t.get("_id", ""),
        "template_id": t.get("templateId", ""),
        "name": t.get("name", ""),
        "description": t.get("description"),
        "content_type": t.get("contentType", ""),
        "category": t.get("category", ""),
        "html_template": t.get("htmlTemplate", ""),
        "css_styles": t.get("cssStyles"),
        "version": t.get("version", "1.0.0"),
    }


def transform_palette(p: dict) -> dict:
    """Transform Convex palette to API response format."""
    return {
        "id": p.get("_id", ""),
        "name": p.get("name", ""),
        "category": p.get("category", ""),
        "colors": p.get("colors", {}),
        "is_default": p.get("isDefault", False),
    }


def transform_theme(t: dict) -> dict:
    """Transform Convex theme to API response format."""
    palette = t.get("palette")
    return {
        "id": t.get("_id", ""),
        "theme_id": t.get("themeId", ""),
        "name": t.get("name", ""),
        "description": t.get("description"),
        "palette": transform_palette(palette) if palette else None,
        "typography": t.get("typography"),
        "spacing": t.get("spacing"),
        "borders": t.get("borders"),
    }


# =============================================================================
# TEMPLATES
# =============================================================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(category: Optional[str] = None):
    """
    List all active templates.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    Data source: Convex
    """
    cache_key = f"list:{category or 'all'}"
    
    # Check cache first
    cached = template_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch from Convex
    templates = await convex_query("templates:listTemplates", {"category": category} if category else {})
    
    # Transform to API format
    template_dicts = [transform_template(t) for t in templates]
    
    # Populate cache
    template_cache.set(cache_key, template_dicts)
    logger.info(f"Templates cache populated: {len(template_dicts)} items (category={category or 'all'})")
    
    return template_dicts


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """Get a specific template by its string identifier."""
    cache_key = f"single:{template_id}"
    
    cached = template_cache.get(cache_key)
    if cached:
        return cached
    
    template = await convex_query("templates:getTemplateFn", {"templateId": template_id})
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    result = transform_template(template)
    template_cache.set(cache_key, result)
    
    return result


# =============================================================================
# THEMES
# =============================================================================

@router.get("/themes", response_model=List[ThemeResponse])
async def list_themes():
    """
    List all available themes with their palettes.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    Data source: Convex
    """
    cache_key = "list:all"
    
    cached = theme_cache.get(cache_key)
    if cached:
        return cached
    
    # Convex listThemes already joins with palettes
    themes = await convex_query("templates:listThemes")
    
    theme_dicts = [transform_theme(t) for t in themes]
    
    theme_cache.set(cache_key, theme_dicts)
    logger.info(f"Themes cache populated: {len(theme_dicts)} items")
    
    return theme_dicts


@router.get("/themes/{theme_id}", response_model=ThemeResponse)
async def get_theme(theme_id: str):
    """
    Get a specific theme with its palette.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    """
    cache_key = f"single:{theme_id}"
    
    cached = theme_cache.get(cache_key)
    if cached:
        return cached
    
    theme = await convex_query("templates:getThemeFn", {"themeId": theme_id})
    
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    result = transform_theme(theme)
    theme_cache.set(cache_key, result)
    
    return result


# =============================================================================
# ENHANCED PREVIEW RENDERING
# =============================================================================

@router.get("/themes/{theme_id}/preview", response_class=HTMLResponse)
async def preview_theme_template(
    theme_id: str,
    template_type: str = "title",
):
    """
    Render an enhanced preview of a template with the specified theme.
    
    Features:
    - Dynamic theme application with CSS variables
    - Responsive slide container
    - Google Fonts integration
    - Template-specific mock data
    - Layout style variants (modern, split, default)
    
    CACHED: L1 (1 min) + L2 Redis (10 min)
    """
    cache_key = f"{theme_id}:{template_type}"
    
    cached_html = preview_cache.get(cache_key)
    if cached_html:
        return HTMLResponse(content=cached_html)
    
    # Fetch theme with palette from Convex
    theme = await convex_query("templates:getThemeFn", {"themeId": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    palette = theme.get("palette", {})
    colors = palette.get("colors", {}) if palette else {}
    typography = theme.get("typography", {})
    spacing = theme.get("spacing", {})
    borders = theme.get("borders", {})
    layout_style = theme.get("layoutStyle", "default")
    
    # Try to get layout-specific template first
    target_template_ids = []
    if layout_style and layout_style != "default":
        target_template_ids.append(f"{template_type}_{layout_style}")
    target_template_ids.append(template_type)
    
    template = None
    for tid in target_template_ids:
        template = await convex_query("templates:getTemplateFn", {"templateId": tid})
        if template:
            break
    
    if not template:
        # Fallback to content template
        template = await convex_query("templates:getTemplateFn", {"templateId": "content"})
    
    if not template:
        raise HTTPException(status_code=404, detail="No template found for preview")
    
    # Generate template-specific mock data
    from datetime import date
    mock_data = _get_mock_data(template_type, date.today())
    
    # Render the template
    from jinja2 import Template
    jinja_template = Template(template.get("htmlTemplate", ""))
    rendered_content = jinja_template.render(**mock_data)
    
    # Generate CSS variables
    css_vars = _generate_css_variables(colors, typography, spacing, borders)
    
    # Generate enhanced base styles
    base_styles = _generate_base_styles()
    
    # Get Google Fonts URL
    fonts_url = _get_google_fonts_url(typography)
    
    # Combine template and theme CSS
    template_css = template.get("cssStyles", "") or ""
    theme_overrides = theme.get("cssOverrides", "") or ""
    
    # Build complete HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{fonts_url}" rel="stylesheet">
    <style>
        {css_vars}
        {base_styles}
        {template_css}
        {theme_overrides}
    </style>
</head>
<body>
    {rendered_content}
</body>
</html>"""
    
    # Cache the rendered HTML
    preview_cache.set(cache_key, html)
    logger.info(f"Preview cache populated for {theme_id}/{template_type}")
    
    return HTMLResponse(content=html)


def _get_mock_data(template_type: str, today: 'date') -> dict:
    """Generate realistic mock data for each template type."""
    from datetime import date
    
    common = {
        "current_date": today.strftime("%B %Y"),
    }
    
    mock_data_by_type = {
        "title": {
            "slide": {
                "order": 1,
                "title": "The Future of AI in Education",
                "subtitle": "Transforming How We Learn and Teach",
                "author": "Dr. Sarah Chen",
                "date": today.strftime("%B %d, %Y"),
            }
        },
        "content": {
            "slide": {
                "order": 2,
                "title": "Key Learning Objectives",
                "bullet_points": [
                    "Understand the fundamentals of machine learning algorithms",
                    "Apply neural networks to real-world classification problems",
                    "Evaluate model performance using industry-standard metrics",
                    "Design ethical AI systems that prioritize fairness"
                ],
            }
        },
        "two_column": {
            "slide": {
                "order": 3,
                "title": "Traditional vs Modern Approaches",
                "left_column": {
                    "title": "Traditional Methods",
                    "content": [
                        "Manual data processing",
                        "Rule-based systems",
                        "Limited scalability",
                        "High maintenance cost"
                    ]
                },
                "right_column": {
                    "title": "AI-Powered Solutions",
                    "content": [
                        "Automated pattern recognition",
                        "Self-improving algorithms",
                        "Infinite scalability",
                        "Reduced operational costs"
                    ]
                },
                "left_points": ["Manual processing", "Rule-based", "Limited scale"],
                "right_points": ["Automated", "Self-learning", "Scalable"],
            }
        },
        "section": {
            "slide": {
                "order": 4,
                "title": "Part II: Implementation Strategies",
                "subtitle": "Practical Approaches",
            }
        },
        "conclusion": {
            "slide": {
                "order": 5,
                "title": "Key Takeaways",
                "bullet_points": [
                    "AI is revolutionizing education at every level",
                    "Personalized learning improves outcomes by 40%",
                    "Ethical considerations must guide development",
                    "The future is collaborative, not competitive"
                ],
                "call_to_action": "Start your AI journey today"
            }
        },
        "quote": {
            "slide": {
                "order": 6,
                "quote_text": "Education is not the filling of a pail, but the lighting of a fire.",
                "quote_author": "William Butler Yeats"
            }
        },
        "diagram": {
            "slide": {
                "order": 7,
                "title": "System Architecture",
                "diagram_mermaid": "graph TD; A[Input] --> B[Process]; B --> C[Output];",
                "bullet_points": ["A simplified view of the data flow"]
            }
        },
        "full_image": {
            "slide": {
                "order": 8,
                "title": "Visual Learning Impact",
                "image_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1280&q=80",
                "image_alt": "Students collaborating with AI tools",
                "image_caption": "AI-enhanced collaborative learning environment"
            }
        },
        "references": {
            "slide": {
                "order": 9,
                "title": "References",
                "formatted_citations": [
                    "Smith, J. (2023). <em>Machine Learning in Education</em>. Academic Press.",
                    "Chen, L., & Wang, M. (2024). Neural networks for adaptive learning. <em>Journal of AI Education</em>, 15(2), 45-67.",
                    "Johnson, R. (2023). Ethical AI frameworks. In <em>Proceedings of AI Conference</em> (pp. 123-145)."
                ]
            }
        },
        "thank_you": {
            "slide": {
                "order": 10,
                "author": "Dr. Sarah Chen",
                "email": "sarah.chen@university.edu",
                "date": today.strftime("%B %d, %Y"),
            },
            "logo_url": None
        }
    }
    
    data = mock_data_by_type.get(template_type, mock_data_by_type["content"])
    data.update(common)
    return data


def _generate_css_variables(colors: dict, typography: dict, spacing: dict, borders: dict) -> str:
    """Generate CSS custom properties from theme configuration."""
    return f"""
:root {{
    /* Layout */
    --slide-width: 1280px;
    --slide-height: 720px;
    
    /* Typography */
    --font-heading: '{typography.get("font_heading", "Inter")}', sans-serif;
    --font-body: '{typography.get("font_body", "Inter")}', sans-serif;
    --font-size-title: {typography.get("font_size_title", "56px")};
    --font-size-heading: {typography.get("font_size_heading", "44px")};
    --font-size-body: {typography.get("font_size_body", "24px")};
    
    /* Spacing */
    --spacing-sm: 12px;
    --spacing-md: {spacing.get("md", "24px")};
    --spacing-lg: {spacing.get("lg", "36px")};
    --spacing-xl: 48px;
    
    /* Colors */
    --color-primary: {colors.get("primary", "#1A365D")};
    --color-secondary: {colors.get("secondary", "#C53030")};
    --color-accent: {colors.get("accent", "#2B6CB0")};
    --color-background: {colors.get("background", "#FFFFFF")};
    --color-surface: {colors.get("surface", "#F7FAFC")};
    --color-text-primary: {colors.get("text_primary", "#2D3748")};
    --color-text-secondary: {colors.get("text_secondary", "#718096")};
    --color-border: {colors.get("border", "#E2E8F0")};
    
    /* Borders */
    --radius-sm: 4px;
    --radius-md: {borders.get("radius_md", "8px")};
    --radius-lg: 16px;
}}
"""


def _generate_base_styles() -> str:
    """Generate enhanced base styles for all slide types."""
    return """
/* Base Reset */
* { margin: 0; padding: 0; box-sizing: border-box; }

body { 
    width: var(--slide-width);
    height: var(--slide-height);
    overflow: hidden;
    background: var(--color-background);
    color: var(--color-text-primary);
    font-family: var(--font-body);
    font-size: var(--font-size-body);
    line-height: 1.5;
}

/* Slide Container */
.slide {
    width: 100%;
    height: 100%;
    padding: var(--spacing-lg) calc(var(--spacing-lg) * 2);
    display: flex;
    flex-direction: column;
    position: relative;
}

/* Header Region */
.header-region {
    margin-bottom: var(--spacing-lg);
}

.header-region h2,
.slide-title {
    font-family: var(--font-heading);
}

/* ===== TITLE SLIDE ===== */
.slide-title {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.slide-title h1,
.slide-title .main-title {
    font-family: var(--font-heading);
    font-size: var(--font-size-title);
    font-weight: 700;
    color: var(--color-primary);
    margin-bottom: var(--spacing-md);
    line-height: 1.1;
}

.slide-title .subtitle {
    font-size: calc(var(--font-size-heading) * 0.7);
    color: var(--color-text-secondary);
    margin-bottom: calc(var(--spacing-lg) * 1.5);
    max-width: 80%;
}

.slide-title .author,
.slide-title .date {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
}

.slide-title .date {
    font-size: calc(var(--font-size-body) * 0.85);
    opacity: 0.7;
    margin-top: calc(var(--spacing-md) * 0.5);
}

.title-footer {
    margin-top: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
}

/* ===== CONTENT SLIDE ===== */
.slide-content h2 {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    font-weight: 600;
    color: var(--color-primary);
    margin-bottom: var(--spacing-lg);
}

.slide-content ul,
.content-region ul {
    list-style: none;
    padding: 0;
}

.slide-content li,
.content-region li {
    font-size: var(--font-size-body);
    line-height: 1.6;
    margin-bottom: var(--spacing-md);
    padding-left: calc(var(--spacing-lg) * 1.2);
    position: relative;
}

.slide-content li::before,
.content-region li::before {
    content: "•";
    position: absolute;
    left: 0;
    color: var(--color-accent);
    font-size: calc(var(--font-size-body) * 1.4);
}

/* ===== SECTION SLIDE ===== */
.slide-section {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    background: var(--color-primary);
    color: white;
}

.slide-section h1,
.slide-section h2,
.slide-section .section-title {
    font-family: var(--font-heading);
    font-size: calc(var(--font-size-title) * 1.15);
    font-weight: 700;
    margin-bottom: var(--spacing-md);
    color: white;
}

.slide-section .subtitle {
    font-size: var(--font-size-heading);
    opacity: 0.9;
}

.section-decoration {
    width: 80px;
    height: 4px;
    background: white;
    opacity: 0.5;
    margin-top: var(--spacing-lg);
    border-radius: 2px;
}

/* ===== TWO COLUMN SLIDE ===== */
.slide-two-column h2 {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    font-weight: 600;
    color: var(--color-primary);
    margin-bottom: var(--spacing-lg);
}

.columns,
.columns-container {
    display: flex;
    gap: calc(var(--spacing-lg) * 2);
    flex: 1;
}

.column {
    flex: 1;
}

.column h3 {
    font-size: calc(var(--font-size-body) * 1.25);
    font-weight: 600;
    color: var(--color-secondary);
    margin-bottom: var(--spacing-md);
    padding-bottom: calc(var(--spacing-md) * 0.5);
    border-bottom: 2px solid var(--color-border);
}

.column ul {
    list-style: none;
    padding: 0;
}

.column li {
    font-size: var(--font-size-body);
    line-height: 1.5;
    margin-bottom: var(--spacing-md);
    padding-left: var(--spacing-md);
    position: relative;
}

.column li::before {
    content: "→";
    position: absolute;
    left: 0;
    color: var(--color-accent);
}

/* ===== QUOTE SLIDE ===== */
.slide-quote {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: calc(var(--spacing-lg) * 2) calc(var(--spacing-lg) * 3);
}

.slide-quote blockquote,
.slide-quote .main-quote {
    font-family: var(--font-heading);
    font-size: calc(var(--font-size-heading) * 1.1);
    font-style: italic;
    line-height: 1.5;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-lg);
    position: relative;
}

.slide-quote blockquote::before {
    content: '"';
    font-size: 4em;
    position: absolute;
    top: -0.3em;
    left: -0.3em;
    color: var(--color-accent);
    opacity: 0.2;
}

.slide-quote .author,
.slide-quote .quote-author,
.slide-quote .quote-attribution {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
}

/* ===== CONCLUSION SLIDE ===== */
.slide-conclusion h2 {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    color: var(--color-primary);
    margin-bottom: var(--spacing-lg);
}

.slide-conclusion ul,
.takeaways-region ul {
    list-style: none;
    padding: 0;
}

.slide-conclusion li,
.takeaways-region li {
    font-size: var(--font-size-body);
    margin-bottom: var(--spacing-md);
    padding-left: var(--spacing-lg);
    position: relative;
}

.slide-conclusion li::before,
.takeaways-region li::before {
    content: "✓";
    position: absolute;
    left: 0;
    color: var(--color-accent);
    font-weight: bold;
}

.conclusion-footer {
    margin-top: auto;
    text-align: center;
    font-size: calc(var(--font-size-heading) * 0.8);
    color: var(--color-secondary);
    font-weight: 600;
}

/* ===== DIAGRAM SLIDE ===== */
.slide-diagram {
    padding: var(--spacing-lg);
}

.slide-diagram h2 {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    color: var(--color-primary);
    margin-bottom: var(--spacing-lg);
}

.diagram-container {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
}

.diagram-svg,
.mermaid {
    max-width: 100%;
    max-height: 100%;
}

.diagram-caption {
    text-align: center;
    font-size: calc(var(--font-size-body) * 0.85);
    color: var(--color-text-secondary);
    margin-top: var(--spacing-md);
}

/* ===== FULL IMAGE SLIDE ===== */
.slide-full-image {
    position: relative;
    padding: 0;
}

.slide-full-image .background-image-container {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}

.slide-full-image .hero-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.slide-full-image .overlay-content {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: var(--spacing-xl) var(--spacing-lg);
    background: linear-gradient(transparent, rgba(0,0,0,0.7));
    color: white;
}

.slide-full-image .overlay-content h2,
.slide-full-image .overlay-content .slide-title {
    font-family: var(--font-heading);
    font-size: var(--font-size-heading);
    color: white;
    margin-bottom: var(--spacing-sm);
}

.slide-full-image .image-caption {
    font-size: calc(var(--font-size-body) * 0.9);
    opacity: 0.9;
}

/* ===== REFERENCES SLIDE ===== */
.slide-references .references-region {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-md);
}

.references-list {
    list-style: none;
    padding-left: 0;
}

.references-list li {
    font-size: 16px;
    line-height: 1.8;
    margin-bottom: var(--spacing-md);
    padding-left: calc(var(--spacing-lg) * 1.5);
    text-indent: calc(-1 * var(--spacing-lg) * 1.5);
}

.references-list li em {
    font-style: italic;
}

/* ===== THANK YOU SLIDE ===== */
.slide-thank-you {
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.thank-you-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-lg);
}

.thank-you-message {
    font-size: calc(var(--font-size-title) * 1.2);
    font-weight: 700;
    color: var(--color-primary);
    margin-bottom: var(--spacing-md);
}

.thank-you-logo {
    max-height: 80px;
    margin-bottom: var(--spacing-md);
}

.author-info {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
}

.presenter-name {
    font-weight: 600;
    font-size: calc(var(--font-size-body) * 1.2);
    color: var(--color-text-primary);
}

.presenter-email {
    font-size: var(--font-size-body);
    color: var(--color-primary);
}

.questions-prompt {
    font-size: calc(var(--font-size-heading) * 0.8);
    color: var(--color-text-secondary);
    font-style: italic;
    margin-top: var(--spacing-lg);
}

/* ===== TWO COLUMN IMAGE ===== */
.slide-two-col-image .image-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.slide-two-col-image .image-wrapper img {
    max-width: 100%;
    max-height: 400px;
    object-fit: contain;
    border-radius: var(--radius-md);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.slide-two-col-image .image-caption {
    font-size: calc(var(--font-size-body) * 0.85);
    color: var(--color-text-secondary);
    margin-top: var(--spacing-sm);
    font-style: italic;
}

/* ===== TWO COLUMN MATH ===== */
.slide-two-col-math .equation-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: var(--spacing-lg);
    background: var(--color-surface);
    border-radius: var(--radius-md);
}

.slide-two-col-math .math-svg,
.slide-two-col-math .latex-content {
    font-size: calc(var(--font-size-heading) * 0.8);
}
"""


def _get_google_fonts_url(typography: dict) -> str:
    """Generate Google Fonts URL for the theme's fonts."""
    heading_font = typography.get("font_heading", "Inter")
    body_font = typography.get("font_body", "Inter")
    
    fonts_to_load = set([heading_font, body_font])
    fonts_url_parts = []
    for font in fonts_to_load:
        font_encoded = font.replace(" ", "+")
        fonts_url_parts.append(f"family={font_encoded}:wght@400;500;600;700;800")
    
    return f"https://fonts.googleapis.com/css2?{'&'.join(fonts_url_parts)}&display=swap"


# =============================================================================
# PALETTES
# =============================================================================

@router.get("/palettes", response_model=List[PaletteResponse])
async def list_palettes():
    """
    List all color palettes.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    Data source: Convex
    """
    cache_key = "list:all"
    
    cached = palette_cache.get(cache_key)
    if cached:
        return cached
    
    palettes = await convex_query("templates:listPalettes")
    
    palette_dicts = [transform_palette(p) for p in palettes]
    
    palette_cache.set(cache_key, palette_dicts)
    logger.info(f"Palettes cache populated: {len(palette_dicts)} items")
    
    return palette_dicts


# =============================================================================
# CACHE MANAGEMENT (Admin)
# =============================================================================

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for monitoring.
    
    Returns L1/L2 cache sizes and connection status.
    """
    from app.services.unified_cache import pdf_kb_cache
    
    return {
        "templates": template_cache.stats(),
        "themes": theme_cache.stats(),
        "palettes": palette_cache.stats(),
        "previews": preview_cache.stats(),
        "pdf_kb": pdf_kb_cache.stats(),
        "data_source": "convex",
    }


@router.post("/cache/clear")
async def clear_all_caches():
    """
    Clear all caches (admin only).
    
    Use sparingly - forces all data to be re-fetched from Convex.
    """
    from app.services.unified_cache import pdf_kb_cache
    
    template_cache.invalidate_pattern("*")
    theme_cache.invalidate_pattern("*")
    palette_cache.invalidate_pattern("*")
    preview_cache.invalidate_pattern("*")
    pdf_kb_cache.invalidate_pattern("*")
    
    logger.warning("All caches cleared by admin request")
    
    return {"status": "all caches cleared", "data_source": "convex"}
