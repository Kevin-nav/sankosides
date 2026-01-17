# Phase 1: Core Slide Types

## Overview
Add `REFERENCES` and `THANK_YOU` slide types to the SankoSlides system with database templates and auto-generation logic.

---

## 1.1 Add New Slide Types to Schema

### File: `sanko-backend/app/models/schemas.py`

Add to `SlideContentType` enum:
```python
class SlideContentType(str, Enum):
    # ...existing types...
    REFERENCES = "references"   # Dedicated references slide
    THANK_YOU = "thank_you"     # Simple thank you slide
```

---

## 1.2 Add Thank You Slide Configuration

### File: `sanko-backend/app/core/university_configs/base.py`

Add to `FormattingRules`:
```python
class ThankYouConfig(BaseModel):
    """Configuration for Thank You slide elements."""
    show_logo: bool = Field(default=True, description="Show university logo")
    show_presenter_name: bool = Field(default=False, description="Show presenter name if provided")
    custom_message: Optional[str] = Field(default=None, description="Custom message instead of 'Thank You'")

class FormattingRules(BaseModel):
    # ...existing fields...
    thank_you: ThankYouConfig = Field(default_factory=ThankYouConfig)
```

---

## 1.3 Add Database Migration

### File: `sanko-backend/alembic/versions/xxx_add_university_to_templates.py`

```python
"""Add university_id to slide_templates"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'slide_templates',
        sa.Column('university_id', sa.String(50), nullable=True)
    )
    op.create_index(
        'ix_slide_templates_university_id',
        'slide_templates',
        ['university_id']
    )

def downgrade():
    op.drop_index('ix_slide_templates_university_id', 'slide_templates')
    op.drop_column('slide_templates', 'university_id')
```

---

## 1.4 Create Template Layouts

### File: `sanko-backend/app/templates/layouts/references.py`

```python
from typing import Optional, List
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class ReferencesTemplate(BaseTemplate):
    id = "references"
    name = "References"
    description = "Bibliography/References slide"
    content_type = "references"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # formatted_citations contains pre-formatted HTML strings
        refs_html = ""
        if slide.formatted_citations:
            refs_html = "<ol class='references-list'>" if self._is_numbered(slide) else "<ul class='references-list'>"
            for citation in slide.formatted_citations:
                refs_html += f"<li>{citation}</li>"
            refs_html += "</ol>" if self._is_numbered(slide) else "</ul>"
        
        return f'''
        <div class="slide slide-references" data-template="references" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="references-region">
                {refs_html}
            </div>
        </div>
        '''
    
    def _is_numbered(self, slide: EnrichedSlide) -> bool:
        # Check if IEEE style (numbered) - this info should come from order_form
        # For now, default to False (bulleted)
        return False
```

### File: `sanko-backend/app/templates/layouts/thank_you.py`

```python
from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette, UniversityBranding
from app.routers.generation.models import EnrichedSlide

class ThankYouTemplate(BaseTemplate):
    id = "thank_you"
    name = "Thank You"
    description = "Simple thank you closing slide"
    content_type = "thank_you"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        branding: Optional[UniversityBranding] = None,
        config: Optional[dict] = None,
    ) -> str:
        # Config contains thank_you settings
        config = config or {}
        message = config.get("custom_message", "Thank You")
        show_logo = config.get("show_logo", True)
        show_name = config.get("show_presenter_name", False)
        presenter_name = config.get("presenter_name", "")
        logo_url = branding.university_badge_url if branding else None
        
        logo_html = ""
        if show_logo and logo_url:
            logo_html = f'<img class="thank-you-logo" src="{logo_url}" alt="Logo">'
        
        name_html = ""
        if show_name and presenter_name:
            name_html = f'<p class="presenter-name">{presenter_name}</p>'
        
        return f'''
        <div class="slide slide-thank-you" data-template="thank_you" data-slide-id="{slide.order}">
            <div class="thank-you-content">
                {logo_html}
                <h1 class="thank-you-message">{message}</h1>
                {name_html}
            </div>
        </div>
        '''
```

---

## 1.5 Register Templates

### File: `sanko-backend/app/templates/__init__.py`

Add to imports and registry:
```python
from app.templates.layouts.references import ReferencesTemplate
from app.templates.layouts.thank_you import ThankYouTemplate

TEMPLATE_REGISTRY: Dict[str, Type[BaseTemplate]] = {
    # ...existing...
    "references": ReferencesTemplate,
    "thank_you": ThankYouTemplate,
}
```

---

## 1.6 Auto-Generate References Slide

### File: `sanko-backend/app/crew/flows/slide_generation.py`

Add method to `SlideGenerationFlow`:
```python
def _generate_references_slide(
    self,
    all_slides: List[RefinedSlide],
    citation_style: str,
    order: int,
) -> RefinedSlide:
    """
    Auto-generate a References slide from all citations in the presentation.
    
    Args:
        all_slides: All content slides with their citations
        citation_style: Style for formatting (harvard, apa, ieee, chicago)
        order: Slide order number for the References slide
        
    Returns:
        RefinedSlide with formatted citations
    """
    from app.models.schemas import RefinedSlide, SlideContentType, CitationMetadata
    
    # Collect all unique citations across slides
    seen_ids = set()
    all_citations: List[CitationMetadata] = []
    
    for slide in all_slides:
        for citation in slide.citations:
            # Use DOI or title+year as unique identifier
            citation_id = citation.doi or f"{citation.title}_{citation.year}"
            if citation_id not in seen_ids:
                seen_ids.add(citation_id)
                all_citations.append(citation)
    
    # Sort alphabetically by first author surname (for Harvard/APA)
    # Or keep in order of appearance (for IEEE)
    if citation_style.lower() in ["harvard", "apa", "chicago"]:
        all_citations.sort(key=lambda c: (c.authors[0] if c.authors else "ZZZ", c.year))
    # IEEE keeps order of appearance (already in order)
    
    # Format citations (will be done by render service in Phase 2)
    # For now, use simple formatting
    formatted = []
    for i, c in enumerate(all_citations, 1):
        author_str = c.authors[0] if c.authors else "Unknown"
        if len(c.authors) > 1:
            author_str += " et al."
        formatted.append(f"{author_str} ({c.year}). <em>{c.title}</em>.")
    
    return RefinedSlide(
        order=order,
        title="References",
        content_type=SlideContentType.REFERENCES,
        bullet_points=[],
        citations=all_citations,
        formatted_citations=formatted,
        template_type="references",
    )
```

---

## 1.7 Auto-Generate Thank You Slide

Add method to `SlideGenerationFlow`:
```python
def _generate_thank_you_slide(
    self,
    order: int,
    config: Optional[ThankYouConfig] = None,
) -> RefinedSlide:
    """
    Generate a Thank You slide.
    
    Args:
        order: Slide order number
        config: Thank You configuration
        
    Returns:
        RefinedSlide for Thank You
    """
    from app.models.schemas import RefinedSlide, SlideContentType
    
    return RefinedSlide(
        order=order,
        title="Thank You",
        content_type=SlideContentType.THANK_YOU,
        bullet_points=[],
        citations=[],
        formatted_citations=[],
        template_type="thank_you",
    )
```

---

## 1.8 Integrate Into Pipeline

Modify the generator step in `slide_generation.py` to append these slides:

```python
async def _run_generator(self, ...):
    # ... existing generation logic ...
    
    # After all content slides are generated:
    total_content_slides = len(generated_slides)
    
    # Auto-generate References slide
    references_slide = self._generate_references_slide(
        all_slides=self.state.refined_content.slides,
        citation_style=self.state.order_form.citation_style,
        order=total_content_slides + 1,
    )
    # Render HTML for references slide
    references_html = await self._render_slide(references_slide, ...)
    generated_slides.append(GeneratedSlide(
        order=references_slide.order,
        title="References",
        theme_id=theme_id,
        rendered_html=references_html,
    ))
    
    # Auto-generate Thank You slide
    thank_you_slide = self._generate_thank_you_slide(
        order=total_content_slides + 2,
        config=self.state.university_context.university.formatting_rules.thank_you if self.state.university_context else None,
    )
    # Render HTML for thank you slide
    thank_you_html = await self._render_slide(thank_you_slide, ...)
    generated_slides.append(GeneratedSlide(
        order=thank_you_slide.order,
        title="Thank You",
        theme_id=theme_id,
        rendered_html=thank_you_html,
    ))
```

---

## 1.9 Seed Database Templates

### File: `sanko-backend/scripts/seed_templates.py`

Add template seeds:
```python
REFERENCES_TEMPLATE = {
    "template_id": "references",
    "name": "References Slide",
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
    text-indent: -var(--spacing-md);
}
.references-list li em {
    font-style: italic;
}
""",
}

THANK_YOU_TEMPLATE = {
    "template_id": "thank_you",
    "name": "Thank You Slide",
    "content_type": "thank_you",
    "html_template": """
<div class="slide slide-thank-you" data-template="thank_you" data-slide-id="{{ slide.order }}">
    <div class="thank-you-content">
        <h1 class="thank-you-message">Thank You</h1>
    </div>
</div>
""",
    "css_styles": """
.slide-thank-you {
    display: flex;
    justify-content: center;
    align-items: center;
}
.thank-you-content {
    text-align: center;
}
.thank-you-message {
    font-size: var(--font-size-title);
    font-weight: var(--font-weight-title);
    color: var(--color-primary);
}
.thank-you-logo {
    max-height: 80px;
    margin-bottom: var(--spacing-lg);
}
.presenter-name {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
    margin-top: var(--spacing-md);
}
""",
}
```

---

## 1.10 Testing Checklist

- [ ] `SlideContentType.REFERENCES` and `THANK_YOU` added to enum
- [ ] Database migration runs successfully
- [ ] Templates registered in `TEMPLATE_REGISTRY`
- [ ] References slide auto-generates with all citations
- [ ] Thank You slide renders correctly
- [ ] Both slides export correctly to PPTX/PDF
- [ ] Templates render from database
- [ ] University-specific templates work with `university_id` filter

---

## Files Modified

| File | Changes |
|------|---------|
| `app/models/schemas.py` | Add `REFERENCES`, `THANK_YOU` to enum |
| `app/core/university_configs/base.py` | Add `ThankYouConfig` |
| `app/templates/layouts/references.py` | NEW - References template |
| `app/templates/layouts/thank_you.py` | NEW - Thank You template |
| `app/templates/__init__.py` | Register new templates |
| `app/crew/flows/slide_generation.py` | Add auto-generation methods |
| `scripts/seed_templates.py` | Add template seeds |
| `alembic/versions/xxx.py` | NEW - Migration for university_id |
