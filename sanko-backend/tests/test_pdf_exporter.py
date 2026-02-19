from app.export.pdf_exporter import _generate_slide_html
from app.models.schemas import RefinedSlide, SlideContentType
from app.models.slide_elements import SlideElementTree, SlideElement, TextContent, TextRun


def test_pdf_exporter_uses_element_tree_html():
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
