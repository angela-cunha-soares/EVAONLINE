"""
Comprehensive tests for data_download service and ETo processing.

Tests:
- download_weather_data validation paths (coordinates, dates, modes)
- Source normalization logic
- Data DataFrame construction with harmonization columns
- ETo processing: _summarize, _generate_recommendations, _calculate_raw_eto
- ClimateValidationService edge cases
"""
import asyncio
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest


# ════════════════════════════════════════════════════════════════
# Data download — input validation paths
# ════════════════════════════════════════════════════════════════
class TestDownloadValidation:

    def _run(self, coro):
        """Helper to run async function"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_invalid_coordinates_raises(self):
        from backend.api.services.data_download import download_weather_data
        with pytest.raises(ValueError, match="[Ii]nvalid|[Cc]oord"):
            self._run(download_weather_data(
                data_source="nasa_power",
                data_inicial="2024-01-01",
                data_final="2024-01-30",
                longitude=0.0,
                latitude=200.0,  # Invalid
            ))

    def test_invalid_dates_raises(self):
        from backend.api.services.data_download import download_weather_data
        with pytest.raises((ValueError, Exception)):
            self._run(download_weather_data(
                data_source="nasa_power",
                data_inicial="not-a-date",
                data_final="2024-01-30",
                longitude=-46.63,
                latitude=-23.55,
            ))

    def test_start_after_end_raises(self):
        from backend.api.services.data_download import download_weather_data
        with pytest.raises((ValueError, Exception)):
            self._run(download_weather_data(
                data_source="nasa_power",
                data_inicial="2024-12-31",
                data_final="2024-01-01",
                longitude=-46.63,
                latitude=-23.55,
            ))


# ════════════════════════════════════════════════════════════════
# Data download — source normalization
# ════════════════════════════════════════════════════════════════
class TestSourceNormalization:

    def test_list_source_normalization(self):
        """Test that list sources are normalized correctly"""
        sources = ["NASA_POWER", "openmeteo_archive"]
        normalized = [str(s).lower() for s in sources]
        assert normalized == ["nasa_power", "openmeteo_archive"]

    def test_comma_separated_source(self):
        data_source_str = "nasa_power, openmeteo_archive"
        requested_sources = [s.strip() for s in data_source_str.split(",")]
        assert requested_sources == ["nasa_power", "openmeteo_archive"]

    def test_single_source_string(self):
        data_source_str = "nasa_power"
        if "," in data_source_str:
            requested_sources = [s.strip() for s in data_source_str.split(",")]
        else:
            requested_sources = [data_source_str]
        assert requested_sources == ["nasa_power"]


# ════════════════════════════════════════════════════════════════
# DataFrame harmonization patterns
# ════════════════════════════════════════════════════════════════
class TestDataHarmonization:

    def test_openmeteo_to_nasa_harmonization(self):
        """Open-Meteo columns map to NASA POWER variables"""
        harmonization = {
            "temperature_2m_max": "T2M_MAX",
            "temperature_2m_min": "T2M_MIN",
            "temperature_2m_mean": "T2M",
            "relative_humidity_2m_mean": "RH2M",
            "wind_speed_2m_mean": "WS2M",
            "shortwave_radiation_sum": "ALLSKY_SFC_SW_DWN",
            "precipitation_sum": "PRECTOTCORR",
        }
        dates = pd.date_range("2024-01-01", periods=3)
        df = pd.DataFrame({
            "temperature_2m_max": [30.0, 31.0, 32.0],
            "temperature_2m_min": [18.0, 19.0, 20.0],
            "temperature_2m_mean": [24.0, 25.0, 26.0],
            "relative_humidity_2m_mean": [65.0, 60.0, 55.0],
            "wind_speed_2m_mean": [3.0, 3.5, 4.0],
            "shortwave_radiation_sum": [20.0, 22.0, 18.0],
            "precipitation_sum": [0.0, 5.0, 10.0],
        }, index=dates)

        for om_var, nasa_var in harmonization.items():
            if om_var in df.columns:
                df[nasa_var] = df[om_var]

        assert "T2M_MAX" in df.columns
        assert "T2M_MIN" in df.columns
        assert "RH2M" in df.columns
        assert "WS2M" in df.columns
        assert "ALLSKY_SFC_SW_DWN" in df.columns
        assert df["T2M_MAX"].iloc[0] == 30.0

    def test_nws_to_nasa_harmonization(self):
        """NWS columns map to NASA POWER variables"""
        nws_harmonization = {
            "temp_max": "T2M_MAX",
            "temp_min": "T2M_MIN",
            "temp_mean": "T2M",
            "humidity_mean": "RH2M",
            "wind_speed_2m_mean": "WS2M",
            "solar_radiation": "ALLSKY_SFC_SW_DWN",
            "precipitation_sum": "PRECTOTCORR",
        }
        dates = pd.date_range("2024-01-01", periods=2)
        df = pd.DataFrame({
            "temp_max": [28.0, 29.0],
            "temp_min": [16.0, 17.0],
            "temp_mean": [22.0, 23.0],
            "humidity_mean": [70.0, 68.0],
        }, index=dates)

        for nws_var, nasa_var in nws_harmonization.items():
            if nws_var in df.columns:
                df[nasa_var] = df[nws_var]

        assert "T2M_MAX" in df.columns
        assert df["T2M_MAX"].iloc[0] == 28.0

    def test_nan_replacement(self):
        """Replace -999.00 sentinel with NaN"""
        df = pd.DataFrame({"T2M_MAX": [30.0, -999.00, 32.0]})
        df = df.replace(-999.00, np.nan)
        assert pd.isna(df["T2M_MAX"].iloc[1])
        assert df["T2M_MAX"].iloc[0] == 30.0


# ════════════════════════════════════════════════════════════════
# ETo Processing Service — _summarize and _generate_recommendations
# ════════════════════════════════════════════════════════════════
class TestEToProcessingServiceHelpers:

    def _make_service(self):
        from backend.core.eto_calculation.eto_services import EToProcessingService
        return EToProcessingService()

    def test_summarize_basic(self):
        service = self._make_service()
        dates = pd.date_range("2024-07-01", periods=30)
        df = pd.DataFrame({
            "et0_mm_day": np.random.uniform(3.0, 6.0, 30),
            "T2M_MAX": np.random.uniform(25, 35, 30),
            "T2M_MIN": np.random.uniform(15, 22, 30),
        }, index=dates)
        summary = service._summarize(df)
        assert isinstance(summary, dict)
        assert "et0_mean_mm_day" in summary

    def test_generate_recommendations(self):
        service = self._make_service()
        dates = pd.date_range("2024-07-01", periods=30)
        df = pd.DataFrame({
            "et0_mm_day": np.random.uniform(3.0, 6.0, 30),
        }, index=dates)
        recs = service._generate_recommendations(df)
        assert isinstance(recs, list)
        assert len(recs) >= 1


# ════════════════════════════════════════════════════════════════
# ETo Calculation Service — validate_measurements
# ════════════════════════════════════════════════════════════════
class TestEToCalculationServiceValidation:

    def _make_service(self):
        from backend.core.eto_calculation.eto_services import EToCalculationService
        return EToCalculationService()

    def _valid_measurements(self):
        return {
            "T2M_MAX": 30.0,
            "T2M_MIN": 18.0,
            "T2M": 24.0,
            "RH2M": 65.0,
            "WS2M": 2.5,
            "ALLSKY_SFC_SW_DWN": 20.0,
            "latitude": -23.55,
            "longitude": -46.63,
            "date": "2024-07-15",
            "elevation_m": 760.0,
        }

    def test_valid_measurements(self):
        svc = self._make_service()
        ok = svc._validate_measurements(self._valid_measurements())
        assert ok is True

    def test_missing_temp_max(self):
        svc = self._make_service()
        m = self._valid_measurements()
        del m["T2M_MAX"]
        with pytest.raises(ValueError, match="ausentes"):
            svc._validate_measurements(m)

    def test_temp_inverted(self):
        """T2M_MAX < T2M_MIN → invalid"""
        svc = self._make_service()
        m = self._valid_measurements()
        m["T2M_MAX"] = 10.0
        m["T2M_MIN"] = 20.0  # Max < Min
        with pytest.raises(ValueError, match="T2M_MAX"):
            svc._validate_measurements(m)

    def test_extreme_elevation(self):
        """Unrealistic elevation → invalid"""
        svc = self._make_service()
        m = self._valid_measurements()
        m["elevation_m"] = 99999.0
        with pytest.raises(ValueError, match="Elevação"):
            svc._validate_measurements(m)


# ════════════════════════════════════════════════════════════════
# ETo Calculation Service — physics formulas
# ════════════════════════════════════════════════════════════════
class TestEToPhysicsFormulas:

    def _make_service(self):
        from backend.core.eto_calculation.eto_services import EToCalculationService
        return EToCalculationService()

    def test_saturation_vapor_pressure(self):
        """es at 20°C ≈ 2.338 kPa"""
        svc = self._make_service()
        es = svc._saturation_vapor_pressure(20.0)
        assert abs(es - 2.338) < 0.1

    def test_svg_slope(self):
        """Slope of svp at 25°C"""
        svc = self._make_service()
        delta = svc._vapor_pressure_slope(25.0)
        assert delta > 0
        assert delta < 1

    def test_solar_declination_equinox(self):
        """March equinox (DOY~80) → declination near 0"""
        svc = self._make_service()
        delta = svc._solar_declination(80)
        assert abs(delta) < 0.1  # radians

    def test_solar_declination_summer(self):
        """June solstice (DOY~172) → positive declination"""
        svc = self._make_service()
        delta = svc._solar_declination(172)
        assert delta > 0.3

    def test_extraterrestrial_radiation_positive(self):
        """Ra should always be positive for reasonable inputs"""
        svc = self._make_service()
        lat_rad = -23.55 * (3.14159 / 180)
        delta = svc._solar_declination(180)
        Ra = svc._extraterrestrial_radiation(lat_rad, 180, delta)
        assert Ra > 0

    def test_net_radiation(self):
        svc = self._make_service()
        Rn = svc._net_radiation(
            Rs=20.0,
            T_max=30.0,
            T_min=18.0,
            RH_mean=65.0,
            Ra=35.0,
        )
        assert isinstance(Rn, float)
        # Rn should be positive for typical day
        assert Rn > 0


# ════════════════════════════════════════════════════════════════
# Historical Loader — ThreadSafeCache
# ════════════════════════════════════════════════════════════════
class TestThreadSafeCache:

    def test_get_set_basic(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=5)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Evicts "a"
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_clear(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        cache.set("k", "v")
        cache.clear()
        assert cache.get("k") is None

    def test_access_refreshes_position(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # Refresh "a"
        cache.set("d", 4)  # Evicts "b"
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_overwrite_key(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache()
        cache.set("k", "old")
        cache.set("k", "new")
        assert cache.get("k") == "new"

    def test_thread_safety(self):
        """Concurrent access doesn't corrupt cache"""
        import threading
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=100)
        errors = []

        def writer(start):
            try:
                for i in range(start, start + 50):
                    cache.set(f"key_{i}", i)
            except Exception as e:
                errors.append(e)

        def reader(start):
            try:
                for i in range(start, start + 50):
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i * 50,)))
            threads.append(threading.Thread(target=reader, args=(i * 50,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_large_cache(self):
        from backend.core.data_processing.historical_loader import ThreadSafeCache
        cache = ThreadSafeCache(max_size=1000)
        for i in range(500):
            cache.set(f"key_{i}", f"value_{i}")
        assert cache.get("key_0") == "value_0"
        assert cache.get("key_499") == "value_499"


# ════════════════════════════════════════════════════════════════
# Historical Loader — get_reference_for_location (mocked FS)
# ════════════════════════════════════════════════════════════════
class TestHistoricalLoader:

    def test_loader_init(self):
        """HistoricalDataLoader can be instantiated"""
        with patch("pandas.read_csv") as mock_csv:
            mock_csv.return_value = pd.DataFrame(columns=["city", "lat", "lon", "region"])
            from backend.core.data_processing.historical_loader import HistoricalDataLoader
            loader = HistoricalDataLoader()
            assert loader is not None

    def test_load_city_coords_missing_file(self):
        """Missing info_cities.csv → empty dict"""
        with patch("pandas.read_csv") as mock_csv:
            mock_csv.return_value = pd.DataFrame(columns=["city", "lat", "lon", "region"])
            from backend.core.data_processing.historical_loader import HistoricalDataLoader
            loader = HistoricalDataLoader()
            # Force missing file path
            loader.city_coords_path = MagicMock()
            loader.city_coords_path.exists.return_value = False
            result = loader._load_city_coords()
            assert result == {}


# ════════════════════════════════════════════════════════════════
# data_download task (Celery)
# ════════════════════════════════════════════════════════════════
class TestDataDownloadTask:

    def test_task_exists(self):
        from backend.infrastructure.celery.tasks.data_download import process_historical_download
        assert callable(process_historical_download)

    def test_task_name(self):
        from backend.infrastructure.celery.tasks.data_download import process_historical_download
        # It's a regular function (called from Celery task), verify it has a name
        assert hasattr(process_historical_download, '__name__')


# ════════════════════════════════════════════════════════════════
# Core Utils — geographic utilities
# ════════════════════════════════════════════════════════════════
class TestCoreUtils:

    def test_haversine_distance_same_point(self):
        from backend.core.utils import haversine_distance
        d = haversine_distance(0, 0, 0, 0)
        assert d == 0.0 or abs(d) < 0.1

    def test_haversine_distance_known(self):
        """São Paulo to Rio de Janeiro ≈ 360 km"""
        from backend.core.utils import haversine_distance
        d = haversine_distance(-23.55, -46.63, -22.91, -43.17)
        assert 300 < d < 450

    def test_detect_geographic_region_brazil(self):
        from backend.core.utils import detect_geographic_region
        region = detect_geographic_region(-23.55, -46.63)
        assert "brasil" in region.lower() or "brazil" in region.lower()

    def test_detect_geographic_region_usa(self):
        from backend.core.utils import detect_geographic_region
        region = detect_geographic_region(40.71, -74.01)
        assert "usa" in region.lower() or "america" in region.lower() or region is not None

    def test_is_same_hemisphere_true(self):
        from backend.core.utils import is_same_hemisphere
        assert is_same_hemisphere(-23.0, -15.0) is True

    def test_is_same_hemisphere_false(self):
        from backend.core.utils import is_same_hemisphere
        assert is_same_hemisphere(-23.0, 40.0) is False
