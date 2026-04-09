"""Tests for frontend.callbacks.navbar_callbacks module."""

import pytest
from unittest.mock import patch, MagicMock
from dash.exceptions import PreventUpdate

from frontend.callbacks.navbar_callbacks import (
    toggle_language,
    translate_navbar_links,
    highlight_active_link,
)


# ============================================================================
# Tests for toggle_language
# ============================================================================
class TestToggleLanguage:
    def test_en_to_pt(self):
        assert toggle_language(1, "en") == "pt"

    def test_pt_to_en(self):
        assert toggle_language(1, "pt") == "en"

    def test_no_clicks_raises_prevent_update(self):
        with pytest.raises(PreventUpdate):
            toggle_language(None, "en")

    def test_zero_clicks_raises_prevent_update(self):
        with pytest.raises(PreventUpdate):
            toggle_language(0, "en")

    def test_multiple_clicks(self):
        assert toggle_language(5, "en") == "pt"

    def test_unknown_language_defaults(self):
        # Any non-"en" value returns "en"
        assert toggle_language(1, "fr") == "en"


# ============================================================================
# Tests for translate_navbar_links
# ============================================================================
class TestTranslateNavbarLinks:
    def test_english(self):
        result = translate_navbar_links("en")
        assert isinstance(result, tuple)
        assert len(result) == 5

    def test_portuguese(self):
        result = translate_navbar_links("pt")
        assert isinstance(result, tuple)
        assert len(result) == 5

    def test_none_defaults_to_english(self):
        result = translate_navbar_links(None)
        en_result = translate_navbar_links("en")
        assert result == en_result

    def test_returns_strings(self):
        result = translate_navbar_links("en")
        for item in result:
            assert isinstance(item, str)


# ============================================================================
# Tests for highlight_active_link
# ============================================================================
class TestHighlightActiveLink:
    def test_home_active(self):
        result = highlight_active_link("/")
        home_style, docs_style, arch_style, about_style = result
        assert home_style["fontWeight"] == "600"
        assert docs_style["fontWeight"] == "400"

    def test_eto_calculator_is_home(self):
        result = highlight_active_link("/eto-calculator")
        home_style = result[0]
        assert home_style["fontWeight"] == "600"

    def test_documentation_active(self):
        result = highlight_active_link("/documentation")
        home_style, docs_style, arch_style, about_style = result
        assert docs_style["fontWeight"] == "600"
        assert home_style["fontWeight"] == "400"

    def test_architecture_active(self):
        result = highlight_active_link("/architecture")
        _, _, arch_style, _ = result
        assert arch_style["fontWeight"] == "600"

    def test_about_active(self):
        result = highlight_active_link("/about")
        _, _, _, about_style = result
        assert about_style["fontWeight"] == "600"

    def test_none_pathname_is_home(self):
        result = highlight_active_link(None)
        home_style = result[0]
        assert home_style["fontWeight"] == "600"

    def test_unknown_path_all_inactive(self):
        result = highlight_active_link("/unknown")
        for style in result:
            assert style["fontWeight"] == "400"

    def test_returns_four_styles(self):
        result = highlight_active_link("/")
        assert len(result) == 4

    def test_active_style_has_border(self):
        result = highlight_active_link("/")
        assert "00695c" in result[0]["borderBottom"]

    def test_inactive_style_transparent_border(self):
        result = highlight_active_link("/documentation")
        assert "transparent" in result[0]["borderBottom"]
