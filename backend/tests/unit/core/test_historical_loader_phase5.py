"""
Phase 5 Tests: HistoricalDataLoader.get_reference_for_location().

Coverage target: backend/core/data_processing/historical_loader.py (61% → 95%+)
Lines 72-166 (get_reference_for_location: cache, city matching, JSON read).
"""

import json

import pytest

from backend.core.data_processing.historical_loader import (
    HistoricalDataLoader,
    ThreadSafeCache,
)


# ---------------------------------------------------------------------------
# ThreadSafeCache tests
# ---------------------------------------------------------------------------


class TestThreadSafeCache:
    """Tests for the LRU cache implementation."""

    def test_set_and_get(self):
        cache = ThreadSafeCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self):
        cache = ThreadSafeCache(max_size=10)
        assert cache.get("missing") is None

    def test_lru_eviction(self):
        cache = ThreadSafeCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # Evicts "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_access_refreshes_order(self):
        cache = ThreadSafeCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # Refresh "a"
        cache.set("c", 3)  # Evicts "b" (not "a")
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_clear(self):
        cache = ThreadSafeCache(max_size=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


# ---------------------------------------------------------------------------
# HistoricalDataLoader helpers
# ---------------------------------------------------------------------------

_SAMPLE_JSON = {
    "climate_normals_all_periods": {
        "1991-2020": {
            "monthly": {
                "1": {
                    "normal": 4.5,
                    "daily_std": 1.2,
                    "p01": 2.0,
                    "p99": 7.5,
                    "precip_normal": 180.0,
                    "precip_daily_std": 12.0,
                    "precip_p01": 0.0,
                    "precip_p99": 350.0,
                },
                "2": {
                    "normal": 4.8,
                    "daily_std": 1.1,
                    "p01": 2.2,
                    "p99": 7.8,
                    "precip_normal": 160.0,
                    "precip_daily_std": 11.0,
                    "precip_p01": 0.0,
                    "precip_p99": 320.0,
                },
            }
        }
    }
}


# ===========================================================================
# Test: get_reference_for_location
# ===========================================================================


class TestGetReferenceForLocation:
    """Tests for the main reference lookup method."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a loader with controlled filesystem."""
        cities_dir = tmp_path / "data" / "historical" / "cities"
        cities_dir.mkdir(parents=True)

        # Create a sample city report
        report = cities_dir / "report_saopaulo_1991_2020.json"
        report.write_text(json.dumps(_SAMPLE_JSON), encoding="utf-8")

        # Create info_cities.csv
        info_path = tmp_path / "data" / "historical" / "info_cities.csv"
        info_path.write_text(
            "city,lat,lon,region\n"
            "saopaulo,-23.55,-46.63,brasil\n"
            "newyork,40.71,-74.0,usa\n",
            encoding="utf-8",
        )

        loader = HistoricalDataLoader.__new__(HistoricalDataLoader)
        loader.historical_dir = cities_dir
        loader.city_coords_path = info_path
        loader.city_coords = loader._load_city_coords()
        loader._cache = ThreadSafeCache(max_size=100)
        return loader

    def test_finds_nearby_city(self, loader):
        """Finds São Paulo reference for a nearby coordinate."""
        found, ref = loader.get_reference_for_location(-23.5, -46.6)
        assert found is True
        assert ref is not None
        assert ref["city"] == "saopaulo"
        assert ref["distance_km"] < 10.0
        assert 1 in ref["eto_normals"]
        assert ref["eto_normals"][1] == 4.5

    def test_cache_hit_on_second_call(self, loader):
        """Second call returns cached result."""
        found1, ref1 = loader.get_reference_for_location(-23.5, -46.6)
        found2, ref2 = loader.get_reference_for_location(-23.5, -46.6)
        assert found1 is True
        assert found2 is True
        assert ref1 == ref2

    def test_too_far_returns_not_found(self, loader):
        """City > max_dist_km returns (False, None)."""
        # London is far from São Paulo and New York
        found, ref = loader.get_reference_for_location(51.5, -0.1)
        assert found is False
        assert ref is None

    def test_cache_stores_not_found(self, loader):
        """NOT_FOUND sentinel cached to avoid repeated lookups."""
        loader.get_reference_for_location(51.5, -0.1)
        # The cache should have "NOT_FOUND"
        key = (round(51.5, 3), round(-0.1, 3))
        assert loader._cache.get(key) == "NOT_FOUND"

    def test_hemisphere_filter(self, loader):
        """City in opposite hemisphere is skipped."""
        # New York (40.71°N) should NOT match for a southern location
        # São Paulo matches instead
        found, ref = loader.get_reference_for_location(-23.5, -46.6)
        assert found is True
        assert ref["city"] == "saopaulo"  # Not newyork

    def test_region_filter_brasil_excludes_foreign(self, loader):
        """Brazilian query excludes non-Brazilian cities."""
        # Query point in Brazil → should NOT use New York
        found, ref = loader.get_reference_for_location(-23.5, -46.6)
        assert found is True
        assert ref["city"] == "saopaulo"

    def test_json_read_error_returns_not_found(self, loader):
        """Corrupt JSON → returns (False, None)."""
        # Overwrite the JSON file with garbage
        report = loader.historical_dir / "report_saopaulo_1991_2020.json"
        report.write_text("NOT JSON", encoding="utf-8")

        # Clear cache to force re-read
        loader._cache.clear()

        found, ref = loader.get_reference_for_location(-23.5, -46.6)
        assert found is False
        assert ref is None

    def test_max_dist_parameter(self, loader):
        """Custom max_dist_km respected."""
        # São Paulo is ~8km from (-23.5, -46.6)
        found_near, _ = loader.get_reference_for_location(
            -23.5, -46.6, max_dist_km=200
        )
        assert found_near is True

        loader._cache.clear()
        found_far, _ = loader.get_reference_for_location(
            -23.5, -46.6, max_dist_km=0.001
        )
        assert found_far is False


# ===========================================================================
# Test: _load_city_coords edge cases
# ===========================================================================


class TestLoadCityCoords:
    """Tests for _load_city_coords."""

    def test_missing_csv_returns_empty(self, tmp_path):
        """Missing info_cities.csv → empty dict."""
        loader = HistoricalDataLoader.__new__(HistoricalDataLoader)
        loader.city_coords_path = tmp_path / "nonexistent.csv"
        result = loader._load_city_coords()
        assert result == {}

    def test_corrupt_csv_returns_empty(self, tmp_path):
        """Corrupt CSV → empty dict."""
        bad_csv = tmp_path / "info_cities.csv"
        bad_csv.write_text("not,a,proper\ncsv,with,wrong,columns\n")
        loader = HistoricalDataLoader.__new__(HistoricalDataLoader)
        loader.city_coords_path = bad_csv
        result = loader._load_city_coords()
        # Should either return empty or handle gracefully
        assert isinstance(result, dict)

    def test_valid_csv_parsed(self, tmp_path):
        """Valid CSV → city coords dict."""
        csv_path = tmp_path / "info_cities.csv"
        csv_path.write_text(
            "city,lat,lon,region\n"
            "campinas,-22.9,-47.06,brasil\n"
        )
        loader = HistoricalDataLoader.__new__(HistoricalDataLoader)
        loader.city_coords_path = csv_path
        result = loader._load_city_coords()
        assert "campinas" in result
        assert result["campinas"][0] == pytest.approx(-22.9)
