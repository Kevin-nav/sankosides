"""
SankoSlides Theme System

Slide themes with fixed structural properties (fonts, spacing, border-radius)
and configurable color palettes. Users can customize colors while maintaining
consistent visual design.

Also includes university branding support for academic presentations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ColorPalette(BaseModel):
    """User-configurable color palette for slides."""
    primary: str = "#0056A0"      # Main brand color
    secondary: str = "#FFD700"    # Accent/highlight color
    accent: str = "#00C853"       # Call-to-action, emphasis
    background: str = "#FFFFFF"   # Slide background
    surface: str = "#F5F5F5"      # Cards, containers
    text_primary: str = "#1A1A1A" # Main text
    text_secondary: str = "#666666"  # Captions, labels
    border: str = "#E0E0E0"       # Borders, dividers


class UniversityBranding(BaseModel):
    """
    University branding overlay for slides.
    
    Applied on top of the theme to add institution-specific elements.
    """
    university_name: str = ""
    university_badge_url: Optional[str] = None  # URL to university logo/badge
    badge_position: str = "top-right"  # top-left, top-right, bottom-left, bottom-right
    show_on_title_slide: bool = True
    show_on_content_slides: bool = True
    show_university_name_footer: bool = True  # Show name in title slide footer
    
    def has_branding(self) -> bool:
        """Check if any branding is configured."""
        return bool(self.university_name or self.university_badge_url)


class SlideTheme(BaseModel):
    """
    Slide style theme with fixed structure and configurable colors.
    
    Fixed Properties (cannot be changed by user):
    - Font families, sizes
    - Spacing, border-radius
    - Layout proportions
    
    Configurable (can be changed by user):
    - Color palette
    """
    id: str
    name: str
    description: str = ""
    
    # =========================================================================
    # FIXED STRUCTURAL PROPERTIES (Part of theme identity)
    # =========================================================================
    
    # Dimensions (Standard PowerPoint 16:9 at 96dpi)
    slide_width: str = "1280px"
    slide_height: str = "720px"
    
    # Typography - Projector-friendly sizes (readable at distance)
    font_heading: str = "Inter"
    font_body: str = "Inter"
    font_size_title: str = "56px"       # Was 48px
    font_size_heading: str = "44px"     # Was 32px
    font_size_subheading: str = "32px"  # Was 24px
    font_size_body: str = "24px"        # Was 18px - CRITICAL for readability
    font_size_caption: str = "18px"     # Was 14px
    font_weight_title: str = "700"
    font_weight_heading: str = "600"
    font_weight_body: str = "400"
    line_height: str = "1.6"            # Was 1.5 - more breathing room
    
    # Spacing (based on 16px unit)
    spacing_xs: str = "8px"
    spacing_sm: str = "16px"
    spacing_md: str = "24px"
    spacing_lg: str = "32px"
    spacing_xl: str = "48px"
    
    # Corners
    border_radius_sm: str = "4px"
    border_radius_md: str = "8px"
    border_radius_lg: str = "12px"
    
    # Shadows
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.05)"
    shadow_md: str = "0 4px 6px rgba(0,0,0,0.1)"
    shadow_lg: str = "0 10px 15px rgba(0,0,0,0.1)"
    
    # =========================================================================
    # CONFIGURABLE PROPERTIES (User can customize)
    # =========================================================================
    
    colors: ColorPalette = Field(default_factory=ColorPalette)
    
    # Custom CSS overrides for advanced styling (background shapes, specific layouts)
    css_overrides: str = ""
    
    def to_css_variables(self) -> str:
        """Generate CSS custom properties for the theme."""
        css = f"""
:root {{
  /* Layout */
  --slide-width: {self.slide_width};
  --slide-height: {self.slide_height};

  /* Typography */
  --font-heading: '{self.font_heading}', sans-serif;
  --font-body: '{self.font_body}', sans-serif;
  --font-size-title: {self.font_size_title};
  --font-size-heading: {self.font_size_heading};
  --font-size-subheading: {self.font_size_subheading};
  --font-size-body: {self.font_size_body};
  --font-size-caption: {self.font_size_caption};
  --font-weight-title: {self.font_weight_title};
  --font-weight-heading: {self.font_weight_heading};
  --font-weight-body: {self.font_weight_body};
  --line-height: {self.line_height};
  
  /* Spacing */
  --spacing-xs: {self.spacing_xs};
  --spacing-sm: {self.spacing_sm};
  --spacing-md: {self.spacing_md};
  --spacing-lg: {self.spacing_lg};
  --spacing-xl: {self.spacing_xl};
  
  /* Corners */
  --radius-sm: {self.border_radius_sm};
  --radius-md: {self.border_radius_md};
  --radius-lg: {self.border_radius_lg};
  
  /* Shadows */
  --shadow-sm: {self.shadow_sm};
  --shadow-md: {self.shadow_md};
  --shadow-lg: {self.shadow_lg};
  
  /* Colors (from palette) */
  --color-primary: {self.colors.primary};
  --color-secondary: {self.colors.secondary};
  --color-accent: {self.colors.accent};
  --color-background: {self.colors.background};
  --color-surface: {self.colors.surface};
  --color-text-primary: {self.colors.text_primary};
  --color-text-secondary: {self.colors.text_secondary};
  --color-border: {self.colors.border};
}}
"""
        return css.strip()


# =============================================================================
# DEFAULT THEMES
# =============================================================================

ACADEMIC_THEME = SlideTheme(
    id="academic",
    name="Academic",
    description="Clean, professional theme for university presentations",
    font_heading="Merriweather",
    font_body="Source Sans Pro",
    border_radius_sm="2px",
    border_radius_md="4px",
    border_radius_lg="6px",
    colors=ColorPalette(
        primary="#1A365D",      # Navy blue
        secondary="#C53030",    # Academic red
        accent="#2B6CB0",       # Accent blue
        background="#FFFFFF",
        surface="#F7FAFC",
        text_primary="#2D3748",
        text_secondary="#718096",
        border="#E2E8F0",
    )
)

MODERN_THEME = SlideTheme(
    id="modern",
    name="Modern",
    description="Bold, contemporary design with vibrant colors",
    font_heading="Inter",
    font_body="Inter",
    border_radius_sm="8px",
    border_radius_md="12px",
    border_radius_lg="16px",
    colors=ColorPalette(
        primary="#6366F1",      # Indigo
        secondary="#EC4899",    # Pink
        accent="#14B8A6",       # Teal
        background="#FFFFFF",
        surface="#F8FAFC",
        text_primary="#0F172A",
        text_secondary="#64748B",
        border="#E2E8F0",
    )
)

MINIMAL_THEME = SlideTheme(
    id="minimal",
    name="Minimal",
    description="Clean, distraction-free design with subtle accents",
    font_heading="Inter",
    font_body="Inter",
    font_weight_title="500",
    font_weight_heading="500",
    border_radius_sm="0px",
    border_radius_md="0px",
    border_radius_lg="2px",
    shadow_sm="none",
    shadow_md="none",
    shadow_lg="0 1px 3px rgba(0,0,0,0.1)",
    colors=ColorPalette(
        primary="#111827",      # Near black
        secondary="#6B7280",    # Gray
        accent="#3B82F6",       # Blue accent
        background="#FFFFFF",
        surface="#FAFAFA",
        text_primary="#111827",
        text_secondary="#6B7280",
        border="#E5E7EB",
    )
)

DARK_THEME = SlideTheme(
    id="dark",
    name="Dark",
    description="Dark mode theme for modern presentations",
    font_heading="Inter",
    font_body="Inter",
    colors=ColorPalette(
        primary="#818CF8",      # Light indigo
        secondary="#F472B6",    # Light pink
        accent="#34D399",       # Light green
        background="#0F172A",   # Slate 900
        surface="#1E293B",      # Slate 800
        text_primary="#F8FAFC", # Slate 50
        text_secondary="#94A3B8",  # Slate 400
        border="#334155",       # Slate 700
    )
)

UMAT_THEME = SlideTheme(
    id="umat",
    name="UMaT Official",
    description="Official University of Mines and Technology theme",
    font_heading="Arial", # Guidelines say Times New Roman, Arial, or Tahoma
    font_body="Arial",
    border_radius_sm="0px",
    border_radius_md="0px", # Academic usually sharp
    border_radius_lg="0px",
    colors=ColorPalette(
        primary="#1E3A5F",      # UMaT Blue
        secondary="#D4AF37",    # UMaT Gold
        accent="#1E3A5F",       
        background="#FFFFFF",
        surface="#F0F4F8",
        text_primary="#000000", # High contrast
        text_secondary="#333333",
        border="#D4AF37",       # Gold borders
    ),
    css_overrides="""
    /* UMaT Specific Styles */
    .slide-title .main-title {
        color: var(--color-primary);
        text-transform: uppercase;
        border-bottom: 2px solid var(--color-secondary);
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }
    .slide-title {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border: 10px solid var(--color-primary);
    }
    .university-badge {
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    }
    .slide-number {
        font-weight: bold;
        color: var(--color-primary);
    }
    /* Figure titles below, Table titles above */
    .slide-image .image-caption {
        margin-top: 10px;
        order: 2; /* Ensure it is visually below if flex used */
        font-style: italic;
    }
    
    /* Academic Info */
    .degree-statement {
        font-style: italic;
        margin-top: 24px;
        font-size: var(--font-size-body);
        color: var(--color-text-secondary);
    }
    .supervisor-info {
        margin-top: 12px;
        font-weight: bold;
        color: var(--color-text-primary);
    }
    """
)

PRO_MODERN_THEME = SlideTheme(
    id="pro_modern",
    name="Pro Modern",
    description="High-end corporate style with sidebar",
    font_heading="Outfit",
    font_body="Inter",
    border_radius_sm="8px",
    border_radius_md="12px",
    border_radius_lg="20px",
    colors=ColorPalette(
        primary="#2563EB",      # Blue 600
        secondary="#3B82F6",    # Blue 500
        accent="#F59E0B",       # Amber 500
        background="#FFFFFF",
        surface="#F3F4F6",      # Gray 100
        text_primary="#111827",
        text_secondary="#4B5563",
        border="#E5E7EB",
    ),
    css_overrides="""
    /* Sidebar Layout Override */
    .slide {
        padding-left: 120px !important; /* Make room for sidebar */
    }
    .slide::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        width: 100px;
        background: var(--color-primary);
        z-index: 0;
    }
    .slide::after {
        content: '';
        position: absolute;
        top: 0;
        left: 100px;
        bottom: 0;
        width: 10px;
        background: rgba(0,0,0,0.05);
        z-index: 0;
    }
    .slide-title {
        padding-left: var(--spacing-lg) !important; /* Reset padding for title */
        background: var(--color-primary);
        color: white !important;
    }
    .slide-title .main-title {
        color: white !important;
    }
    .slide-title .subtitle, .slide-title .author, .slide-title .date {
        color: rgba(255,255,255,0.9) !important;
    }
    .slide-title::before, .slide-title::after {
        display: none; /* Remove sidebar from title slide */
    }
    
    /* Decoration */
    .slide-content .header-region {
        border-bottom: 2px solid var(--color-surface);
        padding-bottom: var(--spacing-sm);
    }
    
    .academic-info {
        margin-top: var(--spacing-md);
        padding-top: var(--spacing-md);
        border-top: 1px solid rgba(255,255,255,0.2);
    }
    """
)


# Theme registry for lookup
DEFAULT_THEMES: Dict[str, SlideTheme] = {
    "academic": ACADEMIC_THEME,
    "modern": MODERN_THEME,
    "minimal": MINIMAL_THEME,
    "dark": DARK_THEME,
    "umat": UMAT_THEME,
    "pro_modern": PRO_MODERN_THEME,
}


def get_theme(theme_id: str) -> Optional[SlideTheme]:
    """Get a theme by ID."""
    return DEFAULT_THEMES.get(theme_id, MODERN_THEME)


def get_all_themes() -> List[SlideTheme]:
    """Get all available themes."""
    return list(DEFAULT_THEMES.values())


def create_custom_theme(
    base_theme_id: str,
    custom_colors: Optional[ColorPalette] = None,
    name: Optional[str] = None,
) -> SlideTheme:
    """
    Create a custom theme by overriding colors on a base theme.
    
    Args:
        base_theme_id: ID of the base theme to customize
        custom_colors: Custom color palette to apply
        name: Optional custom name for the theme
        
    Returns:
        New SlideTheme with custom colors
    """
    base = get_theme(base_theme_id)
    if not base:
        base = MODERN_THEME
    
    # Create copy with custom colors
    theme_data = base.model_dump()
    theme_data["id"] = f"custom_{base_theme_id}"
    
    if name:
        theme_data["name"] = name
    else:
        theme_data["name"] = f"Custom {base.name}"
    
    if custom_colors:
        theme_data["colors"] = custom_colors.model_dump()
    
    return SlideTheme(**theme_data)
