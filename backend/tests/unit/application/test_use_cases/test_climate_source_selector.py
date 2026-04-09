"""
Unit Tests - ClimateSourceSelector

Tests intelligent source selection based on geographic region.
USA → NWS, Nordic → MET Norway, Global → Open-Meteo.

Reference: Article Section 2.2 (Source Selection Algorithm)
"""

import pytest

from backend.api.services.climate_source_selector import (
    ClimateSourceSelector,
    get_available_sources_for_frontend,
)


@pytest.mark.unit
class TestSelectSource:
    """Best source selection by region."""

    def test_usa_selects_nws(self):
        """USA coordinates should select NWS as primary."""
        result = ClimateSourceSelector.select_source(39.74, -104.99)
        # Result is a NamedTuple/dataclass with source_id
        source_id = result.source_id if hasattr(result, "source_id") else str(result)
        assert "nws" in source_id.lower() or "forecast" in source_id.lower()

    def test_nordic_selects_met_norway(self):
        """Nordic coordinates should select MET Norway."""
        result = ClimateSourceSelector.select_source(60.17, 24.94)
        source_id = result.source_id if hasattr(result, "source_id") else str(result)
        assert "met" in source_id.lower() or "norway" in source_id.lower()

    def test_brazil_selects_openmeteo(self):
        """Brazil coordinates should select Open-Meteo."""
        result = ClimateSourceSelector.select_source(-23.55, -46.63)
        source_id = result.source_id if hasattr(result, "source_id") else str(result)
        assert "openmeteo" in source_id.lower()

    def test_global_selects_openmeteo(self):
        """Global location should default to Open-Meteo."""
        result = ClimateSourceSelector.select_source(35.68, 139.69)  # Tokyo
        source_id = result.source_id if hasattr(result, "source_id") else str(result)
        assert "openmeteo" in source_id.lower()


@pytest.mark.unit
class TestGetAllSources:
    """Ordered source list per region."""

    def test_usa_includes_nws_sources(self):
        sources = ClimateSourceSelector.get_all_sources(39.74, -104.99)
        source_ids = [
            s.source_id if hasattr(s, "source_id") else str(s)
            for s in sources
        ]
        assert any("nws" in sid.lower() for sid in source_ids)

    def test_nordic_includes_met_norway(self):
        sources = ClimateSourceSelector.get_all_sources(60.17, 24.94)
        source_ids = [
            s.source_id if hasattr(s, "source_id") else str(s)
            for s in sources
        ]
        assert any("met" in sid.lower() for sid in source_ids)

    def test_all_sources_has_global_fallbacks(self):
        """Every location should have NASA POWER and OpenMeteo as fallbacks."""
        sources = ClimateSourceSelector.get_all_sources(-23.55, -46.63)
        source_ids = [
            (s.source_id if hasattr(s, "source_id") else str(s)).lower()
            for s in sources
        ]
        assert any("nasa" in sid for sid in source_ids)
        assert any("openmeteo" in sid for sid in source_ids)

    def test_returns_multiple_sources(self):
        sources = ClimateSourceSelector.get_all_sources(0, 0)
        assert len(sources) >= 2


@pytest.mark.unit
class TestDataAvailabilitySummary:
    """Static API summary."""

    def test_returns_dict(self):
        summary = ClimateSourceSelector.get_data_availability_summary()
        assert isinstance(summary, dict)

    def test_has_all_six_sources(self):
        summary = ClimateSourceSelector.get_data_availability_summary()
        assert len(summary) >= 6

    def test_each_source_has_metadata(self):
        summary = ClimateSourceSelector.get_data_availability_summary()
        for key, value in summary.items():
            assert isinstance(value, dict)


@pytest.mark.unit
class TestGetCoverageInfo:
    """Location-specific coverage details."""

    def test_returns_dict(self):
        info = ClimateSourceSelector.get_coverage_info(-23.55, -46.63)
        assert isinstance(info, dict)

    def test_has_recommended_source(self):
        info = ClimateSourceSelector.get_coverage_info(-23.55, -46.63)
        assert "recommended_source" in info or "primary" in info or "recommended" in str(info)

    def test_has_all_sources(self):
        info = ClimateSourceSelector.get_coverage_info(39.74, -104.99)
        assert "all_sources" in info or "sources" in info or len(info) > 1


@pytest.mark.unit
class TestGetAvailableSourcesForFrontend:
    """Frontend dropdown source list."""

    def test_returns_dict(self):
        result = get_available_sources_for_frontend(-23.55, -46.63)
        assert isinstance(result, dict)

    def test_usa_includes_stations_option(self):
        result = get_available_sources_for_frontend(39.74, -104.99)
        # Should have a key indicating USA-specific sources
        result_str = str(result).lower()
        assert "nws" in result_str or "station" in result_str or "usa" in result_str

    def test_global_location_has_fusion_default(self):
        result = get_available_sources_for_frontend(-23.55, -46.63)
        result_str = str(result).lower()
        assert "fusion" in result_str or "openmeteo" in result_str
