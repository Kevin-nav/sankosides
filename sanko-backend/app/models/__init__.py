# Models Package

# Export all Pydantic schemas for easy import
from app.models.schemas import (
    # Core models
    OrderForm,
    Skeleton,
    SkeletonSlide,
    SlideContentType,
    
    # Planner output
    PlannedContent,
    PlannedSlide,
    
    # Refiner output
    RefinedContent,
    RefinedSlide,
    CitationMetadata,
    
    # Generator output
    GeneratedPresentation,
    GeneratedSlide,
    
    # QA models
    QAResult,
    QAReport,
)
from app.models.slide_elements import (
    ElementType,
    TextRun,
    TextContent,
    ImageContent,
    EquationContent,
    DiagramContent,
    ShapeContent,
    ChartContent,
    ElementStyle,
    LayoutConstraint,
    SlideElement,
    SlideElementTree,
    BackgroundConfig,
)

# Backwards compatibility aliases for templates
# They use EnrichedSlide which maps to RefinedSlide
EnrichedSlide = RefinedSlide
EnrichedContent = RefinedContent

__all__ = [
    # Core
    "OrderForm",
    "Skeleton",
    "SkeletonSlide",
    "SlideContentType",
    
    # Planner
    "PlannedContent",
    "PlannedSlide",
    
    # Refiner
    "RefinedContent",
    "RefinedSlide",
    "CitationMetadata",
    
    # Generator
    "GeneratedPresentation",
    "GeneratedSlide",
    
    # QA
    "QAResult",
    "QAReport",
    # Slide element tree
    "ElementType",
    "TextRun",
    "TextContent",
    "ImageContent",
    "EquationContent",
    "DiagramContent",
    "ShapeContent",
    "ChartContent",
    "ElementStyle",
    "LayoutConstraint",
    "SlideElement",
    "SlideElementTree",
    "BackgroundConfig",
    
    # Backwards compatibility
    "EnrichedSlide",
    "EnrichedContent",
]
