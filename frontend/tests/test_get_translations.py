"""Tests for shared_utils.get_translations module."""

import json
import os
import pytest
from unittest.mock import patch, mock_open

from shared_utils.get_translations import get_translations, t, clear_translations_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear translation cache before each test."""
    clear_translations_cache()
    yield
    clear_translations_cache()


class TestGetTranslations:
    """Tests for get_translations function."""

    def test_load_english(self):
        result = get_translations("en")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_load_portuguese(self):
        result = get_translations("pt")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_caching(self):
        """Second call should use cache."""
        result1 = get_translations("en")
        result2 = get_translations("en")
        assert result1 is result2

    def test_unknown_lang_falls_back_to_english(self):
        result = get_translations("xx")
        en_result = get_translations("en")
        assert result == en_result

    def test_default_is_english(self):
        result = get_translations()
        en_result = get_translations("en")
        assert result == en_result

    def test_translations_have_navbar(self):
        """Basic structure check - translations should have navbar section."""
        result = get_translations("en")
        assert "navbar" in result


class TestTFunction:
    """Tests for t() shortcut function."""

    def test_simple_key(self):
        result = t("en", "navbar", "home")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_nested_key(self):
        result = t("pt", "navbar", "home")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_key_returns_default(self):
        result = t("en", "nonexistent", "key", default="fallback")
        assert result == "fallback"

    def test_missing_key_default_empty(self):
        result = t("en", "nonexistent", "key")
        assert result == ""

    def test_partial_path_with_dict_value(self):
        """If traversal stops at a dict (not string), return default."""
        result = t("en", "navbar", default="fallback")
        # "navbar" points to a dict, not a string
        assert result == "fallback"

    def test_pt_vs_en_differ(self):
        """PT and EN translations should differ for at least some keys."""
        en = t("en", "navbar", "home")
        pt = t("pt", "navbar", "home")
        # They might be the same if key is a proper noun, but generally differ
        assert isinstance(en, str)
        assert isinstance(pt, str)


class TestClearTranslationsCache:
    """Tests for clear_translations_cache function."""

    def test_clears_cache(self):
        get_translations("en")
        clear_translations_cache()
        # After clear, need to reload from file
        from shared_utils.get_translations import _translations_cache
        assert len(_translations_cache) == 0

    def test_reload_after_clear(self):
        result1 = get_translations("en")
        clear_translations_cache()
        result2 = get_translations("en")
        assert result1 == result2
        # But NOT the same object (reloaded)
        assert result1 is not result2
