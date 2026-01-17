"""
Figure numbering service for presentations.

Assigns sequential figure numbers to slides with images across a presentation.
Supports customizable prefixes (Figure, Fig., Diagram, etc.).
"""

from typing import List, Dict, Optional
from app.models.schemas import RefinedSlide


class FigureNumberingService:
    """
    Assigns sequential figure numbers across a presentation.
    
    Supports:
    - Simple sequential: Figure 1, Figure 2
    - Custom prefixes: Fig. 1, Diagram 1
    """
    
    def __init__(self, prefix: str = "Figure"):
        self.prefix = prefix
        self.counter = 0
        self.assignments: Dict[int, int] = {}  # slide_order -> figure_number
    
    def assign_numbers(self, slides: List[RefinedSlide]) -> Dict[int, int]:
        """
        Assign figure numbers to slides that have images.
        
        Args:
            slides: List of RefinedSlide objects
            
        Returns:
            Dict mapping slide order to figure number
        """
        self.counter = 0
        self.assignments = {}
        
        for slide in slides:
            if slide.image_url:
                self.counter += 1
                self.assignments[slide.order] = self.counter
        
        return self.assignments
    
    def get_figure_number(self, slide_order: int) -> Optional[int]:
        """Get the figure number for a given slide order."""
        return self.assignments.get(slide_order)
    
    def get_caption(
        self,
        slide_order: int,
        caption_text: str,
        format_template: str = "Figure {n}: {caption}"
    ) -> str:
        """
        Generate formatted caption for a slide.
        
        Args:
            slide_order: The slide's order number
            caption_text: Raw caption text
            format_template: Template with {n} and {caption} placeholders
            
        Returns:
            Formatted caption string
        """
        figure_num = self.assignments.get(slide_order, slide_order)
        
        return format_template.format(
            n=figure_num,
            caption=caption_text,
            prefix=self.prefix
        )
    
    def get_source_attribution(
        self,
        source_text: str,
        format_template: str = "Source: {source}"
    ) -> str:
        """
        Generate formatted source attribution.
        
        Args:
            source_text: The source citation text
            format_template: Template with {source} placeholder
            
        Returns:
            Formatted source attribution string
        """
        return format_template.format(source=source_text)
    
    def get_total_figures(self) -> int:
        """Get the total number of figures in the presentation."""
        return self.counter
