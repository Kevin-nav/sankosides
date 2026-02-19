from app.core.layout_engine import layout_slide
from app.models.schemas import RefinedSlide, SlideContentType


def test_layout_slide_returns_non_overflowing_elements():
    slide = RefinedSlide(
        order=1,
        title="Title",
        content_type=SlideContentType.CONTENT,
        bullet_points=["A", "B"],
    )
    tree = layout_slide(slide=slide, preset_id="content_bullets")

    assert tree.elements
    for element in tree.elements:
        assert 0 <= element.x <= 100
        assert 0 <= element.y <= 100
        assert element.x + element.width <= 100
        assert element.y + element.height <= 100
