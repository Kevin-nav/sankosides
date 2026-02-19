"""Data-driven slide layout presets for the element-tree engine."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class Region(BaseModel):
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)
    width: float = Field(..., gt=0, le=100)
    height: float = Field(..., gt=0, le=100)


class LayoutPreset(BaseModel):
    id: str
    description: str = ""
    regions: Dict[str, Region]


PRESETS: Dict[str, LayoutPreset] = {
    "title_centered": LayoutPreset(
        id="title_centered",
        description="Centered title/subtitle layout.",
        regions={
            "title": Region(x=10, y=28, width=80, height=18),
            "subtitle": Region(x=15, y=48, width=70, height=16),
            "footer": Region(x=10, y=90, width=80, height=6),
        },
    ),
    "content_bullets": LayoutPreset(
        id="content_bullets",
        description="Standard title + full-width body bullets.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "body": Region(x=7, y=18, width=86, height=76),
        },
    ),
    "two_col_text_image": LayoutPreset(
        id="two_col_text_image",
        description="Text on left, visual on right.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "left_body": Region(x=5, y=18, width=45, height=75),
            "right_visual": Region(x=52, y=18, width=43, height=75),
        },
    ),
    "two_col_image_text": LayoutPreset(
        id="two_col_image_text",
        description="Visual on left, text on right.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "left_visual": Region(x=5, y=18, width=43, height=75),
            "right_body": Region(x=52, y=18, width=43, height=75),
        },
    ),
    "two_col_text_text": LayoutPreset(
        id="two_col_text_text",
        description="Two balanced text columns.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "left_body": Region(x=5, y=18, width=43, height=75),
            "right_body": Region(x=52, y=18, width=43, height=75),
        },
    ),
    "diagram_focus": LayoutPreset(
        id="diagram_focus",
        description="Large center diagram with title.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "diagram": Region(x=10, y=18, width=80, height=70),
            "caption": Region(x=10, y=90, width=80, height=6),
        },
    ),
    "equation_focus": LayoutPreset(
        id="equation_focus",
        description="Large centered equation with optional explanation.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "equation": Region(x=12, y=28, width=76, height=30),
            "explanation": Region(x=10, y=62, width=80, height=26),
        },
    ),
    "big_stat": LayoutPreset(
        id="big_stat",
        description="Hero metric layout.",
        regions={
            "stat_number": Region(x=10, y=26, width=80, height=24),
            "stat_label": Region(x=20, y=50, width=60, height=10),
            "body": Region(x=10, y=63, width=80, height=24),
        },
    ),
    "timeline": LayoutPreset(
        id="timeline",
        description="Horizontal timeline with title.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "timeline_track": Region(x=6, y=24, width=88, height=60),
        },
    ),
    "comparison": LayoutPreset(
        id="comparison",
        description="Side-by-side comparison panels.",
        regions={
            "title": Region(x=5, y=3, width=90, height=12),
            "left_panel": Region(x=6, y=18, width=42, height=74),
            "right_panel": Region(x=52, y=18, width=42, height=74),
        },
    ),
    "quote": LayoutPreset(
        id="quote",
        description="Centered quote with attribution.",
        regions={
            "quote_text": Region(x=12, y=25, width=76, height=40),
            "attribution": Region(x=20, y=68, width=60, height=10),
        },
    ),
    "references": LayoutPreset(
        id="references",
        description="Dense references list.",
        regions={
            "title": Region(x=5, y=3, width=90, height=10),
            "reference_list": Region(x=6, y=15, width=88, height=80),
        },
    ),
}


def get_layout_preset(preset_id: str) -> LayoutPreset:
    """Return a layout preset or raise KeyError for unknown ids."""
    return PRESETS[preset_id]


def has_layout_preset(preset_id: str) -> bool:
    """Return True when the preset id exists in the registry."""
    return preset_id in PRESETS


def list_layout_presets() -> Dict[str, LayoutPreset]:
    """Return all registered presets."""
    return PRESETS
