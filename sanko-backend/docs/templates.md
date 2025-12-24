# Template System

Documentation for the HTML slide template system.

## Table of Contents

- [Overview](#overview)
- [Template Types](#template-types)
- [Base Template Class](#base-template-class)
- [Layout Templates](#layout-templates)
- [Theme Integration](#theme-integration)
- [Custom Template Development](#custom-template-development)

---

## Overview

SankoSlides uses a template system to convert structured content into semantic HTML slides. Each template:

- Extends a base class
- Renders specific slide types
- Integrates with themes via CSS variables
- Produces accessible, responsive HTML

```
RefinedSlide
     │
     ▼
┌─────────────────┐
│ Template Select │◄── Based on content_type + assets
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Template.render │◄── Applies layout + theme
└─────────────────┘
     │
     ▼
   HTML Slide
```

---

## Template Types

| Template | File | Use Case |
|----------|------|----------|
| **Title** | `title.py` | Opening slide |
| **Content** | `content.py` | Standard bullet points |
| **Section** | `section.py` | Section dividers |
| **Two Column** | `two_column.py` | Side-by-side comparison |
| **Image** | `image.py` | Image-focused slides |
| **Diagram** | `diagram.py` | Mermaid diagrams |
| **Math** | `math.py` | LaTeX equations |
| **Quote** | `quote.py` | Quote highlights |
| **Conclusion** | `conclusion.py` | Summary slides |
| **Special** | `special.py` | Timeline, code, comparison |

---

## Base Template Class

All templates extend `BaseTemplate`:

```python
# app/templates/base.py

from abc import ABC, abstractmethod
from app.models import RefinedSlide

class BaseTemplate(ABC):
    """Base class for all slide templates."""
    
    name: str = "base"
    
    @abstractmethod
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        """Render the slide to HTML."""
        pass
    
    def wrap_slide(
        self, 
        content: str, 
        slide: RefinedSlide, 
        theme_id: str
    ) -> str:
        """Wrap content in slide container."""
        return f'''
<div class="slide slide-{slide.order}" 
     data-template="{self.name}"
     data-theme="{theme_id}">
    <div class="slide-header">
        <h1 class="slide-title">{self._escape(slide.title)}</h1>
    </div>
    <div class="slide-content">
        {content}
    </div>
</div>
'''
    
    def _escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )
    
    def _render_bullets(self, points: List[str]) -> str:
        """Render bullet points as HTML list."""
        items = "".join(f"<li>{self._escape(p)}</li>" for p in points)
        return f"<ul class='bullet-list'>{items}</ul>"
```

---

## Layout Templates

### Title Template

**File:** `app/templates/layouts/title.py`

```python
class TitleTemplate(BaseTemplate):
    name = "title"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        subtitle = slide.bullet_points[0] if slide.bullet_points else ""
        
        content = f'''
<div class="title-content">
    <h1 class="presentation-title">{self._escape(slide.title)}</h1>
    {f'<p class="subtitle">{self._escape(subtitle)}</p>' if subtitle else ''}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

**Output:**
```html
<div class="slide slide-1" data-template="title" data-theme="modern">
    <div class="slide-header">
        <h1 class="slide-title">Introduction to Machine Learning</h1>
    </div>
    <div class="slide-content">
        <div class="title-content">
            <h1 class="presentation-title">Introduction to Machine Learning</h1>
            <p class="subtitle">CS 301 - Fall 2025</p>
        </div>
    </div>
</div>
```

---

### Content Template

**File:** `app/templates/layouts/content.py`

Standard bullet point layout with optional citations.

```python
class ContentTemplate(BaseTemplate):
    name = "content"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        bullets = self._render_bullets(slide.bullet_points)
        
        citations = ""
        if slide.formatted_citations:
            citation_items = "".join(
                f"<li class='citation'>{c}</li>" 
                for c in slide.formatted_citations
            )
            citations = f"<ul class='citations'>{citation_items}</ul>"
        
        content = f'''
<div class="content-body">
    {bullets}
</div>
{citations}
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Two Column Template

**File:** `app/templates/layouts/two_column.py`

Side-by-side comparison layout.

```python
class TwoColumnTemplate(BaseTemplate):
    name = "two_column"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        # Split bullets into two columns
        mid = len(slide.bullet_points) // 2
        left_points = slide.bullet_points[:mid]
        right_points = slide.bullet_points[mid:]
        
        content = f'''
<div class="two-column-layout">
    <div class="column column-left">
        {self._render_bullets(left_points)}
    </div>
    <div class="column column-right">
        {self._render_bullets(right_points)}
    </div>
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Diagram Template

**File:** `app/templates/layouts/diagram.py`

For slides with Mermaid diagrams.

```python
class DiagramTemplate(BaseTemplate):
    name = "diagram"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        diagram = ""
        if slide.diagram_svg:
            diagram = f'''
<div class="diagram-container">
    {slide.diagram_svg}
</div>
'''
        
        bullets = self._render_bullets(slide.bullet_points) if slide.bullet_points else ""
        
        content = f'''
<div class="diagram-layout">
    {diagram}
    {bullets}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Math Template

**File:** `app/templates/layouts/math.py`

For slides with LaTeX equations.

```python
class MathTemplate(BaseTemplate):
    name = "math"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        equation = ""
        if slide.equation_svg:
            equation = f'''
<div class="equation-container">
    <div class="equation">
        {slide.equation_svg}
    </div>
    {f'<p class="equation-caption">{slide.equation_latex}</p>' if slide.equation_latex else ''}
</div>
'''
        
        bullets = self._render_bullets(slide.bullet_points) if slide.bullet_points else ""
        
        content = f'''
<div class="math-layout">
    {equation}
    {bullets}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Image Template

**File:** `app/templates/layouts/image.py`

For image-focused slides.

```python
class ImageTemplate(BaseTemplate):
    name = "image"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        image = ""
        if slide.image_url:
            image = f'''
<figure class="image-container">
    <img src="{slide.image_url}" 
         alt="{self._escape(slide.image_alt or slide.title)}"
         class="slide-image">
    {f'<figcaption>{self._escape(slide.image_caption)}</figcaption>' if slide.image_caption else ''}
</figure>
'''
        
        bullets = self._render_bullets(slide.bullet_points) if slide.bullet_points else ""
        
        content = f'''
<div class="image-layout">
    {image}
    {bullets}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Quote Template

**File:** `app/templates/layouts/quote.py`

For highlighting quotes or key statements.

```python
class QuoteTemplate(BaseTemplate):
    name = "quote"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        quote_text = slide.bullet_points[0] if slide.bullet_points else ""
        attribution = slide.bullet_points[1] if len(slide.bullet_points) > 1 else ""
        
        content = f'''
<blockquote class="featured-quote">
    <p class="quote-text">"{self._escape(quote_text)}"</p>
    {f'<cite class="quote-attribution">— {self._escape(attribution)}</cite>' if attribution else ''}
</blockquote>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

### Conclusion Template

**File:** `app/templates/layouts/conclusion.py`

Summary/takeaway slide.

```python
class ConclusionTemplate(BaseTemplate):
    name = "conclusion"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        content = f'''
<div class="conclusion-content">
    <h2 class="conclusion-heading">Key Takeaways</h2>
    {self._render_bullets(slide.bullet_points)}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

---

## Theme Integration

### CSS Variables

Each theme defines CSS variables that templates use:

```css
/* Theme: Academic */
[data-theme="academic"] {
    --slide-bg: #ffffff;
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a6a;
    --accent-color: #2d4059;
    --accent-secondary: #ea5455;
    --font-heading: 'Merriweather', serif;
    --font-body: 'Source Sans Pro', sans-serif;
    --spacing-unit: 1.5rem;
}

/* Theme: Modern */
[data-theme="modern"] {
    --slide-bg: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --text-primary: #ffffff;
    --text-secondary: rgba(255, 255, 255, 0.8);
    --accent-color: #f093fb;
    --font-heading: 'Inter', sans-serif;
    --font-body: 'Inter', sans-serif;
}

/* Theme: Dark */
[data-theme="dark"] {
    --slide-bg: #0f0f23;
    --text-primary: #cccccc;
    --text-secondary: #888888;
    --accent-color: #00d4ff;
    --font-heading: 'JetBrains Mono', monospace;
    --font-body: 'Inter', sans-serif;
}
```

### Using Variables in Templates

```css
.slide-title {
    color: var(--text-primary);
    font-family: var(--font-heading);
    font-size: 2.5rem;
    margin-bottom: var(--spacing-unit);
}

.bullet-list li {
    color: var(--text-secondary);
    font-family: var(--font-body);
    margin-bottom: calc(var(--spacing-unit) * 0.5);
}

.accent-text {
    color: var(--accent-color);
}
```

---

## Template Selection Logic

The Generator uses this logic to select templates:

```python
# app/templates/__init__.py

from app.templates.layouts import (
    TitleTemplate,
    ContentTemplate,
    SectionTemplate,
    TwoColumnTemplate,
    ImageTemplate,
    DiagramTemplate,
    MathTemplate,
    QuoteTemplate,
    ConclusionTemplate,
)

TEMPLATES = {
    "title": TitleTemplate(),
    "content": ContentTemplate(),
    "section": SectionTemplate(),
    "two_column": TwoColumnTemplate(),
    "image": ImageTemplate(),
    "diagram": DiagramTemplate(),
    "math": MathTemplate(),
    "quote": QuoteTemplate(),
    "conclusion": ConclusionTemplate(),
}

def select_template_for_slide(slide: RefinedSlide) -> BaseTemplate:
    """Select the appropriate template based on slide content."""
    
    # Check for special content first
    if slide.diagram_svg:
        return TEMPLATES["diagram"]
    
    if slide.equation_svg:
        return TEMPLATES["math"]
    
    if slide.image_url:
        return TEMPLATES["image"]
    
    # Then check content type
    if slide.template_type and slide.template_type in TEMPLATES:
        return TEMPLATES[slide.template_type]
    
    # Map content_type to template
    type_mapping = {
        SlideContentType.TITLE: "title",
        SlideContentType.CONCLUSION: "conclusion",
        SlideContentType.SECTION: "section",
        SlideContentType.TWO_COLUMN: "two_column",
        SlideContentType.QUOTE: "quote",
    }
    
    template_name = type_mapping.get(slide.content_type, "content")
    return TEMPLATES[template_name]
```

---

## Custom Template Development

### Creating a New Template

1. **Create template file:**

```python
# app/templates/layouts/timeline.py

from app.templates.base import BaseTemplate
from app.models import RefinedSlide

class TimelineTemplate(BaseTemplate):
    name = "timeline"
    
    def render(self, slide: RefinedSlide, theme_id: str = "modern") -> str:
        # Each bullet point is a timeline event
        events = ""
        for i, point in enumerate(slide.bullet_points):
            events += f'''
<div class="timeline-event">
    <div class="timeline-marker">{i + 1}</div>
    <div class="timeline-content">
        <p>{self._escape(point)}</p>
    </div>
</div>
'''
        
        content = f'''
<div class="timeline-container">
    <div class="timeline-line"></div>
    {events}
</div>
'''
        return self.wrap_slide(content, slide, theme_id)
```

2. **Add to template registry:**

```python
# app/templates/__init__.py

from app.templates.layouts.timeline import TimelineTemplate

TEMPLATES = {
    # ... existing templates
    "timeline": TimelineTemplate(),
}
```

3. **Add CSS styles:**

```css
/* Timeline styles */
.timeline-container {
    position: relative;
    padding-left: 2rem;
}

.timeline-line {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--accent-color);
}

.timeline-event {
    display: flex;
    margin-bottom: var(--spacing-unit);
}

.timeline-marker {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    background: var(--accent-color);
    color: var(--slide-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}

.timeline-content {
    margin-left: 1rem;
}
```

### Template Best Practices

1. **Semantic HTML**: Use proper heading hierarchy, lists, figures
2. **Accessibility**: Include alt text, ARIA labels where needed
3. **Responsive**: Use relative units and flexible layouts
4. **Theme-Aware**: Use CSS variables, not hardcoded colors
5. **Escape Input**: Always escape user content to prevent XSS
6. **Minimal Complexity**: Let CSS handle styling, keep HTML simple
