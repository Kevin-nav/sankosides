from typing import Optional
import math
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TwoColumnTemplate(BaseTemplate):
    id = "two_column"
    name = "Two Column"
    description = "Split layout for side-by-side content"
    content_type = "two_column"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Split buttet points into two columns
        points = slide.bullet_points if slide.bullet_points else []
        mid = math.ceil(len(points) / 2)
        left_points = points[:mid]
        right_points = points[mid:]
        
        left_html = "<ul>" + "".join([f"<li>{p}</li>" for p in left_points]) + "</ul>" if left_points else ""
        right_html = "<ul>" + "".join([f"<li>{p}</li>" for p in right_points]) + "</ul>" if right_points else ""
        
        return f'''
        <div class="slide slide-two-column" data-template="two_column" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="columns-container">
                <div class="column left-column">
                    {left_html}
                </div>
                <div class="column right-column">
                    {right_html}
                </div>
            </div>
        </div>
        '''
