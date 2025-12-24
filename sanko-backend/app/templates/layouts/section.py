from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class SectionTemplate(BaseTemplate):
    id = "section"
    name = "Section Divider"
    description = "Section title slide"
    content_type = "section"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Assuming there might be a slide number or section number available in future
        # For now just center the title
        return f'''
        <div class="slide slide-section" data-template="section" data-slide-id="{slide.order}">
            <div class="section-content">
                <h1 class="section-title">{slide.title}</h1>
                <div class="section-decoration"></div>
            </div>
        </div>
        '''
