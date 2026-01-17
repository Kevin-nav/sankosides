"""
Seed Templates and Themes

Populates the database with the initial set of templates and themes.
Migrates the hardcoded designs from app/templates/layouts/*.py and app/themes/*.py.
"""

import asyncio
import sys
import os
from uuid import uuid4

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db
from app.core.template_models import SlideTemplate, ThemePalette, ThemeConfig
from sqlalchemy import select

# =============================================================================
# TEMPLATES (Jinja2 Format)
# =============================================================================

TEMPLATES = [
    {
        "template_id": "title",
        "name": "Title Slide",
        "description": "Opening slide with title, subtitle, and author info",
        "content_type": "title",
        "html_template": """
<div class="slide slide-title" data-template="title" data-slide-id="{{ slide.order }}">
    <div class="title-content">
        <h1 class="main-title">{{ slide.title }}</h1>
        <p class="subtitle">{{ slide.bullet_points[0] if slide.bullet_points else '' }}</p>
    </div>
    <div class="title-footer">
        <span class="author">Presented by Author</span>
        <span class="date">{{ current_date }}</span>
    </div>
</div>
"""
    },
    {
        "template_id": "content",
        "name": "Standard Content",
        "description": "Title with bullet points",
        "content_type": "content",
        "html_template": """
<div class="slide slide-content" data-template="content" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="content-region">
        {% if slide.bullet_points %}
        <ul>
            {% for point in slide.bullet_points %}
            <li>{{ point }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
</div>
"""
    },
    {
        "template_id": "two_column",
        "name": "Two Column",
        "description": "Split layout for side-by-side content",
        "content_type": "two_column",
        "html_template": """
<div class="slide slide-two-column" data-template="two_column" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="columns-container">
        <div class="column left-column">
            {% if slide.left_points %}
            <ul>
                {% for point in slide.left_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        <div class="column right-column">
            {% if slide.right_points %}
            <ul>
                {% for point in slide.right_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
    </div>
</div>
"""
    },
    {
        "template_id": "two_col_image",
        "name": "Two Column Image",
        "description": "Bullet points on the left, image on the right with caption and attribution",
        "content_type": "two_col_image",
        "html_template": """
<div class="slide slide-two-col-image" data-template="two_col_image" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="columns-container">
        <div class="column content-column">
            {% if slide.bullet_points %}
            <ul>
                {% for point in slide.bullet_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        <div class="column image-column">
            <div class="image-wrapper">
                 <img src="{{ slide.image_url or 'https://via.placeholder.com/600x400?text=Placeholder+Image' }}" alt="{{ slide.image_alt or 'Slide image' }}" />
                 <div class="image-attribution">
                     {% if slide.image_caption %}
                     <p class="image-caption">{{ slide.image_caption }}</p>
                     {% endif %}
                     {% if slide.image_source %}
                     <p class="image-source">{{ slide.image_source }}</p>
                     {% endif %}
                 </div>
            </div>
        </div>
    </div>
</div>
""",
        "css_styles": """
.image-column {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.image-column img {
    max-width: 100%;
    max-height: 400px;
    object-fit: contain;
    border-radius: var(--radius-md);
}

.image-attribution {
    text-align: center;
    margin-top: var(--spacing-sm);
}

.image-caption {
    font-size: var(--font-size-caption, 14px);
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 4px;
}

.image-source {
    font-size: 12px;
    color: var(--color-text-secondary);
    font-style: italic;
}
"""
    },
    {
        "template_id": "diagram",
        "name": "Diagram Slide",
        "description": "Mermaid diagram visualization",
        "content_type": "diagram",
        "html_template": """
<div class="slide slide-diagram" data-template="diagram" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="diagram-container">
        {% if slide.diagram_svg %}
        <div class="diagram-svg">{{ slide.diagram_svg | safe }}</div>
        {% else %}
        <div class="mermaid">{{ slide.diagram_mermaid or 'graph TD; A-->B;' }}</div>
        {% endif %}
        
        {% if slide.bullet_points %}
        <div class="diagram-caption"><p>{{ slide.bullet_points[0] }}</p></div>
        {% endif %}
    </div>
</div>
"""
    },
    {
        "template_id": "section",
        "name": "Section Divider",
        "description": "Section title slide",
        "content_type": "section",
        "html_template": """
<div class="slide slide-section" data-template="section" data-slide-id="{{ slide.order }}">
    <div class="section-content">
        <h1 class="section-title">{{ slide.title }}</h1>
        <div class="section-decoration"></div>
    </div>
</div>
"""
    },
    {
        "template_id": "conclusion",
        "name": "Conclusion",
        "description": "Closing slide with key takeaways",
        "content_type": "conclusion",
        "html_template": """
<div class="slide slide-conclusion" data-template="conclusion" data-slide-id="{{ slide.order }}">
    <div class="conclusion-header">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="takeaways-region">
        {% if slide.bullet_points %}
        <ul>
            {% for point in slide.bullet_points %}
            <li>{{ point }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    <div class="conclusion-footer">
        <p>Thank You</p>
    </div>
</div>
"""
    },
    {
        "template_id": "two_col_math",
        "name": "Two Column Math",
        "description": "Text on left, Equation on right",
        "content_type": "two_col_math",
        "html_template": """
<div class="slide slide-two-col-math" data-template="two_col_math" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="columns-container">
        <div class="column content-column">
            {% if slide.bullet_points %}
            <ul>
                {% for point in slide.bullet_points %}
                <li>{{ point }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        <div class="column math-column">
            <div class="equation-wrapper">
                {% if slide.equation_svg %}
                <div class="math-svg">{{ slide.equation_svg | safe }}</div>
                {% else %}
                <div class="latex-content">$${{ slide.equation_latex or 'E = mc^2' }}$$</div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
"""
    },
    {
        "template_id": "full_image",
        "name": "Full Screen Image",
        "description": "Large hero image with overlay title",
        "content_type": "full_image",
        "html_template": """
<div class="slide slide-full-image" data-template="full_image" data-slide-id="{{ slide.order }}">
    <div class="background-image-container">
        <img src="{{ slide.image_url or 'https://via.placeholder.com/1280x720?text=Hero+Image' }}" alt="{{ slide.image_alt or 'Full screen image' }}" class="hero-image" />
    </div>
    <div class="overlay-content">
        <h2 class="slide-title">{{ slide.title }}</h2>
        {% if slide.image_caption %}
        <p class="image-caption">{{ slide.image_caption }}</p>
        {% elif slide.bullet_points %}
        <p class="image-caption">{{ slide.bullet_points[0] }}</p>
        {% endif %}
    </div>
</div>
"""
    },
    {
        "template_id": "quote",
        "name": "Quote",
        "description": "Large quote with attribution",
        "content_type": "quote",
        "html_template": """
<div class="slide slide-quote" data-template="quote" data-slide-id="{{ slide.order }}">
    <div class="quote-content">
        <blockquote class="main-quote">
            "{{ slide.quote_text }}"
        </blockquote>
        <div class="quote-attribution">
            <span class="quote-author">— {{ slide.quote_author }}</span>
        </div>
    </div>
</div>
"""
    },
    {
        "template_id": "references",
        "name": "References Slide",
        "description": "Bibliography/References slide with formatted citations",
        "content_type": "references",
        "html_template": """
<div class="slide slide-references" data-template="references" data-slide-id="{{ slide.order }}">
    <div class="header-region">
        <h2 class="slide-title">{{ slide.title }}</h2>
    </div>
    <div class="references-region">
        {% if slide.formatted_citations %}
        <ul class="references-list">
            {% for citation in slide.formatted_citations %}
            <li>{{ citation | safe }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
</div>
""",
        "css_styles": """
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
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: var(--spacing-sm);
    padding-left: var(--spacing-md);
    text-indent: calc(-1 * var(--spacing-md));
}
.references-list li em {
    font-style: italic;
}
"""
    },
    {
        "template_id": "thank_you",
        "name": "Thank You Slide",
        "description": "Professional thank you closing slide with author info",
        "content_type": "thank_you",
        "html_template": """
<div class="slide slide-thank-you" data-template="thank_you" data-slide-id="{{ slide.order }}">
    <div class="thank-you-content">
        {% if logo_url %}
        <img class="thank-you-logo" src="{{ logo_url }}" alt="Logo">
        {% endif %}
        <h1 class="thank-you-message">Thank You</h1>
        <div class="author-info">
            {% if slide.author %}
            <p class="presenter-name">{{ slide.author }}</p>
            {% endif %}
            {% if slide.email %}
            <p class="presenter-email">{{ slide.email }}</p>
            {% endif %}
            {% if slide.date %}
            <p class="presentation-date">{{ slide.date }}</p>
            {% endif %}
        </div>
        <p class="questions-prompt">Questions?</p>
    </div>
</div>
""",
        "css_styles": """
.slide-thank-you {
    display: flex !important;
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
    font-size: 72px;
    font-weight: var(--font-weight-title);
    color: var(--color-primary);
    margin-bottom: var(--spacing-md);
}
.author-info {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
}
.presenter-name {
    font-weight: 600;
    font-size: 28px;
    color: var(--color-text-primary);
}
.presenter-email {
    font-size: 20px;
    color: var(--color-primary);
}
.questions-prompt {
    font-size: 32px;
    color: var(--color-text-secondary);
    font-style: italic;
    margin-top: var(--spacing-lg);
}
.thank-you-logo {
    max-height: 80px;
    margin-bottom: var(--spacing-md);
}
"""
    }
]

# =============================================================================
# THEMES
# =============================================================================


PALETTES = [
    {
        "name": "Modern Indigo",
        "category": "modern",
        "is_default": True,
        "colors": {
            "primary": "#6366F1",      # Indigo
            "secondary": "#EC4899",    # Pink
            "accent": "#14B8A6",       # Teal
            "background": "#FFFFFF",
            "surface": "#F8FAFC",
            "text_primary": "#0F172A",
            "text_secondary": "#64748B",
            "border": "#E2E8F0",
        }
    },
    {
        "name": "Academic Blue",
        "category": "academic",
        "is_default": False,
        "colors": {
            "primary": "#1A365D",      # Navy blue
            "secondary": "#C53030",    # Academic red
            "accent": "#2B6CB0",       # Accent blue
            "background": "#FFFFFF",
            "surface": "#F7FAFC",
            "text_primary": "#2D3748",
            "text_secondary": "#718096",
            "border": "#E2E8F0",
        }
    },
    {
        "name": "Minimal Dark",
        "category": "minimal",
        "is_default": False,
        "colors": {
            "primary": "#F9FAFB",      # Gray 50
            "secondary": "#9CA3AF",    # Gray 400
            "accent": "#3B82F6",       # Blue 500
            "background": "#111827",   # Gray 900
            "surface": "#1F2937",      # Gray 800
            "text_primary": "#F9FAFB",
            "text_secondary": "#9CA3AF",
            "border": "#374151",
        }
    },
    # =========================================================================
    # NEW: Reveal.js Inspired Palettes
    # =========================================================================
    {
        "name": "Dracula",
        "category": "dark",
        "is_default": False,
        "colors": {
            "primary": "#BD93F9",      # Purple (headings)
            "secondary": "#FF79C6",    # Pink (links)
            "accent": "#8BE9FD",       # Cyan (hover)
            "background": "#282A36",   # Dark background
            "surface": "#44475A",      # Selection/surface
            "text_primary": "#F8F8F2", # Light text
            "text_secondary": "#6272A4", # Comments/secondary
            "border": "#44475A",
        }
    },
    {
        "name": "Solarized Light",
        "category": "minimal",
        "is_default": False,
        "colors": {
            "primary": "#586E75",      # Heading color
            "secondary": "#D33682",    # Magenta (selection)
            "accent": "#268BD2",       # Blue (links)
            "background": "#FDF6E3",   # Cream background
            "surface": "#EEE8D5",      # Base2 (surface)
            "text_primary": "#657B83", # Base00 (body text)
            "text_secondary": "#93A1A1", # Base1 (secondary)
            "border": "#EEE8D5",
        }
    },
    {
        "name": "Night Blue",
        "category": "dark",
        "is_default": False,
        "colors": {
            "primary": "#8AADF4",      # Light blue
            "secondary": "#F5A97F",    # Peach
            "accent": "#A6DA95",       # Green
            "background": "#24273A",   # Dark blue-gray
            "surface": "#363A4F",      # Surface
            "text_primary": "#CAD3F5", # Light text
            "text_secondary": "#A5ADCB", # Secondary text
            "border": "#494D64",
        }
    },
    {
        "name": "Simple White",
        "category": "minimal",
        "is_default": False,
        "colors": {
            "primary": "#000000",      # Black headings
            "secondary": "#333333",    # Dark gray
            "accent": "#0000EE",       # Classic blue links
            "background": "#FFFFFF",   # Pure white
            "surface": "#F5F5F5",      # Light gray
            "text_primary": "#000000",
            "text_secondary": "#666666",
            "border": "#DDDDDD",
        }
    },
    {
        "name": "UMaT Official",
        "category": "academic",
        "is_default": False,
        "colors": {
            "primary": "#1E3A5F",      # UMaT Blue
            "secondary": "#D4AF37",    # UMaT Gold
            "accent": "#1E3A5F",       
            "background": "#FFFFFF",
            "surface": "#F0F4F8",
            "text_primary": "#000000", # High contrast
            "text_secondary": "#333333",
            "border": "#D4AF37",       # Gold borders
        }
    },
    {
        "name": "Pro Modern",
        "category": "modern",
        "is_default": False,
        "colors": {
            "primary": "#2563EB",      # Blue 600
            "secondary": "#3B82F6",    # Blue 500
            "accent": "#F59E0B",       # Amber 500
            "background": "#FFFFFF",
            "surface": "#F3F4F6",      # Gray 100
            "text_primary": "#111827",
            "text_secondary": "#4B5563",
            "border": "#E5E7EB",
        }
    }
]

THEMES = [
    {
        "theme_id": "modern",
        "name": "Modern",
        "description": "Bold, contemporary design with vibrant colors",
        "palette_name": "Modern Indigo",
        "typography": {
            "font_heading": "Inter",
            "font_body": "Inter",
            "font_size_title": "56px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "24px",
            "lg": "40px"
        },
        "borders": {
            "radius_md": "16px"
        },
        "css_overrides": """
/* Modern: Centered, rounded, subtle shadows */
.slide-title h1 {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.slide-content li::before {
    content: "";
    width: 10px;
    height: 10px;
    background: var(--color-accent);
    border-radius: 50%;
    top: 0.5em;
}

.slide-section {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
}

.header-region h2 {
    padding-bottom: 12px;
    border-bottom: 3px solid var(--color-accent);
    display: inline-block;
}
"""
    },
    {
        "theme_id": "academic",
        "name": "Academic",
        "description": "Clean, professional theme for university presentations",
        "palette_name": "Academic Blue",
        "typography": {
            "font_heading": "Merriweather",
            "font_body": "Source Sans Pro",
            "font_size_title": "56px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "24px",
            "lg": "36px"
        },
        "borders": {
            "radius_md": "4px"
        },
        "css_overrides": """
/* Academic: Left-aligned, formal, serif accents */
.slide-title {
    align-items: flex-start;
    text-align: left;
    padding-left: 100px;
}

.slide-title h1 {
    border-left: 5px solid var(--color-primary);
    padding-left: 28px;
}

.slide-title .subtitle {
    padding-left: 32px;
    font-style: italic;
}

.header-region h2 {
    border-bottom: 2px solid var(--color-border);
    padding-bottom: 16px;
}

.slide-content li::before {
    content: "■";
    font-size: 0.6em;
    top: 0.4em;
}

.slide-section {
    align-items: flex-start;
    text-align: left;
    padding-left: 100px;
}

.slide-quote blockquote {
    text-align: left;
    border-left: 4px solid var(--color-secondary);
    padding-left: 32px;
}
"""
    },
    # =========================================================================
    # Reveal.js Inspired Themes
    # =========================================================================
    {
        "theme_id": "dracula",
        "name": "Dracula",
        "description": "Dark theme with vibrant purple and pink accents. Based on draculatheme.com",
        "palette_name": "Dracula",
        "typography": {
            "font_heading": "League Gothic",
            "font_body": "Lato",
            "font_size_title": "72px",
            "font_size_heading": "48px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "20px",
            "lg": "36px"
        },
        "borders": {
            "radius_md": "8px"
        },
        "css_overrides": """
/* Dracula: Dramatic, uppercase titles, gothic feel */
.slide-title h1 {
    text-transform: uppercase;
    letter-spacing: 6px;
    border-bottom: 4px solid var(--color-secondary);
    padding-bottom: 24px;
}

.slide-title .subtitle {
    letter-spacing: 2px;
    opacity: 0.9;
}

.header-region h2 {
    text-transform: uppercase;
    letter-spacing: 3px;
}

.slide-content li::before {
    content: "›";
    font-size: 1.6em;
    font-weight: bold;
    color: var(--color-secondary);
    top: -0.1em;
}

.slide-section h1,
.slide-section h2 {
    text-transform: uppercase;
    letter-spacing: 8px;
    text-shadow: 0 0 40px var(--color-secondary);
}

.slide-quote blockquote {
    border-top: 2px solid var(--color-secondary);
    border-bottom: 2px solid var(--color-secondary);
    padding: 32px 0;
}
"""
    },
    {
        "theme_id": "solarized",
        "name": "Solarized",
        "description": "Warm cream tones with excellent readability. Based on Ethan Schoonover's Solarized palette",
        "palette_name": "Solarized Light",
        "typography": {
            "font_heading": "Playfair Display",
            "font_body": "Lato",
            "font_size_title": "58px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "22px",
            "lg": "34px"
        },
        "borders": {
            "radius_md": "2px"
        },
        "css_overrides": """
/* Solarized: Classic, warm, elegant serif */
.slide-title h1 {
    font-weight: 400;
    font-style: italic;
}

.slide-title .subtitle {
    letter-spacing: 1px;
}

.header-region h2 {
    font-weight: 400;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 12px;
}

.slide-content li::before {
    content: "—";
    font-weight: normal;
    color: var(--color-accent);
}

.slide-section {
    background: var(--color-surface);
    color: var(--color-primary);
}

.slide-section h1,
.slide-section h2 {
    font-weight: 400;
    font-style: italic;
}

.slide-quote blockquote {
    font-weight: 400;
    font-size: calc(var(--font-size-heading) * 1.2);
}
"""
    },
    {
        "theme_id": "night",
        "name": "Night",
        "description": "Modern dark theme with blue-gray tones and soft accents",
        "palette_name": "Night Blue",
        "typography": {
            "font_heading": "Inter",
            "font_body": "Inter",
            "font_size_title": "58px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "26px",
            "lg": "42px"
        },
        "borders": {
            "radius_md": "12px"
        },
        "css_overrides": """
/* Night: Floating cards, soft glows, modern dark UI */
.slide {
    background: linear-gradient(180deg, var(--color-background) 0%, #1e2030 100%);
}

.slide-title h1 {
    text-shadow: 0 0 60px var(--color-primary);
}

.header-region h2 {
    background: var(--color-surface);
    padding: 16px 28px;
    border-radius: 8px;
    display: inline-block;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.slide-content li {
    background: var(--color-surface);
    padding: 16px 24px;
    border-radius: 8px;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}

.slide-content li::before {
    content: "○";
    color: var(--color-accent);
    position: static;
    margin-right: 16px;
}

.slide-section {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
    box-shadow: inset 0 0 100px rgba(0,0,0,0.3);
}

.slide-quote {
    background: var(--color-surface);
    border-radius: 24px;
    margin: 40px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4);
}
"""
    },
    {
        "theme_id": "simple",
        "name": "Simple",
        "description": "Clean, minimalist black-on-white design for maximum clarity",
        "palette_name": "Simple White",
        "typography": {
            "font_heading": "Georgia",
            "font_body": "Palatino Linotype",
            "font_size_title": "56px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "24px",
            "lg": "36px"
        },
        "borders": {
            "radius_md": "0px"
        },
        "css_overrides": """
/* Simple: Maximum whitespace, no decorations, classic typography */
.slide-title {
    align-items: flex-start;
    text-align: left;
}

.slide-title h1 {
    font-weight: 400;
    line-height: 1.2;
}

.slide-title .subtitle {
    font-style: italic;
    margin-top: 16px;
}

.header-region h2 {
    font-weight: 400;
}

.slide-content li::before {
    content: "—";
    font-weight: normal;
}

.slide-content li {
    padding-left: 48px;
}

.slide-section {
    background: var(--color-background);
    color: var(--color-text-primary);
    border-top: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
}

.slide-quote blockquote {
    font-size: calc(var(--font-size-heading) * 1.3);
    font-weight: 400;
}

.slide-quote .author {
    font-style: italic;
}
"""
    },
    {
        "theme_id": "umat",
        "name": "UMaT Official",
        "description": "Official University of Mines and Technology theme",
        "palette_name": "UMaT Official",
        "typography": {
            "font_heading": "Arial", 
            "font_body": "Arial",
            "font_size_title": "56px",
            "font_size_heading": "44px",
            "font_size_body": "24px"
        },
        "spacing": {
            "md": "24px",
            "lg": "32px"
        },
        "borders": {
            "radius_md": "0px"
        },
        "css_overrides": """
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
    },
    {
        "theme_id": "pro_modern",
        "name": "Pro Modern",
        "description": "High-end corporate style with sidebar",
        "palette_name": "Pro Modern",
        "typography": {
            "font_heading": "Outfit",
            "font_body": "Inter",
            "font_size_title": "48px",
            "font_size_heading": "32px",
            "font_size_body": "18px"
        },
        "spacing": {
            "md": "24px",
            "lg": "32px"
        },
        "borders": {
            "radius_md": "12px"
        },
        "css_overrides": """
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
    }
]


async def seed():
    db.init_async_db()
    async with db.AsyncSessionLocal() as session:
        print("Seeding templates...")
        
        # 1. Templates
        for t_data in TEMPLATES:
            # Check if exists
            stmt = select(SlideTemplate).where(SlideTemplate.template_id == t_data["template_id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                template = SlideTemplate(**t_data)
                session.add(template)
                print(f"Created template: {t_data['name']}")
        
        # 2. Palettes
        palette_map = {}
        for p_data in PALETTES:
            stmt = select(ThemePalette).where(ThemePalette.name == p_data["name"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                palette = ThemePalette(**p_data)
                session.add(palette)
                await session.flush() # Get ID
                palette_map[p_data["name"]] = palette.id
                print(f"Created palette: {p_data['name']}")
            else:
                palette_map[p_data["name"]] = existing.id
        
        # 3. Themes (CREATE or UPDATE to ensure css_overrides get applied)
        for th_data in THEMES:
            theme_data = th_data.copy()  # Don't mutate original
            palette_name = theme_data.pop("palette_name")
            palette_id = palette_map.get(palette_name)
            
            stmt = select(ThemeConfig).where(ThemeConfig.theme_id == theme_data["theme_id"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # UPDATE existing theme with new values (especially css_overrides)
                existing.name = theme_data.get("name", existing.name)
                existing.description = theme_data.get("description", existing.description)
                existing.typography = theme_data.get("typography", existing.typography)
                existing.spacing = theme_data.get("spacing", existing.spacing)
                existing.borders = theme_data.get("borders", existing.borders)
                existing.css_overrides = theme_data.get("css_overrides")  # New field!
                if palette_id:
                    existing.palette_id = palette_id
                print(f"Updated theme: {theme_data['name']}")
            else:
                theme = ThemeConfig(palette_id=palette_id, **theme_data)
                session.add(theme)
                print(f"Created theme: {theme_data['name']}")
                
        await session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed())

