from typing import Optional
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide


class ReferencesTemplate(BaseTemplate):
    """Template for rendering the References slide with formatted citations."""
    
    id = "references"
    name = "References"
    description = "Bibliography/References slide"
    content_type = "references"
    
    def render(self, slide: EnrichedSlide, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        """Render the References slide with formatted citations."""
        refs_html = ""
        if slide.formatted_citations:
            # Check if IEEE style (numbered) based on citation_style from order_form
            is_numbered = self._is_numbered(slide)
            list_tag = "ol" if is_numbered else "ul"
            refs_html = f"<{list_tag} class='references-list'>"
            for citation in slide.formatted_citations:
                refs_html += f"<li>{citation}</li>"
            refs_html += f"</{list_tag}>"
        
        return f'''
        <div class="slide slide-references" data-template="references" data-slide-id="{slide.order}">
            <div class="header-region">
                <h2 class="slide-title">{slide.title}</h2>
            </div>
            <div class="references-region">
                {refs_html}
            </div>
        </div>
        '''
    
    def _is_numbered(self, slide: EnrichedSlide) -> bool:
        """Check if IEEE style (numbered) - info should come from order_form."""
        # Default to False (bulleted for Harvard/APA)
        # In Phase 2, this will check citation_style from order_form
        return False
