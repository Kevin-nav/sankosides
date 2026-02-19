import pytest
from pydantic import ValidationError

from app.models.slide_elements import SlideElement, SlideElementTree, TextContent, TextRun


def test_slide_element_accepts_percentage_bounds():
    element = SlideElement(
        id="el-1",
        type="text",
        x=5.0,
        y=10.0,
        width=40.0,
        height=20.0,
        z_index=1,
        content=TextContent(type="text", runs=[TextRun(text="hello", size=24)]),
    )
    assert element.x == 5.0


def test_slide_element_rejects_out_of_bounds_percentage():
    with pytest.raises(ValidationError):
        SlideElement(
            id="el-2",
            type="text",
            x=101.0,
            y=10.0,
            width=40.0,
            height=20.0,
            z_index=1,
            content=TextContent(type="text", runs=[TextRun(text="bad", size=24)]),
        )


def test_slide_element_tree_serializes():
    element = SlideElement(
        id="el-1",
        type="text",
        x=5.0,
        y=10.0,
        width=40.0,
        height=20.0,
        z_index=1,
        content=TextContent(type="text", runs=[TextRun(text="hello", size=24)]),
    )
    tree = SlideElementTree(
        slide_id="slide-1",
        order=1,
        layout_id="content_bullets",
        elements=[element],
    )

    payload = tree.model_dump()
    assert payload["slide_id"] == "slide-1"
    assert len(payload["elements"]) == 1
