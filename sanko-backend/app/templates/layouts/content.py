from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class ContentTemplate(BaseTemplate):
    id = "content"
    name = "Standard Content"
    description = "Title with bullet points"
    content_type = "content"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in slide.bullet_points]) + "</ul>"
            
        return f'''
        <div class="slide slide-content" data-template="content" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="content-region">
                {points_html}
            </div>
        </div>
        '''
