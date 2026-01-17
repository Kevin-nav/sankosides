from typing import Optional, Dict, Any
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TwoColImageTemplate(BaseTemplate):
    id = "two_col_image"
    name = "Two Column Image"
    description = "Bullet points on the left, image on the right with caption and attribution"
    content_type = "two_col_image"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        figure_number: Optional[int] = None,
        image_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        config = image_config or {}
        caption_format = config.get("caption_format", "Figure {n}: {caption}")
        source_format = config.get("source_format", "Source: {source}")
        
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in slide.bullet_points]) + "</ul>"
            
        image_src = slide.image_url if slide.image_url else "https://via.placeholder.com/600x400?text=Placeholder+Image"
        image_alt = slide.image_alt if slide.image_alt else "Slide image"
        
        # Build caption with figure number
        # Don't display AI-generated placeholder alt text as visible caption
        caption_html = ""
        caption_text = slide.image_caption
        if not caption_text and slide.image_alt:
            # Only use alt text as caption if it's not an AI placeholder
            if not slide.image_alt.lower().startswith("ai-generated"):
                caption_text = slide.image_alt
        
        if caption_text:
            if figure_number:
                formatted_caption = caption_format.format(n=figure_number, caption=caption_text)
            else:
                formatted_caption = caption_text
            caption_html = f'<p class="image-caption">{formatted_caption}</p>'
        
        # Build source attribution
        source_html = ""
        if hasattr(slide, 'image_citation') and slide.image_citation:
            source_text = slide.image_citation.to_citation_string()
            formatted_source = source_format.format(source=source_text)
            source_html = f'<p class="image-source">{formatted_source}</p>'
        
        return f'''
        <div class="slide slide-two-col-image" data-template="two_col_image" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="columns-container">
                <div class="column content-column">
                    {points_html}
                </div>
                <div class="column image-column">
                    <div class="image-wrapper">
                         <img src="{image_src}" alt="{image_alt}" />
                         <div class="image-attribution">
                             {caption_html}
                             {source_html}
                         </div>
                    </div>
                </div>
            </div>
        </div>
        '''

class FullImageTemplate(BaseTemplate):
    id = "full_image"
    name = "Full Screen Image"
    description = "Large hero image with overlay title and attribution"
    content_type = "full_image"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        figure_number: Optional[int] = None,
        image_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        config = image_config or {}
        caption_format = config.get("caption_format", "Figure {n}: {caption}")
        source_format = config.get("source_format", "Source: {source}")
        
        image_src = slide.image_url if slide.image_url else "https://via.placeholder.com/1280x720?text=Hero+Image"
        image_alt = slide.image_alt if slide.image_alt else "Full screen image"
        
        # Build caption with figure number
        caption_html = ""
        caption_text = slide.image_caption or (slide.bullet_points[0] if slide.bullet_points else None)
        if caption_text:
            if figure_number:
                formatted_caption = caption_format.format(n=figure_number, caption=caption_text)
            else:
                formatted_caption = caption_text
            caption_html = f'<p class="image-caption">{formatted_caption}</p>'
        
        # Build source attribution
        source_html = ""
        if hasattr(slide, 'image_citation') and slide.image_citation:
            source_text = slide.image_citation.to_citation_string()
            formatted_source = source_format.format(source=source_text)
            source_html = f'<p class="image-source">{formatted_source}</p>'

        return f'''
        <div class="slide slide-full-image" data-template="full_image" data-slide-id="{slide.order}">
            <div class="background-image-container">
                <img src="{image_src}" alt="{image_alt}" class="hero-image" />
            </div>
            <div class="overlay-content">
                <h2 class="slide-title">{slide.title}</h2>
                <div class="image-attribution">
                    {caption_html}
                    {source_html}
                </div>
            </div>
        </div>
        '''

