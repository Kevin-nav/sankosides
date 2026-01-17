from typing import Optional, Dict, Any
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide


class ThankYouTemplate(BaseTemplate):
    """Template for rendering the Thank You closing slide."""
    
    id = "thank_you"
    name = "Thank You"
    description = "Simple thank you closing slide"
    content_type = "thank_you"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render the Thank You slide.
        
        Args:
            slide: The slide data model
            theme: The structural theme definition
            colors: Optional color palette
            config: Optional config dict with:
                - custom_message: str
                - show_logo: bool
                - show_presenter_name: bool
                - presenter_name: str
                - logo_url: str
        """
        config = config or {}
        message = config.get("custom_message", "Thank You")
        show_logo = config.get("show_logo", True)
        show_name = config.get("show_presenter_name", False)
        presenter_name = config.get("presenter_name", "")
        logo_url = config.get("logo_url")
        
        logo_html = ""
        if show_logo and logo_url:
            logo_html = f'<img class="thank-you-logo" src="{logo_url}" alt="Logo">'
        
        name_html = ""
        if show_name and presenter_name:
            name_html = f'<p class="presenter-name">{presenter_name}</p>'
        
        return f'''
        <div class="slide slide-thank-you" data-template="thank_you" data-slide-id="{slide.order}">
            <div class="thank-you-content">
                {logo_html}
                <h1 class="thank-you-message">{message}</h1>
                {name_html}
            </div>
        </div>
        '''
