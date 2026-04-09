"""
Unit Tests - Database Models (ClimateData + APIVariables)

Tests ORM model attributes, repr, to_dict, indexes, and constraints
without requiring a database connection.

Reference: Article Section 3 (Data Storage Layer)
"""

import pytest
from datetime import datetime

from sqlalchemy.orm import configure_mappers

from backend.database.models.climate_data import ClimateData
from backend.database.models.api_variables import APIVariables

# Ensure all mappers are fully configured (avoids impl=None when
# other tests import modules that partially configure SQLAlchemy).
configure_mappers()


# ============================================================================
# ClimateData Model
# ============================================================================


@pytest.mark.unit
class TestClimateDataModel:
    """ClimateData ORM model tests."""

    def _make_climate_data(self, **overrides):
        """Factory helper bypassing SQLAlchemy instrumentation."""
        defaults = dict(
            id=1,
            source_api="nasa_power",
            latitude=-23.55,
            longitude=-46.63,
            elevation=760.0,
            timezone="America/Sao_Paulo",
            date=datetime(2025, 1, 15),
            raw_data={"T2M_MAX": 28.5, "T2M_MIN": 18.2},
            harmonized_data={"temp_max_c": 28.5, "temp_min_c": 18.2},
            eto_mm_day=4.5,
            eto_method="penman_monteith",
            quality_flags={"missing_data": False},
            processing_metadata={"version": "1.0"},
            created_at=datetime(2025, 1, 15, 10, 0),
        )
        defaults.update(overrides)
        obj = object.__new__(ClimateData)
        obj.__dict__.update(defaults)
        return obj

    def test_tablename(self):
        assert ClimateData.__tablename__ == "climate_data"

    def test_repr_contains_source(self):
        obj = self._make_climate_data()
        r = repr(obj)
        assert "nasa_power" in r

    def test_repr_contains_coordinates(self):
        obj = self._make_climate_data()
        r = repr(obj)
        assert "-23.55" in r
        assert "-46.63" in r

    def test_repr_handles_none_date(self):
        obj = self._make_climate_data(date=None)
        r = repr(obj)
        assert "None" in r

    def test_to_dict_all_keys(self):
        obj = self._make_climate_data()
        d = obj.to_dict()
        expected_keys = {
            "id", "source_api", "latitude", "longitude", "elevation",
            "timezone", "date", "raw_data", "harmonized_data",
            "eto_mm_day", "eto_method", "quality_flags", "created_at",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_to_dict_date_is_isoformat(self):
        obj = self._make_climate_data()
        d = obj.to_dict()
        assert d["date"] == "2025-01-15T00:00:00"

    def test_to_dict_none_date(self):
        obj = self._make_climate_data(date=None)
        d = obj.to_dict()
        assert d["date"] is None

    def test_to_dict_none_elevation(self):
        obj = self._make_climate_data(elevation=None)
        d = obj.to_dict()
        assert d["elevation"] is None

    def test_to_dict_raw_data_preserved(self):
        obj = self._make_climate_data()
        d = obj.to_dict()
        assert d["raw_data"]["T2M_MAX"] == 28.5

    def test_indexes_defined(self):
        """Model should have composite indexes."""
        args = ClimateData.__table_args__
        index_names = [
            a.name for a in args if hasattr(a, "name") and isinstance(a.name, str)
        ]
        assert "idx_climate_location_date" in index_names
        assert "idx_climate_source_date" in index_names
        assert "idx_climate_date" in index_names


# ============================================================================
# APIVariables Model
# ============================================================================


@pytest.mark.unit
class TestAPIVariablesModel:
    """APIVariables ORM model tests."""

    def _make_api_variable(self, **overrides):
        """Factory helper bypassing SQLAlchemy instrumentation."""
        defaults = dict(
            id=1,
            source_api="nasa_power",
            variable_name="T2M_MAX",
            standard_name="temp_max_c",
            unit="\u00b0C",
            description="Temperatura m\u00e1xima a 2 metros",
            is_required_for_eto=True,
        )
        defaults.update(overrides)
        obj = object.__new__(APIVariables)
        obj.__dict__.update(defaults)
        return obj

    def test_tablename(self):
        assert APIVariables.__tablename__ == "api_variables"

    def test_repr_contains_source(self):
        obj = self._make_api_variable()
        r = repr(obj)
        assert "nasa_power" in r

    def test_repr_contains_variable_name(self):
        obj = self._make_api_variable()
        r = repr(obj)
        assert "T2M_MAX" in r

    def test_repr_contains_standard_name(self):
        obj = self._make_api_variable()
        r = repr(obj)
        assert "temp_max_c" in r

    def test_repr_contains_eto_flag(self):
        obj = self._make_api_variable()
        r = repr(obj)
        assert "True" in r

    def test_to_dict_all_keys(self):
        obj = self._make_api_variable()
        d = obj.to_dict()
        expected_keys = {
            "id", "source_api", "variable_name", "standard_name",
            "unit", "description", "is_required_for_eto",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_values(self):
        obj = self._make_api_variable()
        d = obj.to_dict()
        assert d["source_api"] == "nasa_power"
        assert d["variable_name"] == "T2M_MAX"
        assert d["standard_name"] == "temp_max_c"
        assert d["unit"] == "°C"
        assert d["is_required_for_eto"] is True

    def test_to_dict_none_description(self):
        obj = self._make_api_variable(description=None)
        d = obj.to_dict()
        assert d["description"] is None

    def test_unique_constraint_defined(self):
        args = APIVariables.__table_args__
        constraint_names = [
            a.name for a in args
            if hasattr(a, "name") and isinstance(a.name, str)
        ]
        assert "uq_api_variable" in constraint_names

    def test_indexes_defined(self):
        args = APIVariables.__table_args__
        index_names = [
            a.name for a in args
            if hasattr(a, "name") and isinstance(a.name, str) and a.name.startswith("idx_")
        ]
        assert "idx_source_api" in index_names
        assert "idx_standard_name" in index_names
        assert "idx_required_eto" in index_names

    def test_default_eto_flag_is_false(self):
        """Column default for is_required_for_eto should be False."""
        col = APIVariables.__table__.columns["is_required_for_eto"]
        assert col.default is not None
        assert col.default.arg is False
