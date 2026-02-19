import asyncio
from types import SimpleNamespace

import pytest

from app.models.schemas import GeneratedPresentation, GeneratedSlide
from app.models.slide_elements import SlideElementTree, SlideElement, TextContent, TextRun


def _sample_tree() -> SlideElementTree:
    return SlideElementTree(
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
                content=TextContent(type="text", runs=[TextRun(text="Edited", size=40)]),
            )
        ],
    )


def test_patch_element_tree_updates_slide(monkeypatch):
    try:
        from app.api.routers import generation as generation_router
    except ModuleNotFoundError:
        pytest.skip("API router dependencies unavailable in this environment")

    slide = GeneratedSlide(
        order=1,
        title="Slide 1",
        theme_id="modern",
        rendered_html="<html><body>old</body></html>",
    )
    presentation = GeneratedPresentation(
        title="Deck",
        theme_id="modern",
        slides=[slide],
        total_slides=1,
    )
    state = SimpleNamespace(
        status=generation_router.FlowStatus.COMPLETED,
        generated_presentation=presentation,
        project_id=None,
        order_form=SimpleNamespace(theme_id="modern"),
    )

    monkeypatch.setattr(generation_router, "get_session", lambda _session_id: state)
    monkeypatch.setattr(generation_router, "save_session", lambda _state: None)

    request = generation_router.PatchElementTreeRequest(
        slide_order=1,
        element_tree=_sample_tree(),
        regenerate_html=False,
    )

    result = asyncio.run(generation_router.patch_element_tree("session-1", request))

    assert result.slide_order == 1
    assert slide.element_tree is not None
    assert slide.element_tree.layout_id == "content_bullets"


def test_patch_element_tree_regenerated_html_is_sanitized(monkeypatch):
    try:
        from app.api.routers import generation as generation_router
    except ModuleNotFoundError:
        pytest.skip("API router dependencies unavailable in this environment")

    slide = GeneratedSlide(
        order=1,
        title="Slide 1",
        theme_id="modern",
        rendered_html="<html><body>old</body></html>",
    )
    presentation = GeneratedPresentation(
        title="Deck",
        theme_id="modern",
        slides=[slide],
        total_slides=1,
    )
    state = SimpleNamespace(
        status=generation_router.FlowStatus.COMPLETED,
        generated_presentation=presentation,
        project_id=None,
        order_form=SimpleNamespace(theme_id="modern"),
    )

    monkeypatch.setattr(generation_router, "get_session", lambda _session_id: state)
    monkeypatch.setattr(generation_router, "save_session", lambda _state: None)

    import app.templates.html_generator as html_generator

    monkeypatch.setattr(
        html_generator,
        "element_tree_to_html",
        lambda **_kwargs: "<html><body><script>alert('x')</script><div onclick=\"evil()\">safe</div></body></html>",
    )

    request = generation_router.PatchElementTreeRequest(
        slide_order=1,
        element_tree=_sample_tree(),
        regenerate_html=True,
    )

    result = asyncio.run(generation_router.patch_element_tree("session-1", request))
    rendered = result.slide["rendered_html"].lower()

    assert "<script" not in rendered
    assert "onclick" not in rendered
    assert "safe" in rendered
