"""
PDF Exporter

Generates PDF files from slides using the render service.
Leverages existing HTML rendering and MathJax for high-fidelity output.
"""

from typing import List, Optional
from app.models.schemas import RefinedSlide
from app.core.logging import get_logger
from app.core.config import settings
from app.templates.html_generator import element_tree_to_html
from app.themes import get_theme

logger = get_logger(__name__)


async def export_to_pdf(
    slides: List[RefinedSlide],
    title: str = "Presentation",
    format: str = "16:9",
    include_notes: bool = False,
) -> bytes:
    """
    Export slides to PDF format.
    
    Uses the render service to generate a high-fidelity PDF from
    HTML slides with MathJax-rendered equations and embedded diagrams.
    
    Args:
        slides: List of RefinedSlide objects
        title: Presentation title
        format: Page format (16:9, 4:3, A4, Letter)
        include_notes: Whether to include speaker notes
        
    Returns:
        PDF file as bytes
        
    Raises:
        RuntimeError: If PDF generation fails
    """
    from app.export.render_client import get_render_client

    render_client = get_render_client()
    
    # Generate HTML for each slide
    slides_html = []
    for slide in slides:
        html = _generate_slide_html(slide, title)
        slides_html.append(html)
    
    logger.info(f"Generating PDF for {len(slides)} slides")
    
    # Call render service to generate PDF
    pdf_bytes, error = await render_client.html_to_pdf(
        slides_html=slides_html,
        format=format,
    )
    
    if pdf_bytes is None:
        raise RuntimeError(f"PDF generation failed: {error}")
    
    logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
    return pdf_bytes


def _generate_slide_html(slide: RefinedSlide, title: str) -> str:
    """
    Generate HTML content for a single slide.
    
    This is a simplified version - in production, would use
    the full template system with proper styling.
    """
    if settings.enable_element_tree_export and getattr(slide, "element_tree", None) is not None:
        return element_tree_to_html(tree=slide.element_tree, theme=get_theme("modern"))

    # Base styles for slides
    styles = """
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 40px 60px;
            background: white;
            color: #1a1a2e;
            height: 100%;
            box-sizing: border-box;
        }
        .slide-title {
            font-size: 36px;
            font-weight: 700;
            color: #2d4059;
            margin-bottom: 30px;
            border-bottom: 3px solid #ea5455;
            padding-bottom: 15px;
        }
        .content {
            font-size: 22px;
            line-height: 1.6;
        }
        .bullet-list {
            list-style: none;
            padding: 0;
            margin: 20px 0;
        }
        .bullet-list li {
            padding: 12px 0;
            padding-left: 30px;
            position: relative;
        }
        .bullet-list li::before {
            content: "●";
            position: absolute;
            left: 0;
            color: #ea5455;
            font-size: 14px;
        }
        .equation-container {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 12px;
            margin: 25px 0;
            font-size: 28px;
        }
        .diagram-container {
            text-align: center;
            padding: 20px;
            margin: 25px 0;
        }
        .diagram-container img {
            max-width: 100%;
            max-height: 400px;
        }
        .title-slide {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            text-align: center;
        }
        .title-slide .slide-title {
            font-size: 52px;
            border: none;
        }
        .title-slide .subtitle {
            font-size: 28px;
            color: #6b7280;
            margin-top: 20px;
        }
    """
    
    # MathJax script for equations
    mathjax_script = """
        <script>
            window.MathJax = {
                tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] },
                svg: { fontCache: 'global' }
            };
        </script>
        <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    """
    
    # Build content based on slide type
    from app.models.schemas import SlideContentType
    
    if slide.content_type == SlideContentType.TITLE:
        content = f"""
            <div class="title-slide">
                <h1 class="slide-title">{_escape_html(slide.title)}</h1>
                {f'<p class="subtitle">{_escape_html(slide.bullet_points[0])}</p>' if slide.bullet_points else ''}
            </div>
        """
    else:
        # Build content sections
        sections = []
        
        # Bullet points
        if slide.bullet_points:
            bullets = "".join(f"<li>{_escape_html(bp)}</li>" for bp in slide.bullet_points)
            sections.append(f'<ul class="bullet-list">{bullets}</ul>')
        
        # Equation (render inline with MathJax)
        if slide.equation_latex:
            latex = slide.equation_latex.replace('\\', '\\\\')
            sections.append(f'<div class="equation-container">$${latex}$$</div>')
        
        # Diagram (use SVG if available)
        if slide.diagram_svg:
            sections.append(f'<div class="diagram-container">{slide.diagram_svg}</div>')
        
        content = f"""
            <h1 class="slide-title">{_escape_html(slide.title)}</h1>
            <div class="content">
                {"".join(sections)}
            </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{styles}</style>
    {mathjax_script}
</head>
<body>
    {content}
</body>
</html>
    """


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
