from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TwoColMathTemplate(BaseTemplate):
    id = "two_col_math"
    name = "Two Column Math"
    description = "Text on left, Equation on right"
    content_type = "two_col_math"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        points_html = ""
        if slide.bullet_points:
            points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in slide.bullet_points]) + "</ul>"
            
        if slide.equation_svg:
            math_content = f'<div class="math-svg">{slide.equation_svg}</div>'
        else:
            latex_content = slide.equation_latex if slide.equation_latex else r"E = mc^2"
            math_content = f'<div class="latex-content">$${latex_content}$$</div>'
        
        return f'''
        <div class="slide slide-two-col-math" data-template="two_col_math" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="columns-container">
                <div class="column content-column">
                    {points_html}
                </div>
                <div class="column math-column">
                    <div class="equation-wrapper">
                        <!-- RenderService will target this class -->
                         {math_content}
                    </div>
                </div>
            </div>
        </div>
        '''
