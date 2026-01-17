"""
Template System API Router

Endpoints for managing slide templates, themes, and color palettes.
Also provides preview rendering for the frontend editor.

CACHING STRATEGY:
- All list endpoints use shared 2-tier cache (L1 in-memory + L2 Redis)
- First user request populates cache, all subsequent users benefit
- Cache invalidation on admin CRUD operations
"""

from typing import List, Optional, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import get_async_session
from app.core.template_models import SlideTemplate, ThemePalette, ThemeConfig
from app.services.unified_cache import template_cache, theme_cache, palette_cache, preview_cache
from app.core.logging import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)

class TemplateResponse(BaseModel):
    id: UUID
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
    id: UUID
    name: str
    category: str
    colors: Dict[str, str]
    is_default: bool

    class Config:
        from_attributes = True

class ThemeResponse(BaseModel):
    id: UUID
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
# TEMPLATES
# =============================================================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all active templates.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    First request populates cache, all users benefit.
    """
    cache_key = f"list:{category or 'all'}"
    
    # Check cache first (L1 memory → L2 Redis)
    cached = template_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch from database
    query = select(SlideTemplate).where(SlideTemplate.is_active == True)
    
    if category:
        query = query.where(SlideTemplate.category == category)
        
    result = await session.execute(query)
    templates = result.scalars().all()
    
    # Convert to dicts for caching (ORM objects not serializable)
    template_dicts = [
        {
            "id": str(t.id),
            "template_id": t.template_id,
            "name": t.name,
            "description": t.description,
            "content_type": t.content_type,
            "category": t.category,
            "html_template": t.html_template,
            "css_styles": t.css_styles,
            "version": t.version,
        }
        for t in templates
    ]
    
    # Populate cache for future requests
    template_cache.set(cache_key, template_dicts)
    logger.info(f"Templates cache populated: {len(template_dicts)} items (category={category or 'all'})")
    
    return templates

@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific template by its ID or string identifier."""
    # Try UUID lookup first
    try:
        uuid_val = UUID(template_id)
        query = select(SlideTemplate).where(SlideTemplate.id == uuid_val)
    except ValueError:
        # Fallback to string template_id
        query = select(SlideTemplate).where(SlideTemplate.template_id == template_id)
        
    result = await session.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    return template

# =============================================================================
# THEMES
# =============================================================================

@router.get("/themes", response_model=List[ThemeResponse])
async def list_themes(
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all available themes.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    First request populates cache, all users benefit.
    """
    cache_key = "list:all"
    
    # Check cache first
    cached = theme_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch from database
    query = select(ThemeConfig).where(ThemeConfig.is_active == True).options(selectinload(ThemeConfig.palette))
    result = await session.execute(query)
    themes = result.scalars().all()
    
    # Convert to dicts for caching
    theme_dicts = [
        {
            "id": str(t.id),
            "theme_id": t.theme_id,
            "name": t.name,
            "description": t.description,
            "palette": {
                "id": str(t.palette.id),
                "name": t.palette.name,
                "category": t.palette.category,
                "colors": t.palette.colors,
                "is_default": t.palette.is_default,
            } if t.palette else None,
            "typography": t.typography,
            "spacing": t.spacing,
            "borders": t.borders,
        }
        for t in themes
    ]
    
    # Populate cache
    theme_cache.set(cache_key, theme_dicts)
    logger.info(f"Themes cache populated: {len(theme_dicts)} items")
    
    return themes

@router.get("/themes/{theme_id}", response_model=ThemeResponse)
async def get_theme(
    theme_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific theme.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    """
    cache_key = f"single:{theme_id}"
    
    # Check cache first
    cached = theme_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch from database
    query = select(ThemeConfig).where(ThemeConfig.theme_id == theme_id).options(selectinload(ThemeConfig.palette))
    result = await session.execute(query)
    theme = result.scalar_one_or_none()
    
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Convert to dict for caching
    theme_dict = {
        "id": str(theme.id),
        "theme_id": theme.theme_id,
        "name": theme.name,
        "description": theme.description,
        "palette": {
            "id": str(theme.palette.id),
            "name": theme.palette.name,
            "category": theme.palette.category,
            "colors": theme.palette.colors,
            "is_default": theme.palette.is_default,
        } if theme.palette else None,
        "typography": theme.typography,
        "spacing": theme.spacing,
        "borders": theme.borders,
    }
    
    # Populate cache for future requests
    theme_cache.set(cache_key, theme_dict)
    logger.info(f"Theme cache populated for theme_id: {theme_id}")
        
    return theme

# Note: RedisCache is still used by the unified_cache internally
# Preview caching is now handled by preview_cache from unified_cache

@router.get("/themes/{theme_id}/preview", response_class=HTMLResponse)
async def preview_theme_template(
    theme_id: str,
    template_type: str = "title",
    session: AsyncSession = Depends(get_async_session)
):
    """
    Render a preview of a template with the specified theme.
    Returns the complete HTML string.
    
    CACHED: L1 (1 min) + L2 Redis (10 min)
    First request populates cache, all users benefit instantly.
    """
    cache_key = f"{theme_id}:{template_type}"
    
    # Check cache first (L1 memory → L2 Redis)
    cached_html = preview_cache.get(cache_key)
    if cached_html:
        return HTMLResponse(content=cached_html)
    
    # 1. Get Theme with palette eagerly loaded
    query = select(ThemeConfig).where(ThemeConfig.theme_id == theme_id).options(selectinload(ThemeConfig.palette))
    result = await session.execute(query)
    theme = result.scalar_one_or_none()
    
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # 2. Get Template
    # Priority:
    # 1. Variant specific: {template_type}_{theme.layout_style}
    # 2. Standard/Default: {template_type}
    # 3. Fallback: content
    
    layout_style = theme.layout_style or "default"
    target_ids = []
    
    if layout_style != "default":
        target_ids.append(f"{template_type}_{layout_style}")
            
    # Always include the base type as fallback
    target_ids.append(template_type)
    
    query = select(SlideTemplate).where(SlideTemplate.template_id.in_(target_ids))
    result = await session.execute(query)
    found_templates = {t.template_id: t for t in result.scalars().all()}
    
    # Pick the best match
    template = None
    
    # 1. Try specific variant
    if layout_style != "default":
        template = found_templates.get(f"{template_type}_{layout_style}")
        
    # 2. Try base type
    if not template:
        template = found_templates.get(template_type)
        
    # 3. Fallback to generic content
    if not template:
        # Fallback to generic content template
        template_query = select(SlideTemplate).where(SlideTemplate.template_id == "content")
        result = await session.execute(template_query)
        template = result.scalar_one()

    # 3. Generate Mock Data based on template type
    from jinja2 import Template
    from datetime import date
    
    # Different mock data for different slide types
    mock_data_by_type = {
        "title": {
            "slide": {
                "order": 1,
                "title": "The Future of AI in Education",
                "subtitle": "Transforming How We Learn and Teach",
                "author": "Dr. Sarah Chen",
                "date": date.today().strftime("%B %d, %Y"),
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
                }
            }
        },
        "section": {
            "slide": {
                "order": 4,
                "title": "Part II",
                "subtitle": "Implementation Strategies",
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
        "image": {
            "slide": {
                "order": 7,
                "title": "Visual Learning Impact",
                "image_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1280&q=80",
                "image_alt": "Students collaborating with AI tools",
                "image_caption": "AI-enhanced collaborative learning environment"
            }
        }
    }
    
    # Get mock data for this template type, fallback to content
    mock_data = mock_data_by_type.get(template_type, mock_data_by_type["content"])
    mock_data["current_date"] = date.today().strftime("%B %Y")
    
    # 4. Generate CSS variables from theme
    palette = theme.palette.colors
    
    css_vars = f"""
:root {{
  /* Layout */
  --slide-width: 1280px;
  --slide-height: 720px;

  /* Typography */
  --font-heading: '{theme.typography.get("font_heading")}', sans-serif;
  --font-body: '{theme.typography.get("font_body")}', sans-serif;
  --font-size-title: {theme.typography.get("font_size_title")};
  --font-size-heading: {theme.typography.get("font_size_heading")};
  --font-size-body: {theme.typography.get("font_size_body")};
  
  /* Spacing */
  --spacing-md: {theme.spacing.get("md")};
  --spacing-lg: {theme.spacing.get("lg")};
  
  /* Colors */
  --color-primary: {palette.get("primary")};
  --color-secondary: {palette.get("secondary")};
  --color-accent: {palette.get("accent")};
  --color-background: {palette.get("background")};
  --color-surface: {palette.get("surface")};
  --color-text-primary: {palette.get("text_primary")};
  --color-text-secondary: {palette.get("text_secondary")};
  --color-border: {palette.get("border")};
  
  /* Borders */
  --radius-md: {theme.borders.get("radius_md", "8px")};
}}
"""

    # 5. Render Template
    jinja_template = Template(template.html_template)
    rendered_content = jinja_template.render(**mock_data)
    
    # 6. Get font families for Google Fonts
    heading_font = theme.typography.get("font_heading", "Inter")
    body_font = theme.typography.get("font_body", "Inter")
    # Build Google Fonts URL with proper weights
    fonts_to_load = set([heading_font, body_font])
    fonts_url_parts = []
    for font in fonts_to_load:
        # URL encode the font name and add common weights
        font_encoded = font.replace(" ", "+")
        fonts_url_parts.append(f"family={font_encoded}:wght@400;500;600;700")
    google_fonts_url = f"https://fonts.googleapis.com/css2?{'&'.join(fonts_url_parts)}&display=swap"
    
    # 7. Wrap in full HTML with theme-aware styles
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link href="{google_fonts_url}" rel="stylesheet">
    <style>
        {css_vars}
        
        /* Base styles */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            width: 1280px; 
            height: 720px; 
            overflow: hidden;
            background: var(--color-background);
            color: var(--color-text-primary);
            font-family: var(--font-body);
            font-size: var(--font-size-body);
        }}
        
        /* Slide container */
        .slide {{
            width: 100%;
            height: 100%;
            padding: var(--spacing-lg) calc(var(--spacing-lg) * 2);
            display: flex;
            flex-direction: column;
        }}
        
        /* Title slide specific */
        .slide-title {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}
        
        .slide-title h1 {{
            font-family: var(--font-heading);
            font-size: var(--font-size-title);
            font-weight: 700;
            color: var(--color-primary);
            margin-bottom: var(--spacing-md);
            line-height: 1.1;
            text-transform: none;
        }}
        
        .slide-title .subtitle {{
            font-size: calc(var(--font-size-heading) * 0.7);
            color: var(--color-text-secondary);
            margin-bottom: calc(var(--spacing-lg) * 1.5);
        }}
        
        .slide-title .author {{
            font-size: var(--font-size-body);
            color: var(--color-text-secondary);
        }}
        
        .slide-title .date {{
            font-size: calc(var(--font-size-body) * 0.85);
            color: var(--color-text-secondary);
            opacity: 0.7;
            margin-top: calc(var(--spacing-md) * 0.5);
        }}
        
        /* Header region (common to content slides) */
        .header-region {{
            margin-bottom: var(--spacing-lg);
        }}
        
        .header-region h2,
        .slide-title {{
            font-family: var(--font-heading);
        }}
        
        /* Content slide */
        .slide-content h2 {{
            font-family: var(--font-heading);
            font-size: var(--font-size-heading);
            font-weight: 600;
            color: var(--color-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .slide-content ul {{
            list-style: none;
            padding: 0;
        }}
        
        .slide-content li {{
            font-size: var(--font-size-body);
            line-height: 1.6;
            margin-bottom: var(--spacing-md);
            padding-left: calc(var(--spacing-lg) * 1.2);
            position: relative;
        }}
        
        .slide-content li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--color-accent);
            font-size: calc(var(--font-size-body) * 1.4);
        }}
        
        /* Section slide */
        .slide-section {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: var(--color-primary);
            color: white;
        }}
        
        .slide-section h2 {{
            font-family: var(--font-heading);
            font-size: calc(var(--font-size-title) * 1.15);
            font-weight: 700;
            margin-bottom: var(--spacing-md);
        }}
        
        .slide-section .subtitle {{
            font-size: var(--font-size-heading);
            opacity: 0.9;
        }}
        
        /* Two column slide */
        .slide-two-column h2 {{
            font-family: var(--font-heading);
            font-size: var(--font-size-heading);
            font-weight: 600;
            color: var(--color-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .columns, .columns-container {{
            display: flex;
            gap: calc(var(--spacing-lg) * 2);
            flex: 1;
        }}
        
        .column {{
            flex: 1;
        }}
        
        .column h3 {{
            font-size: calc(var(--font-size-body) * 1.25);
            font-weight: 600;
            color: var(--color-secondary);
            margin-bottom: var(--spacing-md);
            padding-bottom: calc(var(--spacing-md) * 0.5);
            border-bottom: 2px solid var(--color-border);
        }}
        
        .column ul {{
            list-style: none;
            padding: 0;
        }}
        
        .column li {{
            font-size: var(--font-size-body);
            line-height: 1.5;
            margin-bottom: var(--spacing-md);
            padding-left: var(--spacing-md);
            position: relative;
        }}
        
        .column li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--color-accent);
        }}
        
        /* Quote slide */
        .slide-quote {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: calc(var(--spacing-lg) * 2) calc(var(--spacing-lg) * 3);
        }}
        
        .slide-quote blockquote {{
            font-family: var(--font-heading);
            font-size: calc(var(--font-size-heading) * 1.1);
            font-style: italic;
            line-height: 1.5;
            color: var(--color-text-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .slide-quote .author {{
            font-size: var(--font-size-body);
            color: var(--color-text-secondary);
        }}
        
        /* Conclusion slide */
        .slide-conclusion h2 {{
            font-family: var(--font-heading);
            font-size: var(--font-size-heading);
            color: var(--color-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .slide-conclusion ul {{
            list-style: none;
            padding: 0;
        }}
        
        .slide-conclusion li {{
            font-size: var(--font-size-body);
            margin-bottom: var(--spacing-md);
            padding-left: var(--spacing-lg);
            position: relative;
        }}
        
        .slide-conclusion li::before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: var(--color-accent);
        }}
        
        /* Diagram slide */
        .slide-diagram {{
            padding: var(--spacing-lg);
        }}
        
        .slide-diagram h2 {{
            font-family: var(--font-heading);
            font-size: var(--font-size-heading);
            color: var(--color-primary);
            margin-bottom: var(--spacing-lg);
        }}
        
        .diagram-container {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        
        /* Title footer for title slides */
        .title-footer {{
            margin-top: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        /* Full image slide */
        .slide-full-image {{
            position: relative;
            padding: 0;
        }}
        
        .slide-full-image .hero-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .slide-full-image .overlay-content {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: var(--spacing-lg);
            background: linear-gradient(transparent, rgba(0,0,0,0.7));
            color: white;
        }}
        
        {template.css_styles or ""}
        
        /* Theme-specific layout overrides */
        {theme.css_overrides or ""}
    </style>
</head>
<body>
    {rendered_content}
</body>
</html>"""

    # Cache the rendered HTML (L1 + L2)
    preview_cache.set(cache_key, html)
    logger.info(f"Preview cache populated for {theme_id}/{template_type}")
    
    return HTMLResponse(content=html)

# =============================================================================
# PALETTES
# =============================================================================

class PaletteUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    colors: Optional[Dict[str, str]] = None

class PaletteCreateRequest(BaseModel):
    name: str
    category: str = "custom"
    colors: Dict[str, str]

@router.get("/palettes", response_model=List[PaletteResponse])
async def list_palettes(
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all color palettes.
    
    CACHED: L1 (5 min) + L2 Redis (1 hour)
    First request populates cache, all users benefit.
    """
    cache_key = "list:all"
    
    # Check cache first
    cached = palette_cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch from database
    query = select(ThemePalette)
    result = await session.execute(query)
    palettes = result.scalars().all()
    
    # Convert to dicts for caching
    palette_dicts = [
        {
            "id": str(p.id),
            "name": p.name,
            "category": p.category,
            "colors": p.colors,
            "is_default": p.is_default,
        }
        for p in palettes
    ]
    
    # Populate cache
    palette_cache.set(cache_key, palette_dicts)
    logger.info(f"Palettes cache populated: {len(palette_dicts)} items")
    
    return palettes

@router.post("/palettes", response_model=PaletteResponse)
async def create_palette(
    data: PaletteCreateRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new color palette. Invalidates cache."""
    palette = ThemePalette(
        name=data.name,
        category=data.category,
        colors=data.colors,
        is_default=False,
        is_system=False
    )
    session.add(palette)
    await session.commit()
    await session.refresh(palette)
    
    # Invalidate palettes cache so new palette is visible
    palette_cache.invalidate("list:all")
    logger.info(f"Palette created: {data.name} - cache invalidated")
    
    return palette

@router.put("/palettes/{palette_id}", response_model=PaletteResponse)
async def update_palette(
    palette_id: str,
    data: PaletteUpdateRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Update an existing color palette."""
    # Try UUID lookup
    try:
        uuid_val = UUID(palette_id)
        query = select(ThemePalette).where(ThemePalette.id == uuid_val)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid palette ID")
    
    result = await session.execute(query)
    palette = result.scalar_one_or_none()
    
    if not palette:
        raise HTTPException(status_code=404, detail="Palette not found")
    
    # Update fields if provided
    if data.name is not None:
        palette.name = data.name
    if data.category is not None:
        palette.category = data.category
    if data.colors is not None:
        palette.colors = data.colors
    
    await session.commit()
    await session.refresh(palette)
    
    # Invalidate palettes cache
    palette_cache.invalidate("list:all")
    logger.info(f"Palette updated: {palette_id} - cache invalidated")
    
    return palette

@router.delete("/palettes/{palette_id}")
async def delete_palette(
    palette_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a color palette (only non-system palettes)."""
    try:
        uuid_val = UUID(palette_id)
        query = select(ThemePalette).where(ThemePalette.id == uuid_val)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid palette ID")
    
    result = await session.execute(query)
    palette = result.scalar_one_or_none()
    
    if not palette:
        raise HTTPException(status_code=404, detail="Palette not found")
    
    if palette.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system palettes")
    
    await session.delete(palette)
    await session.commit()
    
    # Invalidate palettes cache
    palette_cache.invalidate("list:all")
    logger.info(f"Palette deleted: {palette_id} - cache invalidated")
    
    return {"status": "deleted"}


# =============================================================================
# CACHE MANAGEMENT (Admin)
# =============================================================================

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for monitoring.
    
    Returns L1/L2 cache sizes and connection status.
    Useful for debugging cache performance.
    """
    from app.services.unified_cache import pdf_kb_cache
    
    return {
        "templates": template_cache.stats(),
        "themes": theme_cache.stats(),
        "palettes": palette_cache.stats(),
        "previews": preview_cache.stats(),
        "pdf_kb": pdf_kb_cache.stats(),
    }


@router.post("/cache/clear")
async def clear_all_caches():
    """
    Clear all caches (admin only).
    
    Use sparingly - forces all data to be re-fetched from database.
    """
    from app.services.unified_cache import pdf_kb_cache
    
    template_cache.invalidate_pattern("*")
    theme_cache.invalidate_pattern("*")
    palette_cache.invalidate_pattern("*")
    preview_cache.invalidate_pattern("*")
    pdf_kb_cache.invalidate_pattern("*")
    
    logger.warning("All caches cleared by admin request")
    
    return {"status": "all caches cleared"}
