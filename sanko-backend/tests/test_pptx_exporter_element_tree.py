import pytest

from app.export.pptx_exporter import percent_to_emu, export_to_pptx, HAS_PPTX
from app.models.schemas import RefinedSlide, SlideContentType
from app.models.slide_elements import SlideElementTree, SlideElement, TextContent, TextRun


def test_percent_to_emu_conversion():
    left, top, width, height = percent_to_emu(10, 10, 50, 50)
    assert left > 0
    assert top > 0
    assert width > left
    assert height > top


def test_export_uses_element_tree_when_present(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_element_tree_export", True)

    if not HAS_PPTX:
        pytest.skip("python-pptx unavailable in this environment")

    tree = SlideElementTree(
        slide_id="slide-1",
        order=1,
        layout_id="content_bullets",
        elements=[
            SlideElement(
                id="title",
                type="text",
                x=5,
                y=5,
                width=90,
                height=12,
                z_index=1,
                content=TextContent(type="text", runs=[TextRun(text="Deck Title", size=40, bold=True)]),
            )
        ],
    )

    slide = RefinedSlide(
        order=1,
        title="Legacy title",
        content_type=SlideContentType.CONTENT,
        bullet_points=["a", "b"],
        element_tree=tree,
    )

    pptx = export_to_pptx([slide], title="Test")
    assert isinstance(pptx, bytes)
    assert len(pptx) > 0
