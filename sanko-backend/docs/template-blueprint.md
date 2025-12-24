# Slide Template System Blueprint

This document defines the template architecture for SankoSlides, enabling customizable slide layouts with themed variants.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Template System                              │
├─────────────────────────────────────────────────────────────────┤
│  SlideTheme (colors, fonts)  ──►  SlideLayout (structure)       │
│           ▼                              ▼                       │
│     ColorPalette              TemplateRenderer (HTML output)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Slide Layouts (Content Types)

| Layout ID | Description | Elements |
|-----------|-------------|----------|
| `title` | Opening slide | Title, Subtitle, Author, Date |
| `section` | Section divider | Section title, Number |
| `content` | Standard content | Title, 3-5 bullet points |
| `two_column` | Split layout | Left content, Right content |
| `two_col_image` | Text + Image | Bullets left, Image right |
| `two_col_math` | Text + Equation | Text left, Equation right |
| `full_image` | Hero image | Title, Full-width image, Caption |
| `diagram` | Mermaid diagram | Title, SVG diagram, Caption |
| `quote` | Quotation | Quote text, Author, Source |
| `comparison` | Compare items | Two columns with headers |
| `timeline` | Process steps | Horizontal or vertical flow |
| `code` | Code snippet | Title, Syntax-highlighted code |
| `conclusion` | Closing slide | Key takeaways, Call-to-action |

---

## 2. Layout Template Specification

Each layout is defined as a JSON template:

```json
{
  "id": "two_column",
  "name": "Two Column",
  "description": "Split layout for side-by-side content",
  "regions": [
    {"id": "title", "type": "text", "required": true},
    {"id": "left", "type": "content", "required": true},
    {"id": "right", "type": "content", "required": true}
  ],
  "layout": {
    "display": "grid",
    "grid_template": "1fr 1fr",
    "gap": "var(--spacing-lg)"
  }
}
```

### Region Types

| Type | Description | Renders As |
|------|-------------|------------|
| `text` | Single text element | `<h1>`, `<p>` |
| `content` | Bullet list | `<ul>` with `<li>` |
| `image` | Image with alt | `<img>` |
| `equation` | LaTeX equation | `<div>` with SVG |
| `diagram` | Mermaid diagram | `<div>` with SVG |
| `code` | Code block | `<pre><code>` |
| `quote` | Blockquote | `<blockquote>` |

---

## 3. Theme Variants

### Base Themes (Structural)

```python
THEMES = {
    "academic": {
        "font_heading": "Merriweather",
        "font_body": "Source Sans Pro",
        "border_radius": "small",
        "shadows": "subtle"
    },
    "modern": {
        "font_heading": "Inter",
        "font_body": "Inter", 
        "border_radius": "large",
        "shadows": "medium"
    },
    "minimal": {
        "font_heading": "Inter",
        "font_body": "Inter",
        "border_radius": "none",
        "shadows": "none"
    },
    "playful": {
        "font_heading": "Poppins",
        "font_body": "Nunito",
        "border_radius": "extra-large",
        "shadows": "colorful"
    }
}
```

### Color Palettes (Swappable)

```python
PALETTES = {
    "default": {
        "primary": "#0056A0",
        "secondary": "#FFD700",
        "accent": "#00C853",
        "background": "#FFFFFF",
        "text_primary": "#1A1A1A"
    },
    "ocean": {
        "primary": "#0369A1",
        "secondary": "#0891B2",
        "accent": "#06B6D4",
        "background": "#F0F9FF",
        "text_primary": "#0C4A6E"
    },
    "forest": {
        "primary": "#15803D",
        "secondary": "#65A30D",
        "accent": "#84CC16",
        "background": "#F0FDF4",
        "text_primary": "#14532D"
    },
    "sunset": {
        "primary": "#C2410C",
        "secondary": "#EA580C",
        "accent": "#FB923C",
        "background": "#FFF7ED",
        "text_primary": "#7C2D12"
    },
    "midnight": {
        "primary": "#818CF8",
        "secondary": "#A78BFA",
        "accent": "#C4B5FD",
        "background": "#0F172A",
        "text_primary": "#F8FAFC"
    }
}
```

---

## 4. Template File Structure

```
app/
├── templates/
│   ├── __init__.py          # Template registry
│   ├── base.py               # BaseTemplate class
│   ├── layouts/
│   │   ├── __init__.py
│   │   ├── title.py          # Title slide template
│   │   ├── content.py        # Standard content
│   │   ├── two_column.py     # Two-column layouts
│   │   ├── image.py          # Image-focused layouts
│   │   ├── diagram.py        # Diagram layouts
│   │   ├── quote.py          # Quote layout
│   │   ├── code.py           # Code snippet layout
│   │   └── conclusion.py     # Conclusion layout
│   └── components/
│       ├── bullet_list.py    # Reusable bullet list
│       ├── equation.py       # Equation component
│       ├── citation.py       # Citation footer
│       └── image.py          # Image with caption
└── themes.py                  # Existing themes + palettes
```

---

## 5. Base Template Class

```python
class BaseTemplate:
    """Base class for all slide templates."""
    
    id: str
    name: str
    description: str
    content_type: str
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: ColorPalette
    ) -> str:
        """Render slide to HTML."""
        raise NotImplementedError
    
    def get_css(self, theme: SlideTheme, colors: ColorPalette) -> str:
        """Get CSS styles for this template."""
        raise NotImplementedError
```

---

## 6. Example: Title Template

```python
class TitleTemplate(BaseTemplate):
    id = "title"
    name = "Title Slide"
    content_type = "title"
    
    def render(self, slide, theme, colors):
        return f'''
        <div class="slide slide-title" data-id="slide-{slide.order}">
            <div class="title-content">
                <h1 data-id="title-{slide.order}">{slide.title}</h1>
                <p class="subtitle" data-id="subtitle-{slide.order}">
                    {slide.bullet_points[0] if slide.bullet_points else ""}
                </p>
            </div>
            <div class="title-footer">
                <span class="author">Presented by Author</span>
                <span class="date">{date.today().strftime("%B %Y")}</span>
            </div>
        </div>
        '''
```

---

## 7. Template Selection Logic

```python
def select_template(content_type: str, slide_data: dict) -> BaseTemplate:
    """Select the best template for a slide."""
    
    # Map content types to templates
    TEMPLATE_MAP = {
        "title": TitleTemplate,
        "content": ContentTemplate,
        "section": SectionTemplate,
        "conclusion": ConclusionTemplate,
    }
    
    # Check for special content that needs specific layouts
    if slide_data.get("equation_latex"):
        return TwoColMathTemplate()
    if slide_data.get("image_url"):
        return TwoColImageTemplate()
    if slide_data.get("diagram_mermaid"):
        return DiagramTemplate()
    
    return TEMPLATE_MAP.get(content_type, ContentTemplate)()
```

---

## 8. Variant Generation

To create many variants, combine:

| Dimension | Options | Count |
|-----------|---------|-------|
| Layout | 13 layouts | 13 |
| Theme | 4 base themes | 4 |
| Palette | 5 color palettes | 5 |
| **Total Combinations** | | **260** |

### Variant Naming Convention

```
{layout}_{theme}_{palette}

Examples:
- content_modern_ocean
- title_academic_default
- two_column_minimal_sunset
```

---

## 9. Implementation Roadmap

### Phase 1: Core Templates (Priority)
- [x] Title slide
- [x] Content (bullets)
- [ ] Section divider
- [ ] Two-column
- [ ] Conclusion

### Phase 2: Rich Content
- [ ] Two-column + image
- [ ] Two-column + equation
- [ ] Diagram layout
- [ ] Quote layout

### Phase 3: Special Layouts
- [ ] Timeline
- [ ] Comparison
- [ ] Code snippet

### Phase 4: UI Integration
- [ ] Template preview in playground
- [ ] Theme picker with live preview
- [ ] Custom color palette editor

---

## 10. CSS Architecture

### CSS Variables (from Theme)

```css
:root {
  /* Layout */
  --slide-width: 1280px;
  --slide-height: 720px;
  
  /* Typography */
  --font-heading: 'Inter', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-size-title: 48px;
  --font-size-body: 18px;
  
  /* Spacing */
  --spacing-xs: 8px;
  --spacing-sm: 16px;
  --spacing-md: 24px;
  --spacing-lg: 32px;
  
  /* Colors (from Palette) */
  --color-primary: #6366F1;
  --color-secondary: #EC4899;
  --color-background: #FFFFFF;
  --color-text: #0F172A;
}
```

### Component Classes

```css
/* Base slide */
.slide { width: var(--slide-width); height: var(--slide-height); }

/* Layout variants */
.slide-title { justify-content: center; text-align: center; }
.slide-content { padding: var(--spacing-lg); }
.slide-two-col { display: grid; grid-template-columns: 1fr 1fr; }

/* Components */
.bullet-list { /* ... */ }
.equation-container { /* ... */ }
.image-container { /* ... */ }
```
