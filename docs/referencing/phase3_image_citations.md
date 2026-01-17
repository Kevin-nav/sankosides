# Phase 3: Image Citations & Captions

## Overview
Implement image attribution system with configurable caption formats, source citations, and figure numbering.

---

## 3.1 Image Citation Configuration

### File: `sanko-backend/app/core/university_configs/base.py`

Add `ImageConfig` to `FormattingRules`:
```python
class ImageConfig(BaseModel):
    """Configuration for image captions and attributions."""
    
    # Caption format
    caption_format: str = Field(
        default="Figure {n}: {caption}",
        description="Template for image captions. {n}=number, {caption}=description"
    )
    
    # Source attribution format
    source_format: str = Field(
        default="Source: {source}",
        description="Template for source attribution. {source}=citation or URL"
    )
    
    # Where to show attribution
    attribution_position: Literal["below_caption", "slide_footer"] = Field(
        default="below_caption",
        description="Where to display source attribution"
    )
    
    # Include images in References slide
    include_in_references: bool = Field(
        default=True,
        description="Whether to include image sources in References slide"
    )
    
    # Numbering style
    numbering_prefix: str = Field(
        default="Figure",
        description="Prefix for figure numbering (Figure, Fig., Diagram, etc.)"
    )


class FormattingRules(BaseModel):
    # ...existing fields...
    images: ImageConfig = Field(default_factory=ImageConfig)
```

---

## 3.2 Image Citation Metadata

### File: `sanko-backend/app/models/schemas.py`

Add `ImageCitation` model:
```python
class ImageCitation(BaseModel):
    """Citation metadata specifically for images."""
    source_type: Literal["original", "adapted", "screenshot", "generated", "stock", "creative_commons"] = Field(
        default="original",
        description="Type of image source"
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Where the image came from (e.g., 'NASA', 'Author's own')"
    )
    creator: Optional[str] = Field(
        default=None,
        description="Original creator/photographer"
    )
    year: Optional[str] = Field(default=None)
    license: Optional[str] = Field(
        default=None,
        description="License type (CC BY 4.0, Public Domain, etc.)"
    )
    url: Optional[str] = Field(default=None)
    adapted_from: Optional[str] = Field(
        default=None,
        description="If adapted, original source citation"
    )
    
    def to_citation_string(self, style: str = "harvard") -> str:
        """Generate formatted citation string."""
        if self.source_type == "original":
            return "Author's own work"
        elif self.source_type == "generated":
            return "AI-generated image"
        elif self.source_type == "adapted":
            return f"Adapted from {self.adapted_from}" if self.adapted_from else "Adapted"
        else:
            parts = []
            if self.creator:
                parts.append(self.creator)
            if self.year:
                parts.append(f"({self.year})")
            if self.source_name:
                parts.append(self.source_name)
            if self.license:
                parts.append(f"[{self.license}]")
            return " ".join(parts) if parts else "Unknown source"


class RefinedSlide(BaseModel):
    # ...existing fields...
    
    # Image citation (NEW)
    image_citation: Optional[ImageCitation] = Field(
        default=None,
        description="Citation/attribution for the slide's image"
    )
```

---

## 3.3 Figure Numbering Service

### File: `sanko-backend/app/services/figure_numbering.py`

```python
"""Figure numbering service for presentations."""

from typing import List, Dict, Tuple
from app.models.schemas import RefinedSlide


class FigureNumberingService:
    """
    Assigns sequential figure numbers across a presentation.
    
    Supports:
    - Simple sequential: Figure 1, Figure 2
    - Custom prefixes: Fig. 1, Diagram 1
    """
    
    def __init__(self, prefix: str = "Figure"):
        self.prefix = prefix
        self.counter = 0
        self.assignments: Dict[int, int] = {}  # slide_order -> figure_number
    
    def assign_numbers(self, slides: List[RefinedSlide]) -> Dict[int, int]:
        """
        Assign figure numbers to slides that have images.
        
        Returns:
            Dict mapping slide order to figure number
        """
        self.counter = 0
        self.assignments = {}
        
        for slide in slides:
            if slide.image_url:
                self.counter += 1
                self.assignments[slide.order] = self.counter
        
        return self.assignments
    
    def get_caption(
        self,
        slide_order: int,
        caption_text: str,
        format_template: str = "Figure {n}: {caption}"
    ) -> str:
        """
        Generate formatted caption for a slide.
        
        Args:
            slide_order: The slide's order number
            caption_text: Raw caption text
            format_template: Template with {n} and {caption} placeholders
            
        Returns:
            Formatted caption string
        """
        figure_num = self.assignments.get(slide_order, slide_order)
        
        return format_template.format(
            n=figure_num,
            caption=caption_text,
            prefix=self.prefix
        )
    
    def get_source_attribution(
        self,
        source_text: str,
        format_template: str = "Source: {source}"
    ) -> str:
        """Generate formatted source attribution."""
        return format_template.format(source=source_text)
```

---

## 3.4 Update Image Template

### File: `sanko-backend/app/templates/layouts/image.py`

```python
from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide


class TwoColImageTemplate(BaseTemplate):
    id = "two_col_image"
    name = "Two Column with Image"
    description = "Content on left, image on right with caption"
    content_type = "two_col_image"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        figure_number: Optional[int] = None,
        image_config: Optional[dict] = None,
    ) -> str:
        config = image_config or {}
        caption_format = config.get("caption_format", "Figure {n}: {caption}")
        source_format = config.get("source_format", "Source: {source}")
        
        # Build caption
        caption_html = ""
        if slide.image_alt or slide.image_caption:
            caption_text = slide.image_caption or slide.image_alt
            if figure_number:
                formatted_caption = caption_format.format(
                    n=figure_number,
                    caption=caption_text
                )
            else:
                formatted_caption = caption_text
            caption_html = f'<p class="image-caption">{formatted_caption}</p>'
        
        # Build source attribution
        source_html = ""
        if hasattr(slide, 'image_citation') and slide.image_citation:
            source_text = slide.image_citation.to_citation_string()
            formatted_source = source_format.format(source=source_text)
            source_html = f'<p class="image-source">{formatted_source}</p>'
        
        # Content bullets
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{p}</li>" for p in slide.bullet_points]) + "</ul>"
        
        return f'''
        <div class="slide slide-two-col-image" data-template="two_col_image" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="columns-container">
                <div class="column text-column">
                    {points_html}
                </div>
                <div class="column image-column">
                    <img src="{slide.image_url}" alt="{slide.image_alt or ''}">
                    <div class="image-attribution">
                        {caption_html}
                        {source_html}
                    </div>
                </div>
            </div>
        </div>
        '''
```

---

## 3.5 CSS for Image Attribution

### File: `sanko-backend/scripts/seed_templates.py`

Add CSS to image template:
```python
IMAGE_TEMPLATE_CSS = """
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
    font-size: var(--font-size-caption);
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
```

---

## 3.6 Include Image Citations in References

### File: `sanko-backend/app/crew/flows/slide_generation.py`

Update `_generate_references_slide`:
```python
async def _generate_references_slide(
    self,
    all_slides: List[RefinedSlide],
    citation_style: str,
    order: int,
    include_images: bool = True,
) -> RefinedSlide:
    """Generate References slide with text and image citations."""
    
    # Collect text citations
    text_citations = []
    seen_ids = set()
    for slide in all_slides:
        for citation in slide.citations:
            cid = citation.doi or f"{citation.title}_{citation.year}"
            if cid not in seen_ids:
                seen_ids.add(cid)
                text_citations.append(citation)
    
    # Collect image citations if configured
    image_citations = []
    if include_images:
        figure_num = 0
        for slide in all_slides:
            if slide.image_url and slide.image_citation:
                figure_num += 1
                # Don't include "Author's own work" or "AI-generated"
                if slide.image_citation.source_type not in ["original", "generated"]:
                    img_cit = {
                        "figure_number": figure_num,
                        "caption": slide.image_caption or slide.image_alt or "",
                        "citation": slide.image_citation.to_citation_string(),
                    }
                    image_citations.append(img_cit)
    
    # Format text citations via render service
    formatted_text = await self._format_citations_via_service(text_citations, citation_style)
    
    # Format image citations (simple format)
    formatted_images = []
    for img in image_citations:
        formatted_images.append(
            f"Figure {img['figure_number']}: {img['citation']}"
        )
    
    # Combine
    all_formatted = formatted_text
    if formatted_images:
        all_formatted.append("")  # Blank line
        all_formatted.append("<strong>Figure Sources</strong>")
        all_formatted.extend(formatted_images)
    
    return RefinedSlide(
        order=order,
        title="References",
        content_type=SlideContentType.REFERENCES,
        bullet_points=[],
        citations=text_citations,
        formatted_citations=all_formatted,
        template_type="references",
    )
```

---

## 3.7 Agent: Include Image Citation in Refiner

### File: `sanko-backend/app/crew/agents/refiner.py`

Update system prompt to include image attribution:
```python
REFINER_SYSTEM_PROMPT = """...existing content...

### 5. Image Attribution (NEW)
For each slide with an image:
1. Determine the source type:
   - "original" - Author's own photo/diagram
   - "adapted" - Modified from another source
   - "screenshot" - Screenshot from software/website
   - "stock" - Stock photo (include license)
   - "creative_commons" - CC-licensed image
   - "generated" - AI-generated image
   
2. Create ImageCitation with appropriate metadata:
   - source_name: Where from (NASA, Wikipedia, etc.)
   - creator: Original photographer/artist
   - year: When created
   - license: License type if applicable
   - adapted_from: Original source if adapted

3. The caption should describe what the image shows
4. The source attribution will be auto-formatted by the template

DO NOT leave images without attribution. Even if original, mark as "original".
"""
```

---

## 3.8 University-Specific Image Rules

### File: `sanko-backend/scripts/seed_umat.py`

Add UMaT-specific image config:
```python
UMAT_IMAGE_CONFIG = {
    "caption_format": "Figure {n}: {caption}",
    "source_format": "Source: {source}",
    "attribution_position": "below_caption",
    "include_in_references": True,
    "numbering_prefix": "Figure",
}

# UMaT rule: Figure captions go BELOW the image (already default)
# UMaT rule: Table captions go ABOVE the table
```

---

## 3.9 Testing Checklist

- [ ] `ImageCitation` model created
- [ ] `ImageConfig` added to `FormattingRules`
- [ ] Figure numbering service works
- [ ] Image templates show captions correctly
- [ ] Source attribution appears below caption
- [ ] Image citations appear on References slide
- [ ] "Author's own work" doesn't appear in References
- [ ] UMaT caption rules are followed
- [ ] Export includes proper image captions

---

## 3.10 UMaT Complete Configuration

For reference, here's the complete UMaT configuration based on discussion:

```python
UMAT_CONFIG = {
    "university_id": "umat",
    "name": "University of Mines and Technology",
    "short_name": "UMaT",
    "country": "Ghana",
    "default_citation_style": "harvard",
    "spelling_variant": "british",
    "unit_system": "si",
    "primary_color": "#1E3A5F",  # Navy blue
    "secondary_color": "#D4AF37",  # Gold
    "formatting_rules": {
        "figure_caption_position": "below",
        "table_caption_position": "above",
        "reference_placement": "last_slide",
        "acronym_first_use": "spell_out",
        "number_unit_spacing": True,
        "references": {
            "inline_format": "author_year",
            "allow_multiple_citations": True,
            "ordering": "alphabetical",
            "use_numbered_list": False,
        },
        "images": {
            "caption_format": "Figure {n}: {caption}",
            "source_format": "Source: {source}",
            "attribution_position": "below_caption",
            "include_in_references": True,
        },
        "thank_you": {
            "show_logo": True,
            "show_presenter_name": False,
        },
    },
}
```

---

## Files Modified/Created

| File | Changes |
|------|---------|
| `app/core/university_configs/base.py` | Add `ImageConfig` |
| `app/models/schemas.py` | Add `ImageCitation` model |
| `app/services/figure_numbering.py` | NEW - Figure numbering |
| `app/templates/layouts/image.py` | Add caption/attribution |
| `app/crew/agents/refiner.py` | Add image attribution instructions |
| `app/crew/flows/slide_generation.py` | Include images in References |
| `scripts/seed_templates.py` | Image template CSS |
| `scripts/seed_umat.py` | UMaT-specific config |
