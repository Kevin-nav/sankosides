from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class TimelineTemplate(BaseTemplate):
    id = "timeline"
    name = "Timeline"
    description = "Sequential events visualization"
    content_type = "timeline"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Assuming points are chronological steps
        steps_html = ""
        if slide.bullet_points:
             steps_html = '<div class="timeline-steps">'
             for i, point in enumerate(slide.bullet_points):
                 steps_html += f'''
                 <div class="timeline-step">
                    <div class="step-marker">{i+1}</div>
                    <div class="step-content">{point}</div>
                 </div>
                 '''
             steps_html += "</div>"
        
        return f'''
        <div class="slide slide-timeline" data-template="timeline" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="timeline-container">
                {steps_html}
            </div>
        </div>
        '''

class ComparisonTemplate(BaseTemplate):
    id = "comparison"
    name = "Comparison"
    description = "Side-by-side comparison"
    content_type = "comparison"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Assuming even split of points for left/right
        points = slide.bullet_points if slide.bullet_points else []
        mid = len(points) // 2
        left_points = points[:mid]
        right_points = points[mid:]
        
        left_html = "<ul>" + "".join([f"<li>{p}</li>" for p in left_points]) + "</ul>"
        right_html = "<ul>" + "".join([f"<li>{p}</li>" for p in right_points]) + "</ul>"
        
        return f'''
        <div class="slide slide-comparison" data-template="comparison" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="comparison-container">
                <div class="comparison-side left-side">
                    <h3 class="side-header">Option A</h3> <!-- TODO: Dynamic headers -->
                    {left_html}
                </div>
                <div class="comparison-side right-side">
                    <h3 class="side-header">Option B</h3>
                    {right_html}
                </div>
            </div>
        </div>
        '''

class CodeTemplate(BaseTemplate):
    id = "code"
    name = "Code Snippet"
    description = "Syntax highlighted code block"
    content_type = "code"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Code content usually comes from a specific field, but fallback to bullet points join
        code_content = "print('Hello World')"
        if slide.bullet_points:
            code_content = "\n".join(slide.bullet_points)
            
        return f'''
        <div class="slide slide-code" data-template="code" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="code-container">
                <pre><code class="language-python">{code_content}</code></pre>
            </div>
        </div>
        '''
