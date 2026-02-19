"""Deterministic slide layout engine producing structured element trees."""

from __future__ import annotations

from typing import List, Optional

from app.core.layout_presets import LayoutPreset, get_layout_preset
from app.core.text_fitting import fit_text_to_box
from app.models.schemas import RefinedSlide, SlideContentType
from app.models.slide_elements import (
    BackgroundConfig,
    DiagramContent,
    ElementType,
    EquationContent,
    ImageContent,
    LayoutConstraint,
    SlideElement,
    SlideElementTree,
    TextContent,
    TextRun,
)

REFERENCE_WIDTH_PX = 1920
REFERENCE_HEIGHT_PX = 1080


def _select_default_preset(slide: RefinedSlide) -> str:
    content_type = slide.content_type

    if content_type == SlideContentType.TITLE:
        return "title_centered"
    if content_type == SlideContentType.DIAGRAM:
        return "diagram_focus"
    if content_type == SlideContentType.EQUATION:
        return "equation_focus"
    if content_type == SlideContentType.BIG_STAT:
        return "big_stat"
    if content_type == SlideContentType.TIMELINE:
        return "timeline"
    if content_type == SlideContentType.COMPARISON:
        return "comparison"
    if content_type == SlideContentType.QUOTE:
        return "quote"
    if content_type == SlideContentType.REFERENCES:
        return "references"
    if content_type == SlideContentType.TWO_COLUMN:
        return "two_col_text_text"
    if slide.image_url:
        return "two_col_text_image"
    return "content_bullets"


def _region_to_pixels(width_pct: float, height_pct: float) -> tuple[int, int]:
    return (
        int(REFERENCE_WIDTH_PX * (width_pct / 100.0)),
        int(REFERENCE_HEIGHT_PX * (height_pct / 100.0)),
    )


def _first_region(preset: LayoutPreset, keys: List[str]):
    for key in keys:
        region = preset.regions.get(key)
        if region is not None:
            return key, region
    return None, None


def _rectangles_intersect(a: SlideElement, b: SlideElement) -> bool:
    ax2 = a.x + a.width
    ay2 = a.y + a.height
    bx2 = b.x + b.width
    by2 = b.y + b.height
    return not (ax2 <= b.x or bx2 <= a.x or ay2 <= b.y or by2 <= a.y)


def layout_slide(slide: RefinedSlide, preset_id: Optional[str] = None) -> SlideElementTree:
    """
    Convert a RefinedSlide into a positioned SlideElementTree.
    """
    selected_preset_id = preset_id or _select_default_preset(slide)
    preset = get_layout_preset(selected_preset_id)

    elements: List[SlideElement] = []
    warnings: List[str] = []

    # Title element
    title_region_key, title_region = _first_region(preset, ["title", "quote_text", "stat_number"])
    if title_region:
        title_w_px, title_h_px = _region_to_pixels(title_region.width, title_region.height)
        title_fit = fit_text_to_box(
            text=slide.title or "",
            box_width_px=title_w_px,
            box_height_px=title_h_px,
            start_size=44,
            min_size=24,
        )
        elements.append(
            SlideElement(
                id=f"slide-{slide.order}-title",
                type=ElementType.TEXT,
                x=title_region.x,
                y=title_region.y,
                width=title_region.width,
                height=title_region.height,
                z_index=1,
                content=TextContent(
                    type="text",
                    runs=[TextRun(text=slide.title, size=title_fit.font_size, bold=True)],
                ),
            )
        )

    # Body text element
    body_region_key, body_region = _first_region(
        preset, ["body", "left_body", "right_body", "reference_list", "explanation"]
    )
    if body_region and slide.bullet_points:
        body_text = "\n".join(slide.bullet_points)
        body_w_px, body_h_px = _region_to_pixels(body_region.width, body_region.height)
        body_fit = fit_text_to_box(
            text=body_text,
            box_width_px=body_w_px,
            box_height_px=body_h_px,
            start_size=28,
            min_size=16,
        )
        if body_fit.truncated:
            warnings.append(f"text_body_truncated:{slide.order}")
        elements.append(
            SlideElement(
                id=f"slide-{slide.order}-body",
                type=ElementType.TEXT,
                x=body_region.x,
                y=body_region.y,
                width=body_region.width,
                height=body_region.height,
                z_index=1,
                content=TextContent(
                    type="text",
                    runs=[TextRun(text=body_text, size=body_fit.font_size)],
                ),
            )
        )

    # Visual elements (image / equation / diagram)
    visual_region_key, visual_region = _first_region(
        preset,
        ["right_visual", "left_visual", "diagram", "equation", "timeline_track", "left_panel", "right_panel"],
    )
    if visual_region:
        if slide.image_url:
            elements.append(
                SlideElement(
                    id=f"slide-{slide.order}-image",
                    type=ElementType.IMAGE,
                    x=visual_region.x,
                    y=visual_region.y,
                    width=visual_region.width,
                    height=visual_region.height,
                    z_index=1,
                    content=ImageContent(
                        type="image",
                        url=slide.image_url,
                        alt=slide.image_alt,
                        caption=slide.image_caption,
                    ),
                )
            )
        elif slide.equation_latex:
            elements.append(
                SlideElement(
                    id=f"slide-{slide.order}-equation",
                    type=ElementType.EQUATION,
                    x=visual_region.x,
                    y=visual_region.y,
                    width=visual_region.width,
                    height=visual_region.height,
                    z_index=1,
                    content=EquationContent(
                        type="equation",
                        latex=slide.equation_latex,
                        rendered_svg=slide.equation_svg,
                    ),
                )
            )
        elif slide.diagram_mermaid or slide.diagram_svg:
            elements.append(
                SlideElement(
                    id=f"slide-{slide.order}-diagram",
                    type=ElementType.DIAGRAM,
                    x=visual_region.x,
                    y=visual_region.y,
                    width=visual_region.width,
                    height=visual_region.height,
                    z_index=1,
                    content=DiagramContent(
                        type="diagram",
                        mermaid_source=slide.diagram_mermaid,
                        rendered_svg=slide.diagram_svg,
                    ),
                )
            )

    # Constraint checks
    for idx in range(len(elements)):
        for jdx in range(idx + 1, len(elements)):
            if _rectangles_intersect(elements[idx], elements[jdx]):
                warnings.append(f"overlap:{elements[idx].id}:{elements[jdx].id}")

    constraints = [
        LayoutConstraint(type="no_overflow", elements=[el.id for el in elements]),
        LayoutConstraint(type="no_intersection", elements=[el.id for el in elements]),
    ]

    return SlideElementTree(
        slide_id=f"slide-{slide.order}",
        order=slide.order,
        layout_id=selected_preset_id,
        background=BackgroundConfig(type="solid", color="#FFFFFF"),
        elements=elements,
        constraints=constraints,
        warnings=warnings,
    )
