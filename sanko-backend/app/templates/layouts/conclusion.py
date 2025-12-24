from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class ConclusionTemplate(BaseTemplate):
    id = "conclusion"
    name = "Conclusion"
    description = "Closing slide with key takeaways"
    content_type = "conclusion"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in slide.bullet_points]) + "</ul>"
            
        return f'''
        <div class="slide slide-conclusion" data-template="conclusion" data-slide-id="{slide.order}">
            <div class="conclusion-header">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="takeaways-region">
                {points_html}
            </div>
            <div class="conclusion-footer">
                <p>Thank You</p>
            </div>
        </div>
        '''
