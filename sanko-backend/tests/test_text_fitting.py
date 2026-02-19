from app.core.text_fitting import fit_text_to_box


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
