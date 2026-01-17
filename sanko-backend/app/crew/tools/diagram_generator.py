"""
AI Diagram Generator

Generates diagrams using AI when Mermaid rendering fails.
Optimizes prompts for specific diagram types (quadrant, xy, sankey, etc.)
"""

from typing import Optional
from app.crew.tools.image_generation_tool import NanoBananaImageTool
from app.core.logging import get_logger

logger = get_logger(__name__)


# Type-specific prompt templates for better diagram generation
DIAGRAM_PROMPTS = {
    "quadrantchart": """A 2x2 quadrant matrix diagram:
- Four equal quadrants with clear dividing lines
- Axes labeled clearly at the edges
- Data points or labels positioned in appropriate quadrants
- Clean, minimal design with good contrast""",
    
    "xychart": """A clean XY chart/graph:
- Clear X and Y axis with labeled tick marks
- Data points or line connecting data
- Grid lines in background
- Legend if multiple series
- Professional chart styling""",
    
    "sankey": """A Sankey flow diagram:
- Flowing bands connecting sources to destinations
- Width of bands proportional to flow values
- Clear labels on nodes
- Smooth curves for the flow paths
- Color-coded flows for clarity""",
    
    "pie": """A pie chart:
- Clear wedges with distinct colors
- Percentage labels on or near each wedge
- Legend with category names
- Clean, professional styling""",
    
    "gantt": """A Gantt chart:
- Horizontal bars representing tasks
- Timeline along the top or bottom
- Task names on the left
- Clear start and end dates
- Color-coded by category or status""",
    
    "mindmap": """A mind map diagram:
- Central topic in the middle
- Branches radiating outward
- Sub-branches for child topics
- Color-coded branches
- Clear, readable text on each node""",
    
    "timeline": """A timeline diagram:
- Horizontal or vertical line
- Events marked with points and labels
- Dates clearly indicated
- Consistent spacing
- Clean, minimal design""",
    
    "flowchart": """A flowchart diagram:
- Rectangular boxes for processes
- Diamond shapes for decisions
- Arrows connecting elements
- Clear flow direction (top-to-bottom or left-to-right)
- Consistent styling""",
    
    "sequence": """A sequence diagram:
- Vertical lifelines for participants
- Horizontal arrows for messages
- Activation boxes on lifelines
- Clear labels on arrows
- Proper ordering of events""",
    
    "class": """A class diagram:
- Rectangular boxes for classes
- Class name at top, methods below
- Arrows showing relationships (inheritance, composition)
- Clear relationship labels
- UML-style notation""",
    
    "default": """A professional diagram:
- Clean, minimal design
- Clear labels and annotations
- Good use of whitespace
- Professional color scheme
- Easy to understand at a glance"""
}


def _detect_diagram_type(mermaid_code: str) -> str:
    """Detect diagram type from Mermaid code."""
    code_lower = mermaid_code.lower().strip()
    
    type_mapping = {
        "quadrantchart": "quadrantchart",
        "xychart": "xychart",
        "sankey": "sankey",
        "pie": "pie",
        "gantt": "gantt",
        "mindmap": "mindmap",
        "timeline": "timeline",
        "flowchart": "flowchart",
        "graph": "flowchart",
        "sequencediagram": "sequence",
        "classdiagram": "class",
        "statediagram": "flowchart",
        "erdiagram": "class",
    }
    
    for keyword, diagram_type in type_mapping.items():
        if code_lower.startswith(keyword):
            return diagram_type
    
    return "default"


def _extract_diagram_content(mermaid_code: str) -> str:
    """Extract meaningful content from Mermaid code for prompt."""
    # Remove Mermaid keywords and syntax, keep labels and descriptions
    lines = mermaid_code.split('\n')
    content_parts = []
    
    for line in lines:
        # Skip empty lines and pure syntax
        line = line.strip()
        if not line or line.startswith('%%'):
            continue
        
        # Extract quoted text (usually labels)
        import re
        quotes = re.findall(r'["\']([^"\']+)["\']', line)
        content_parts.extend(quotes)
        
        # Extract text in brackets (node labels)
        brackets = re.findall(r'\[([^\]]+)\]', line)
        content_parts.extend(brackets)
        
        # Extract text in parentheses  
        parens = re.findall(r'\(([^)]+)\)', line)
        content_parts.extend(parens)
    
    return ', '.join(content_parts[:20])  # Limit to avoid prompt bloat


async def generate_diagram_with_ai(
    mermaid_code: str,
    description: Optional[str] = None,
    upload_to_r2: bool = True,
) -> Optional[str]:
    """
    Generate a diagram image using AI when Mermaid rendering fails.
    
    Args:
        mermaid_code: Original Mermaid code (used to understand intent)
        description: Optional human description of the diagram
        upload_to_r2: Whether to upload to R2 storage
        
    Returns:
        Image URL if successful, None if failed
    """
    # Detect diagram type
    diagram_type = _detect_diagram_type(mermaid_code)
    logger.info(f"[DIAGRAM_GEN] Generating {diagram_type} diagram with AI")
    
    # Build optimized prompt
    type_prompt = DIAGRAM_PROMPTS.get(diagram_type, DIAGRAM_PROMPTS["default"])
    
    # Extract content from Mermaid code
    content_hints = _extract_diagram_content(mermaid_code)
    
    # User description takes priority if provided
    content_description = description or content_hints or "the specified content"
    
    full_prompt = f"""Create a professional diagram for an academic presentation:

TYPE: {type_prompt}

CONTENT TO VISUALIZE: {content_description}

STYLE REQUIREMENTS:
- Colors: Use blue (#2563EB), gray (#64748B), white (#FFFFFF) background
- All text must be clearly readable
- Clean, professional appearance
- Suitable for academic/business presentation
- No decorative elements, focus on clarity
- White or very light background"""
    
    try:
        tool = NanoBananaImageTool()
        result = await tool.generate_asset(
            prompt=full_prompt,
            style="professional diagram, clean design, minimal, academic",
            upload_to_r2=upload_to_r2,
        )
        
        if result.success:
            logger.info(f"[DIAGRAM_GEN] Successfully generated {diagram_type} diagram")
            return result.file_path
        else:
            logger.error(f"[DIAGRAM_GEN] Failed: {result.error}")
            return None
            
    except Exception as e:
        logger.error(f"[DIAGRAM_GEN] Exception: {e}")
        return None


async def render_diagram_with_fallback(
    mermaid_code: str,
    render_tool,
    description: Optional[str] = None,
) -> tuple[Optional[str], str]:
    """
    Render Mermaid diagram with AI fallback.
    
    Args:
        mermaid_code: Mermaid diagram code
        render_tool: RenderServiceTool instance
        description: Optional description for AI fallback
        
    Returns:
        Tuple of (svg_or_image_url, source)
        source is "mermaid" or "ai"
    """
    # Try Mermaid first
    try:
        result = render_tool._run(action="mermaid", content=mermaid_code)
        if result and not result.startswith("Error"):
            return result, "mermaid"
    except Exception as e:
        logger.warning(f"[DIAGRAM] Mermaid render failed: {e}")
    
    # Fallback to AI generation
    logger.info("[DIAGRAM] Falling back to AI generation")
    image_url = await generate_diagram_with_ai(mermaid_code, description)
    
    if image_url:
        return image_url, "ai"
    
    return None, "failed"
