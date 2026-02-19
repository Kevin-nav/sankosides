from app.core.layout_presets import get_layout_preset


def test_two_col_text_image_preset_exists():
    preset = get_layout_preset("two_col_text_image")
    assert preset.id == "two_col_text_image"
    assert "left_body" in preset.regions
    assert "right_visual" in preset.regions
