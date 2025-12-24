from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class DiagramTemplate(BaseTemplate):
    id = "diagram"
    name = "Diagram Slide"
    description = "Mermaid diagram visualization"
    content_type = "diagram"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        caption_html = ""
        if slide.bullet_points:
             caption_html = f'<div class="diagram-caption"><p>{slide.bullet_points[0]}</p></div>'
            
        if slide.diagram_svg:
            diagram_content = f'<div class="diagram-svg">{slide.diagram_svg}</div>'
        else:
            mermaid_code = slide.diagram_mermaid if slide.diagram_mermaid else "graph TD; A-->B;"
            diagram_content = f'<div class="mermaid">{mermaid_code}</div>'
        
        return f'''
        <div class="slide slide-diagram" data-template="diagram" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="diagram-container">
                {diagram_content}
                {caption_html}
            </div>
        </div>
        '''
