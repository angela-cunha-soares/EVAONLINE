"""
Tests for frontend/pages/documentation.py.

Smoke tests for every section creator + layout builder.
All functions are pure (lang → Dash components), no I/O needed.
"""

import pytest
from dash import html



# ---------------------------------------------------------------------------
# _t helper
# ---------------------------------------------------------------------------
class TestTHelper:
    def test_returns_string(self):
        from frontend.pages.documentation import _t
        result = _t("en", "nav_quick_start")
        assert isinstance(result, str)

    def test_fallback_for_unknown_key(self):
        from frontend.pages.documentation import _t
        result = _t("en", "nonexistent_key_xyz", default="fallback")
        assert result == "fallback"


# ---------------------------------------------------------------------------
# Section creators — smoke tests
# ---------------------------------------------------------------------------
class TestSectionCreators:
    """Each section creator should return a Dash component without errors."""

    @pytest.fixture(params=["en", "pt"])
    def lang(self, request):
        return request.param

    def test_quick_start(self, lang):
        from frontend.pages.documentation import _create_quick_start_section
        result = _create_quick_start_section(lang)
        assert result is not None

    def test_interactive_map(self, lang):
        from frontend.pages.documentation import _create_interactive_map_section
        result = _create_interactive_map_section(lang)
        assert result is not None

    def test_operation_modes(self, lang):
        from frontend.pages.documentation import _create_operation_modes_section
        result = _create_operation_modes_section(lang)
        assert result is not None

    def test_usa_stations(self, lang):
        from frontend.pages.documentation import _create_usa_stations_section
        result = _create_usa_stations_section(lang)
        assert result is not None

    def test_results(self, lang):
        from frontend.pages.documentation import _create_results_section
        result = _create_results_section(lang)
        assert result is not None

    def test_variables(self, lang):
        from frontend.pages.documentation import _create_variables_section
        result = _create_variables_section(lang)
        assert result is not None

    def test_data_sources(self, lang):
        from frontend.pages.documentation import _create_data_sources_section
        result = _create_data_sources_section(lang)
        assert result is not None

    def test_features(self, lang):
        from frontend.pages.documentation import _create_features_section
        result = _create_features_section(lang)
        assert result is not None

    def test_usage_limits(self, lang):
        from frontend.pages.documentation import _create_usage_limits_section
        result = _create_usage_limits_section(lang)
        assert result is not None

    def test_faq(self, lang):
        from frontend.pages.documentation import _create_faq_section
        result = _create_faq_section(lang)
        assert result is not None

    def test_license(self, lang):
        from frontend.pages.documentation import _create_license_section
        result = _create_license_section(lang)
        assert result is not None


# ---------------------------------------------------------------------------
# create_documentation_layout
# ---------------------------------------------------------------------------
class TestCreateDocumentationLayout:
    def test_returns_div_en(self):
        from frontend.pages.documentation import create_documentation_layout
        result = create_documentation_layout(lang="en")
        assert isinstance(result, html.Div)

    def test_returns_div_pt(self):
        from frontend.pages.documentation import create_documentation_layout
        result = create_documentation_layout(lang="pt")
        assert isinstance(result, html.Div)

    def test_default_lang(self):
        from frontend.pages.documentation import create_documentation_layout
        result = create_documentation_layout()
        assert result is not None
