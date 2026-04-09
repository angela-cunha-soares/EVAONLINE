"""
Unit Tests - EToVariableValidator

Tests the FAO-56 variable completeness checker used to determine
which climate sources can compute reference evapotranspiration.

Reference: Article Section 2.3 (Source Selection)
"""

import pytest

from backend.api.services.eto_variable_validator import EToVariableValidator


@pytest.mark.unit
class TestRequiredVariables:
    """Verify required variables constant is correct."""

    def test_required_variables_count(self):
        assert len(EToVariableValidator.REQUIRED_VARIABLES) == 6

    def test_required_variables_contains_temperature(self):
        rv = EToVariableValidator.REQUIRED_VARIABLES
        assert "temperature_max" in rv or "temp_max" in rv or any(
            "temp" in v and "max" in v for v in rv
        )

    def test_required_variables_is_set(self):
        assert isinstance(EToVariableValidator.REQUIRED_VARIABLES, (set, frozenset))


@pytest.mark.unit
class TestHasAllEtoVariables:
    """Test source completeness check."""

    def test_nasa_power_is_complete(self):
        assert EToVariableValidator.has_all_eto_variables("nasa_power") is True

    def test_openmeteo_archive_is_complete(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_archive") is True

    def test_openmeteo_forecast_is_complete(self):
        assert EToVariableValidator.has_all_eto_variables("openmeteo_forecast") is True

    def test_met_norway_is_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("met_norway") is False

    def test_nws_forecast_is_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("nws_forecast") is False

    def test_nws_stations_is_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("nws_stations") is False

    def test_unknown_source_is_incomplete(self):
        assert EToVariableValidator.has_all_eto_variables("unknown_api") is False


@pytest.mark.unit
class TestGetMissingVariables:
    """Test identification of missing variables."""

    def test_complete_source_returns_empty(self):
        missing = EToVariableValidator.get_missing_variables("nasa_power")
        assert missing == set()

    def test_incomplete_source_returns_nonempty(self):
        missing = EToVariableValidator.get_missing_variables("met_norway")
        assert len(missing) > 0

    def test_unknown_source_returns_all_required(self):
        missing = EToVariableValidator.get_missing_variables("fake_source")
        assert missing == EToVariableValidator.REQUIRED_VARIABLES

    def test_missing_is_subset_of_required(self):
        """Missing vars must always be a subset of required vars."""
        for source in EToVariableValidator.SOURCE_VARIABLES:
            missing = EToVariableValidator.get_missing_variables(source)
            assert missing.issubset(EToVariableValidator.REQUIRED_VARIABLES)


@pytest.mark.unit
class TestGetAvailableVariables:
    """Test retrieval of available variables per source."""

    def test_known_source_returns_nonempty(self):
        avail = EToVariableValidator.get_available_variables("nasa_power")
        assert len(avail) > 0

    def test_unknown_source_returns_empty(self):
        avail = EToVariableValidator.get_available_variables("nonexistent")
        assert avail == set()

    def test_available_plus_missing_equals_required_for_complete(self):
        """For a complete source, available ⊇ required."""
        avail = EToVariableValidator.get_available_variables("nasa_power")
        assert EToVariableValidator.REQUIRED_VARIABLES.issubset(avail)


@pytest.mark.unit
class TestGetSourcesWithCompleteEto:
    """Test enumeration of complete sources."""

    def test_returns_list(self):
        result = EToVariableValidator.get_sources_with_complete_eto()
        assert isinstance(result, list)

    def test_contains_nasa_power(self):
        assert "nasa_power" in EToVariableValidator.get_sources_with_complete_eto()

    def test_contains_openmeteo_archive(self):
        assert "openmeteo_archive" in EToVariableValidator.get_sources_with_complete_eto()

    def test_excludes_incomplete_sources(self):
        complete = EToVariableValidator.get_sources_with_complete_eto()
        assert "met_norway" not in complete
        assert "nws_forecast" not in complete

    def test_at_least_three_complete(self):
        assert len(EToVariableValidator.get_sources_with_complete_eto()) >= 3


@pytest.mark.unit
class TestGetSourceDescription:
    """Test source description dict generation."""

    def test_complete_source_description(self):
        desc = EToVariableValidator.get_source_description("nasa_power")
        assert isinstance(desc, dict)
        assert desc.get("has_complete_eto") is True

    def test_incomplete_source_description(self):
        desc = EToVariableValidator.get_source_description("met_norway")
        assert desc.get("has_complete_eto") is False

    def test_description_has_source_id(self):
        desc = EToVariableValidator.get_source_description("openmeteo_forecast")
        assert "source_id" in desc or "source" in desc or "id" in desc

    def test_unknown_source_description(self):
        desc = EToVariableValidator.get_source_description("nonexistent")
        assert isinstance(desc, dict)
        assert desc.get("has_complete_eto") is False
