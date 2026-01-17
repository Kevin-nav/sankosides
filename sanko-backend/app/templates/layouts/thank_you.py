from typing import Optional, Dict, Any
from app.templates.base import BaseTemplate
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide


class ThankYouTemplate(BaseTemplate):
    """Template for rendering the Thank You closing slide with author info."""
    
    id = "thank_you"
    name = "Thank You"
    description = "Professional thank you slide with author info and contact"
    content_type = "thank_you"
    
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render the Thank You slide with author information.
        
        Args:
            slide: The slide data model (may have author, email, date attributes)
            theme: The structural theme definition
            colors: Optional color palette
            config: Optional config dict with:
                - custom_message: str (default: "Thank You")
                - show_questions: bool (default: True)
                - show_contact: bool (default: True)
                - presenter_name: str
                - presenter_email: str
                - date: str
                - logo_url: str
        """
        config = config or {}
        
        # Get message
        message = config.get("custom_message", "Thank You")
        
        # Get author info from slide attributes or config
        presenter_name = (
            getattr(slide, 'author', None) or 
            config.get("presenter_name", "")
        )
        presenter_email = (
            getattr(slide, 'email', None) or 
            config.get("presenter_email", "")
        )
        date_str = (
            getattr(slide, 'date', None) or 
            config.get("date", "")
        )
        
        # Options
        show_questions = config.get("show_questions", True)
        show_contact = config.get("show_contact", True)
        logo_url = config.get("logo_url")
        
        # Build HTML parts
        logo_html = ""
        if logo_url:
            logo_html = f'<img class="thank-you-logo" src="{logo_url}" alt="Logo">'
        
        author_html = ""
        if presenter_name:
            author_html = f'<p class="presenter-name">{presenter_name}</p>'
        
        email_html = ""
        if show_contact and presenter_email:
            email_html = f'<p class="presenter-email">{presenter_email}</p>'
        
        date_html = ""
        if date_str:
            date_html = f'<p class="presentation-date">{date_str}</p>'
        
        questions_html = ""
        if show_questions:
            questions_html = '<p class="questions-prompt">Questions?</p>'
        
        # Combine info block
        info_parts = [p for p in [author_html, email_html, date_html] if p]
        info_block = f'<div class="author-info">{"".join(info_parts)}</div>' if info_parts else ""
        
        return f'''
        <div class="slide slide-thank-you" data-template="thank_you" data-slide-id="{slide.order}">
            <div class="thank-you-content">
                {logo_html}
                <h1 class="thank-you-message">{message}</h1>
                {info_block}
                {questions_html}
            </div>
        </div>
        '''
