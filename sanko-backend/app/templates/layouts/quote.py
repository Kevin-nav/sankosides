from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class QuoteTemplate(BaseTemplate):
    id = "quote"
    name = "Quote"
    description = "Large quote with attribution"
    content_type = "quote"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        # Assuming the quote is the first bullet point or distinct field?
        # Blueprint says "Quote text, Author, Source"
        # Since EnrichedSlide is generic, let's assume raw text or first point is quote, second is author.
        quote_text = "Quote text goes here."
        author_text = "Unknown"
        
        if slide.bullet_points:
            quote_text = slide.bullet_points[0]
            if len(slide.bullet_points) > 1:
                author_text = slide.bullet_points[1]
            
        return f'''
        <div class="slide slide-quote" data-template="quote" data-slide-id="{slide.order}">
            <div class="quote-content">
                <blockquote class="main-quote">
                    "{quote_text}"
                </blockquote>
                <div class="quote-attribution">
                    <span class="quote-author">— {author_text}</span>
                </div>
            </div>
        </div>
        '''
