"""
Unit Tests - Climate Ensemble & Kalman Filters (data_processing layer)

Tests for the refactored architecture:
- AdaptiveKalmanFilter / SimpleKalmanFilter (kalman_filters.py)
- KalmanApplier (kalman_filters.py)
- ClimateFusion (climate_fusion.py)
- HistoricalDataLoader (historical_loader.py)
- ClimateKalmanEnsemble (climate_ensemble.py - orchestrator)
"""

import time
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from backend.core.data_processing.climate_ensemble import ClimateKalmanEnsemble
from backend.core.data_processing.kalman_filters import (
    AdaptiveKalmanFilter,
    SimpleKalmanFilter,
    KalmanApplier,
)
from backend.core.data_processing.climate_fusion import ClimateFusion
from backend.core.data_processing.historical_loader import HistoricalDataLoader


# ============================================================================
# AdaptiveKalmanFilter
# ============================================================================


class TestAdaptiveKalmanFilter:
    """Tests for AdaptiveKalmanFilter"""

    def test_initialization(self):
        """Test initialization with defaults"""
        kf = AdaptiveKalmanFilter()
        assert kf.normal == 5.0
        assert kf.std == 1.0
        assert kf.estimate == 5.0

    def test_initialization_custom(self):
        """Test initialization with custom values"""
        kf = AdaptiveKalmanFilter(normal=10.0, std=2.0, p01=4.0, p99=16.0)
        assert kf.normal == 10.0
        assert kf.std == 2.0
        assert kf.p01 == 4.0
        assert kf.p99 == 16.0
        assert kf.estimate == 10.0

    def test_minimum_std_enforcement(self):
        """Test that std is enforced to minimum 0.4"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=0.1)
        assert kf.std >= 0.4

    def test_update_with_valid_value(self):
        """Test update with valid measurement"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0)
        result = kf.update(5.5)
        assert isinstance(result, float)
        assert result == pytest.approx(5.3, abs=0.2)

    def test_update_with_nan(self):
        """Test update with NaN returns current estimate"""
        kf = AdaptiveKalmanFilter(normal=5.0)
        result = kf.update(np.nan)
        assert result == 5.0

    def test_outlier_dampening(self):
        """Test that outliers beyond percentile bounds are dampened"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0, p01=2.0, p99=8.0)
        result = kf.update(1.0)
        assert abs(result - 5.0) < abs(1.0 - 5.0)

    def test_adaptive_noise_on_outliers(self):
        """Test that R increases for measurements outside percentile bounds"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0, p01=2.0, p99=8.0)
        kf.update(5.1)
        normal_estimate = kf.estimate

        kf2 = AdaptiveKalmanFilter(normal=5.0, std=1.0, p01=2.0, p99=8.0)
        kf2.update(50.0)
        extreme_estimate = kf2.estimate

        # Extreme outlier should move estimate much less proportionally
        assert abs(extreme_estimate - 5.0) < abs(50.0 - 5.0) * 0.5

    def test_update_batch(self):
        """Test batch update processing"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0)
        values = np.array([5.1, 4.9, 5.2, 5.0, 4.8])
        results = kf.update_batch(values)
        assert len(results) == 5
        assert all(isinstance(r, (float, np.floating)) for r in results)

    def test_update_batch_with_nans(self):
        """Test batch update with NaN values"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0)
        values = np.array([5.1, np.nan, 5.2, np.nan, 4.8])
        results = kf.update_batch(values)
        assert len(results) == 5
        assert not np.isnan(results[0])
        assert not np.isnan(results[2])
        assert not np.isnan(results[4])

    def test_convergence(self):
        """Test that filter converges toward repeated measurements"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0)
        target = 7.0
        for _ in range(50):
            kf.update(target)
        assert abs(kf.estimate - target) < 0.5

    def test_filter_state_attributes(self):
        """Test that filter exposes state as direct attributes"""
        kf = AdaptiveKalmanFilter(normal=5.0, std=1.0)
        assert hasattr(kf, "estimate")
        assert hasattr(kf, "error")
        assert hasattr(kf, "Q")
        assert kf.estimate == 5.0
        assert kf.error > 0
        assert kf.Q > 0


# ============================================================================
# SimpleKalmanFilter
# ============================================================================


class TestSimpleKalmanFilter:
    """Tests for SimpleKalmanFilter"""

    def test_initialization(self):
        """Test initialization"""
        kf = SimpleKalmanFilter(10.0)
        assert kf.estimate == 10.0
        assert kf.error == 1.0
        assert kf.Q == 0.05
        assert kf.R == 0.8

    def test_update(self):
        """Test simple update"""
        kf = SimpleKalmanFilter(5.0)
        result = kf.update(6.0)
        assert isinstance(result, float)
        assert 5.0 < result < 6.0

    def test_update_with_nan(self):
        """Test update with NaN"""
        kf = SimpleKalmanFilter(5.0)
        result = kf.update(np.nan)
        assert result == 5.0

    def test_update_batch(self):
        """Test batch processing"""
        kf = SimpleKalmanFilter(5.0)
        values = np.array([5.0, 6.0, 7.0])
        results = kf.update_batch(values)
        assert len(results) == 3
        assert all(isinstance(r, (float, np.floating)) for r in results)

    def test_convergence(self):
        """Test convergence toward constant signal"""
        kf = SimpleKalmanFilter(3.0)
        for _ in range(100):
            kf.update(10.0)
        assert abs(kf.estimate - 10.0) < 1.0


# ============================================================================
# KalmanApplier
# ============================================================================


class TestKalmanApplier:
    """Tests for KalmanApplier static methods"""

    def _make_df(self, n_days=10):
        """Helper to create a test DataFrame"""
        dates = pd.date_range("2023-01-01", periods=n_days)
        return pd.DataFrame(
            {
                "date": dates,
                "T2M_MAX": np.random.uniform(25, 35, n_days),
                "T2M_MIN": np.random.uniform(10, 20, n_days),
                "T2M": np.random.uniform(18, 28, n_days),
                "RH2M": np.random.uniform(40, 80, n_days),
                "WS2M": np.random.uniform(1, 5, n_days),
                "ALLSKY_SFC_SW_DWN": np.random.uniform(15, 30, n_days),
                "PRECTOTCORR": np.random.exponential(2, n_days),
                "et0_mm": np.random.uniform(2, 8, n_days),
            },
        )

    def test_apply_precipitation_filter_without_reference(self):
        """Test precipitation filter without local reference (simple clip)"""
        df = self._make_df()
        df.loc[df.index[0], "PRECTOTCORR"] = -5.0
        df.loc[df.index[1], "PRECTOTCORR"] = 2000.0

        result = KalmanApplier.apply_precipitation_filter(df, ref=None)
        assert "PRECTOTCORR" in result.columns
        assert result["PRECTOTCORR"].min() >= 0
        assert result["PRECTOTCORR"].max() <= 1800

    def test_apply_precipitation_filter_with_reference(self):
        """Test precipitation filter with local reference (adaptive Kalman)"""
        df = self._make_df()
        ref = {
            "precip_normals": {1: 5.0},
            "precip_stds": {1: 2.0},
            "precip_p01": {1: 0.0},
            "precip_p99": {1: 15.0},
        }
        result = KalmanApplier.apply_precipitation_filter(df, ref=ref)
        assert "PRECTOTCORR" in result.columns
        assert result["PRECTOTCORR"].min() >= 0

    def test_apply_eto_filter_without_reference(self):
        """Test ETo filter without reference (SimpleKalmanFilter fallback)"""
        df = self._make_df()
        result = KalmanApplier.apply_eto_filter(df, ref=None)
        assert "eto_final" in result.columns
        assert "eto_evaonline" in result.columns
        assert result["eto_final"].notna().all()

    def test_apply_eto_filter_with_reference(self):
        """Test ETo filter with local reference (adaptive mode)"""
        df = self._make_df()
        ref = {
            "eto_normals": {1: 4.0},
            "eto_stds": {1: 1.0},
            "eto_p01": {1: 1.0},
            "eto_p99": {1: 8.0},
        }
        result = KalmanApplier.apply_eto_filter(df, ref=ref, lat=-22.0)
        assert "eto_final" in result.columns
        assert "anomaly_eto_mm" in result.columns
        assert "eto_evaonline" in result.columns


# ============================================================================
# ClimateFusion
# ============================================================================


class TestClimateFusion:
    """Tests for ClimateFusion"""

    def setup_method(self):
        self.fusion = ClimateFusion()

    def _make_multi_source_df(self, n_days=5):
        """Helper to create multi-source DataFrame"""
        dates = pd.date_range("2023-01-01", periods=n_days)
        rows = []
        for source in ["nasa_power", "openmeteo_archive"]:
            for d in dates:
                rows.append(
                    {
                        "date": d,
                        "source": source,
                        "T2M_MAX": 25 + np.random.normal(0, 2),
                        "T2M_MIN": 15 + np.random.normal(0, 1),
                        "T2M": 20 + np.random.normal(0, 1.5),
                        "RH2M": 60 + np.random.normal(0, 5),
                        "WS2M": 3 + np.random.normal(0, 0.5),
                        "ALLSKY_SFC_SW_DWN": 20 + np.random.normal(0, 3),
                        "PRECTOTCORR": max(0, np.random.exponential(2)),
                    }
                )
        return pd.DataFrame(rows)

    def test_initialization(self):
        """Test ClimateFusion initialization"""
        assert hasattr(self.fusion, "quality_metrics")
        assert hasattr(self.fusion, "source_health")

    def test_detect_region_with_priority_usa(self):
        """Test USA region detection"""
        info = self.fusion._detect_region_with_priority(40.0, -100.0)
        assert info["name"] == "USA"

    def test_detect_region_with_priority_global(self):
        """Test global/non-USA region detection"""
        info = self.fusion._detect_region_with_priority(-23.0, -46.0)
        assert info["name"] in ("GLOBAL", "NORDIC", "USA")

    def test_validate_climate_data_no_exception(self):
        """Test validation doesn't raise for reasonable data"""
        df = pd.DataFrame({"T2M": [20.0, 25.0], "RH2M": [50.0, 60.0]})
        self.fusion._validate_climate_data(df, "test_source")

    def test_fuse_multi_source_empty_input(self):
        """Test fusion with empty DataFrame"""
        result = self.fusion.fuse_multi_source(pd.DataFrame(), 0.0, 0.0)
        assert isinstance(result, pd.DataFrame)

    def test_fuse_multi_source_basic(self):
        """Test basic multi-source fusion"""
        df = self._make_multi_source_df()
        result = self.fusion.fuse_multi_source(df, -23.0, -46.0)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "T2M" in result.columns
            assert "RH2M" in result.columns


# ============================================================================
# HistoricalDataLoader
# ============================================================================


class TestHistoricalDataLoader:
    """Tests for HistoricalDataLoader"""

    def setup_method(self):
        self.loader = HistoricalDataLoader()

    def test_initialization(self):
        """Test loader initialization"""
        assert hasattr(self.loader, "_cache")
        assert hasattr(self.loader, "city_coords")

    def test_load_city_coords_success(self):
        """Test successful loading of city coordinates"""
        with patch.object(
            HistoricalDataLoader,
            "_load_city_coords",
            return_value={
                "SaoPaulo": (-23.55, -46.63, "brasil"),
                "RioDeJaneiro": (-22.90, -43.17, "brasil"),
            },
        ):
            loader = HistoricalDataLoader()
            loader.city_coords = loader._load_city_coords()
            assert "SaoPaulo" in loader.city_coords
            assert loader.city_coords["SaoPaulo"][0] == -23.55

    def test_get_reference_for_location_with_cache(self):
        """Test cache hit returns cached data"""
        cache_key = (-23.55, -46.63)
        self.loader._cache.set(cache_key, {"city": "SaoPaulo", "test": True})

        has_ref, ref = self.loader.get_reference_for_location(-23.55, -46.63)
        assert has_ref is True
        assert ref["city"] == "SaoPaulo"

    def test_get_reference_for_location_no_match(self):
        """Test when no nearby city is found"""
        has_ref, ref = self.loader.get_reference_for_location(0.0, 0.0)
        assert isinstance(has_ref, bool)
        if not has_ref:
            assert ref is None


# ============================================================================
# ClimateKalmanEnsemble (Orchestrator)
# ============================================================================


class TestClimateKalmanEnsemble:
    """Tests for ClimateKalmanEnsemble orchestrator"""

    def setup_method(self):
        self.ensemble = ClimateKalmanEnsemble()

    def test_initialization(self):
        """Test orchestrator initialization"""
        assert isinstance(self.ensemble.loader, HistoricalDataLoader)
        assert isinstance(self.ensemble.fusion, ClimateFusion)
        assert isinstance(self.ensemble.kalman, KalmanApplier)

    def test_process_empty_dataframe(self):
        """Test process with empty input returns empty DataFrame"""
        result = self.ensemble.process(pd.DataFrame(), -23.0, -46.0)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_process_basic(self):
        """Test basic processing pipeline"""
        dates = pd.date_range("2023-01-01", periods=5)
        rows = []
        for source in ["nasa_power", "openmeteo_archive"]:
            for d in dates:
                rows.append(
                    {
                        "date": d,
                        "source": source,
                        "T2M_MAX": 28 + np.random.normal(0, 1),
                        "T2M_MIN": 18 + np.random.normal(0, 1),
                        "T2M": 23 + np.random.normal(0, 1),
                        "RH2M": 65 + np.random.normal(0, 3),
                        "WS2M": 2.5 + np.random.normal(0, 0.3),
                        "ALLSKY_SFC_SW_DWN": 22 + np.random.normal(0, 2),
                        "PRECTOTCORR": max(0, np.random.exponential(1.5)),
                    }
                )
        df = pd.DataFrame(rows)

        result = self.ensemble.process(df, -23.55, -46.63)
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "fusion_mode" in result.columns
            assert result["fusion_mode"].iloc[0] in (
                "high_precision",
                "global_fallback",
            )


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the full pipeline"""

    def test_full_fusion_pipeline(self):
        """Test complete fusion pipeline end-to-end"""
        dates = pd.date_range("2023-01-01", periods=5)
        rows = []
        for source in ["nasa_power", "openmeteo_archive"]:
            for d in dates:
                rows.append(
                    {
                        "date": d,
                        "source": source,
                        "T2M_MAX": 25 + np.random.normal(0, 1),
                        "T2M_MIN": 15 + np.random.normal(0, 1),
                        "T2M": 20 + np.random.normal(0, 1),
                        "RH2M": 60 + np.random.normal(0, 3),
                        "WS2M": 2.0 + np.random.normal(0, 0.3),
                        "ALLSKY_SFC_SW_DWN": 20 + np.random.normal(0, 2),
                        "PRECTOTCORR": max(0, np.random.exponential(1)),
                    }
                )
        df = pd.DataFrame(rows)

        ensemble = ClimateKalmanEnsemble()
        result = ensemble.process(df, -23.55, -46.63)

        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "fusion_mode" in result.columns
            climate_cols = ["T2M", "RH2M", "PRECTOTCORR"]
            for col in climate_cols:
                if col in result.columns:
                    assert result[col].notna().any()


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance tests"""

    def test_multi_source_performance(self):
        """Test performance with large multi-source dataset"""
        dates = pd.date_range("2024-01-01", periods=30)
        sources = ["nasa_power", "openmeteo_archive"]

        rows = []
        for source in sources:
            for d in dates:
                rows.append(
                    {
                        "date": d,
                        "source": source,
                        "T2M_MAX": 25 + np.random.normal(0, 3),
                        "T2M_MIN": 15 + np.random.normal(0, 2),
                        "T2M": 20 + np.random.normal(0, 2.5),
                        "RH2M": 60 + np.random.normal(0, 10),
                        "WS2M": 3 + np.random.exponential(1),
                        "ALLSKY_SFC_SW_DWN": 20 + np.random.normal(0, 5),
                        "PRECTOTCORR": max(0, np.random.exponential(2)),
                    }
                )

        df = pd.DataFrame(rows)

        start = time.time()
        ensemble = ClimateKalmanEnsemble()
        result = ensemble.process(df, lat=-23.55, lon=-46.63)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Pipeline too slow: {elapsed:.2f}s"
        assert isinstance(result, pd.DataFrame)
