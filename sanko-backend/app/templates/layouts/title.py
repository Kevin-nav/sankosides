from datetime import date
from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TitleTemplate(BaseTemplate):
    id = "title"
    name = "Title Slide"
    description = "Opening slide with title, subtitle, and author info"
    content_type = "title"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        subtitle = slide.bullet_points[0] if slide.bullet_points else ""
        # TODO: Retrieve author from somewhere if available, otherwise generic or empty
        author_text = "Presented by Author" 
        current_date = date.today().strftime("%B %Y")
        
        return f'''
        <div class="slide slide-title" data-template="title" data-slide-id="{slide.order}">
            <div class="title-content">
                <h1 class="main-title">{slide.title}</h1>
                <p class="subtitle">{subtitle}</p>
            </div>
            <div class="title-footer">
                <span class="author">{author_text}</span>
                <span class="date">{current_date}</span>
            </div>
        </div>
        '''
