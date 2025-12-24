from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TwoColImageTemplate(BaseTemplate):
    id = "two_col_image"
    name = "Two Column Image"
    description = "Bullet points on the left, image on the right"
    content_type = "two_col_image"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in slide.bullet_points]) + "</ul>"
            
        image_src = slide.image_url if slide.image_url else "https://via.placeholder.com/600x400?text=Placeholder+Image"
        image_alt = slide.image_alt if slide.image_alt else "Slide image"
        
        caption_html = ""
        if slide.image_caption:
             caption_html = f'<p class="image-caption">{slide.image_caption}</p>'
        
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
                         {caption_html}
                    </div>
                </div>
            </div>
        </div>
        '''

class FullImageTemplate(BaseTemplate):
    id = "full_image"
    name = "Full Screen Image"
    description = "Large hero image with overlay title"
    content_type = "full_image"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        image_src = slide.image_url if slide.image_url else "https://via.placeholder.com/1280x720?text=Hero+Image"
        image_alt = slide.image_alt if slide.image_alt else "Full screen image"
        
        caption_html = ""
        if slide.image_caption:
            caption_html = f'<p class="image-caption">{slide.image_caption}</p>'
        elif slide.bullet_points:
             caption_html = f'<p class="image-caption">{slide.bullet_points[0]}</p>'

        return f'''
        <div class="slide slide-full-image" data-template="full_image" data-slide-id="{slide.order}">
            <div class="background-image-container">
                <img src="{image_src}" alt="{image_alt}" class="hero-image" />
            </div>
            <div class="overlay-content">
                <h2 class="slide-title">{slide.title}</h2>
                {caption_html}
            </div>
        </div>
        '''
