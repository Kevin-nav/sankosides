import pytest
from app.templates.layouts import TitleTemplate, ContentTemplate, TwoColumnTemplate
from app.themes import MODERN_THEME
from app.routers.generation.models import EnrichedSlide, CitationMetadata

# Mock slide data
@pytest.fixture
def slide_data():
    return EnrichedSlide(
        order=1,
        title="Test Slide",
        bullet_points=["Point 1", "Point 2", "Point 3"],
        content_type="content"
    )

def test_title_template_render(slide_data):
    template = TitleTemplate()
    html = template.render(slide_data, MODERN_THEME)
    
    assert "class=\"slide slide-title\"" in html
    assert "Test Slide" in html
    assert "Point 1" in html  # Subtitle
    assert "Presented by Author" in html

def test_content_template_render(slide_data):
    template = ContentTemplate()
    html = template.render(slide_data, MODERN_THEME)
    
    assert "class=\"slide slide-content\"" in html
    assert "<li>Point 1</li>" in html
    assert "<li>Point 2</li>" in html
    assert "<li>Point 3</li>" in html

def test_two_column_template_render(slide_data):
    template = TwoColumnTemplate()
    html = template.render(slide_data, MODERN_THEME)
    
    assert "class=\"slide slide-two-column\"" in html
    assert "left-column" in html
    assert "right-column" in html
    assert "<li>Point 1</li>" in html
    # Point 2 should be in left (ceil(3/2)=2) or right? logic: mid=2, left=[0,1], right=[2]
    # Verify split logic roughly by existence
    assert "<li>Point 3</li>" in html

def test_template_css_generation():
    template = TitleTemplate()
    css = template.get_css(MODERN_THEME)
    
    assert ":root {" in css
    assert "--slide-width: 1280px" in css
    assert "--slide-height: 720px" in css
    assert "--font-heading: 'Inter'" in css
    assert "--color-primary: #6366F1" in css

def test_image_template_render(slide_data):
    # EnrichedSlide with image data
    slide = slide_data.model_copy(update={"image_url": "http://test.com/img.jpg", "content_type": "two_col_image"})
    from app.templates.layouts import TwoColImageTemplate
    template = TwoColImageTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "class=\"slide slide-two-col-image\"" in html
    assert "src=\"http://test.com/img.jpg\"" in html
    assert "image-column" in html

def test_math_template_render(slide_data):
    slide = slide_data.model_copy(update={"equation_latex": "a^2+b^2=c^2", "content_type": "two_col_math"})
    from app.templates.layouts import TwoColMathTemplate
    template = TwoColMathTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "class=\"slide slide-two-col-math\"" in html
    assert "a^2+b^2=c^2" in html
    assert "latex-content" in html

def test_diagram_template_render(slide_data):
    slide = slide_data.model_copy(update={"diagram_mermaid": "graph TD; A-->B", "content_type": "diagram"})
    from app.templates.layouts import DiagramTemplate
    template = DiagramTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "class=\"slide slide-diagram\"" in html
    assert "graph TD; A-->B" in html
    assert "mermaid" in html

def test_math_template_svg_precedence(slide_data):
    # Test that SVG is used if provided
    slide = slide_data.model_copy(update={
        "equation_latex": "a^2+b^2=c^2", 
        "equation_svg": "<svg>math</svg>",
        "content_type": "two_col_math"
    })
    from app.templates.layouts import TwoColMathTemplate
    template = TwoColMathTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "math-svg" in html
    assert "<svg>math</svg>" in html
    assert "latex-content" not in html

def test_diagram_template_svg_precedence(slide_data):
    # Test that SVG is used if provided
    slide = slide_data.model_copy(update={
        "diagram_mermaid": "graph TD", 
        "diagram_svg": "<svg>diagram</svg>",
        "content_type": "diagram"
    })
    from app.templates.layouts import DiagramTemplate
    template = DiagramTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "diagram-svg" in html
    assert "<svg>diagram</svg>" in html
    assert "mermaid" not in html

def test_image_template_caption(slide_data):
    slide = slide_data.model_copy(update={
        "image_url": "http://img.com/1.jpg", 
        "image_caption": "My Caption",
        "content_type": "two_col_image"
    })
    from app.templates.layouts import TwoColImageTemplate
    template = TwoColImageTemplate()
    html = template.render(slide, MODERN_THEME)
    
    assert "image-caption" in html
    assert "My Caption" in html
