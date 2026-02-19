"""Utilities for deterministic text fitting inside bounded slide regions."""

from pydantic import BaseModel


class TextFitResult(BaseModel):
    font_size: int
    truncated: bool = False


def _estimate_line_capacity(box_width_px: int, font_size: int) -> int:
    # Average glyph width approximation for sans-serif body text.
    avg_char_width = max(1.0, font_size * 0.55)
    return max(1, int(box_width_px / avg_char_width))


def _estimate_text_height(text: str, box_width_px: int, font_size: int) -> int:
    capacity = _estimate_line_capacity(box_width_px, font_size)
    if capacity <= 0:
        capacity = 1
    line_count = max(1, (len(text) + capacity - 1) // capacity)
    line_height = font_size * 1.25
    return int(line_count * line_height)


def fit_text_to_box(
    text: str,
    box_width_px: int,
    box_height_px: int,
    start_size: int,
    min_size: int,
) -> TextFitResult:
    """
    Return the largest font size in [min_size, start_size] that fits the text box.

    The fit is deterministic and based on simple character-density heuristics,
    which is sufficient for pre-layout checks before browser rendering.
    """
    size = start_size
    while size > min_size:
        if _estimate_text_height(text, box_width_px, size) <= box_height_px:
            return TextFitResult(font_size=size, truncated=False)
        size -= 1

    return TextFitResult(font_size=min_size, truncated=True)
