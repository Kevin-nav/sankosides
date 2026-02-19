from app.core.text_fitting import fit_text_to_box, _estimate_line_capacity, _estimate_text_height


def test_fit_text_reduces_font_size_when_overflowing():
    result = fit_text_to_box(
        text="A " * 200,
        box_width_px=320,
        box_height_px=120,
        start_size=32,
        min_size=16,
    )
    assert result.font_size <= 32
    assert result.font_size >= 16


def test_estimate_text_height_uses_ceiling_division_without_extra_line():
    box_width_px = 320
    font_size = 20
    capacity = _estimate_line_capacity(box_width_px, font_size)
    height = _estimate_text_height("A" * capacity, box_width_px, font_size)

    assert height == int(font_size * 1.25)
