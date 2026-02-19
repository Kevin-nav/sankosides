from app.export.pdf_exporter import _generate_slide_html
from app.models.schemas import RefinedSlide, SlideContentType
from app.models.slide_elements import SlideElementTree, SlideElement, TextContent, TextRun


def test_pdf_exporter_uses_element_tree_html(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_element_tree_export", True)

    tree = SlideElementTree(
        slide_id="slide-1",
        order=1,
        layout_id="content_bullets",
        elements=[
            SlideElement(
                id="title",
                type="text",
                x=5,
                y=3,
                width=90,
                height=12,
                z_index=1,
                content=TextContent(type="text", runs=[TextRun(text="Element Tree Title", size=44)]),
            )
        ],
    )
    slide = RefinedSlide(
        order=1,
        title="Legacy title",
        content_type=SlideContentType.CONTENT,
        bullet_points=["A"],
        element_tree=tree,
    )

    html = _generate_slide_html(slide, "Deck")
    assert "position:absolute" in html
    assert "Element Tree Title" in html


def test_pdf_exporter_falls_back_to_legacy_html_when_export_flag_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_element_tree_export", False)

    tree = SlideElementTree(
        slide_id="slide-1",
        order=1,
        layout_id="content_bullets",
        elements=[],
    )
    slide = RefinedSlide(
        order=1,
        title="Legacy title",
        content_type=SlideContentType.CONTENT,
        bullet_points=["A"],
        element_tree=tree,
    )

    html = _generate_slide_html(slide, "Deck")
    assert "position:absolute" not in html
    assert "Legacy title" in html
