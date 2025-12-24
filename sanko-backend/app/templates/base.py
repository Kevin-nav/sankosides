from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from app.themes import SlideTheme, ColorPalette
from app.routers.generation.models import EnrichedSlide

class BaseTemplate(ABC):
    """Base abstract class for all slide templates."""
    
    id: str = "base"
    name: str = "Base Template"
    description: str = "Abstract base template"
    content_type: str = "generic"
    
    @abstractmethod
    def render(
        self,
        slide: EnrichedSlide,
        theme: SlideTheme,
        colors: Optional[ColorPalette] = None
    ) -> str:
        """
        Render the slide content into HTML.
        
        Args:
            slide: The slide data model
            theme: The structural theme definition
            colors: Optional color palette (overrides theme default)
            
        Returns:
            str: HTML string for the slide
        """
        pass
    
    def get_css(self, theme: SlideTheme, colors: Optional[ColorPalette] = None) -> str:
        """
        Get the CSS variables and styles for this template under the specific theme.
        Defaults to returning the theme's CSS variables.
        Templates can override this to add specific styles.
        """
        palette = colors if colors else theme.colors
        # We might need to create a temporary theme object with the overridden palette to generate CSS
        active_theme = theme
        if colors:
            # Shallow copy and replace colors for CSS generation
            # Note: This depends on how SlideTheme is implemented (Pydantic model)
            active_theme = theme.model_copy(update={"colors": colors})
            
        return active_theme.to_css_variables()
