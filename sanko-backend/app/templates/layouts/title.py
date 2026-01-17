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
        
        author = getattr(slide, 'author', None) or "Presented by Author" 
        current_date = getattr(slide, 'date', None) or date.today().strftime("%B %Y")
        
        # Extra metadata (e.g. for academic slides)
        degree = getattr(slide, 'degree', None)
        supervisor = getattr(slide, 'supervisor', None)
        
        extra_info_html = ""
        if degree:
            extra_info_html += f'<p class="degree-statement">{degree}</p>'
        if supervisor:
            extra_info_html += f'<p class="supervisor-info">Supervised by: {supervisor}</p>'
        
        return f'''
        <div class="slide slide-title" data-template="title" data-slide-id="{slide.order}">
            <div class="title-content">
                <h1 class="main-title">{slide.title}</h1>
                <p class="subtitle">{subtitle}</p>
                <div class="academic-info">
                    {extra_info_html}
                </div>
            </div>
            <div class="title-footer">
                <span class="author">{author}</span>
                <span class="date">{current_date}</span>
            </div>
        </div>
        '''
