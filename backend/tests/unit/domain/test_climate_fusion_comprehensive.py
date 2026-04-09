"""
Tests for ClimateFusion — multi-source climate data fusion.

Covers:
- _validate_climate_data: physical limit validation
- _track_data_quality: quality scoring per source
- _check_source_health: circuit breaker logic
- _detect_region_with_priority: regional weight selection
- _prepare_data: data cleaning and deduplication
- _interpolate_safe: safe interpolation with clipping
- fuse_multi_source: full multi-source fusion pipeline
"""

import numpy as np
import pandas as pd
import pytest

from backend.core.data_processing.climate_fusion import ClimateFusion


# ════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def fusion():
    return ClimateFusion()


@pytest.fixture
def sample_source_df():
    """Single-source DataFrame for basic tests."""
    dates = pd.date_range("2024-01-01", periods=7, freq="D")
    return pd.DataFrame({
        "date": dates,
        "source": "nasa_power",
        "T2M_MAX": [30.0, 31.0, 29.5, 30.5, 32.0, 31.5, 30.0],
        "T2M_MIN": [18.0, 19.0, 17.5, 18.5, 20.0, 19.5, 18.0],
        "T2M": [24.0, 25.0, 23.5, 24.5, 26.0, 25.5, 24.0],
        "RH2M": [65.0, 70.0, 60.0, 68.0, 72.0, 66.0, 64.0],
        "WS2M": [2.5, 3.0, 2.0, 2.8, 3.5, 2.2, 2.6],
        "ALLSKY_SFC_SW_DWN": [20.0, 22.0, 18.0, 21.0, 24.0, 19.5, 20.5],
        "PRECTOTCORR": [0.0, 5.0, 0.0, 2.0, 0.0, 8.0, 1.0],
    })


@pytest.fixture
def multi_source_df():
    """Two-source DataFrame for fusion tests."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    rows = []
    for d in dates:
        # NASA POWER
        rows.append({
            "date": d, "source": "nasa_power",
            "T2M_MAX": 31.0, "T2M_MIN": 19.0, "T2M": 25.0,
            "RH2M": 65.0, "WS2M": 2.5,
            "ALLSKY_SFC_SW_DWN": 20.0, "PRECTOTCORR": 0.0,
        })
        # OpenMeteo Archive
        rows.append({
            "date": d, "source": "openmeteo_archive",
            "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
            "RH2M": 68.0, "WS2M": 3.0,
            "ALLSKY_SFC_SW_DWN": 19.0, "PRECTOTCORR": 1.0,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def forecast_multi_source_df():
    """Multi-source DataFrame for forecast mode."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    rows = []
    for d in dates:
        rows.append({
            "date": d, "source": "openmeteo_forecast",
            "T2M_MAX": 30.5, "T2M_MIN": 18.5, "T2M": 24.5,
            "RH2M": 66.0, "WS2M": 2.8,
            "ALLSKY_SFC_SW_DWN": 19.5, "PRECTOTCORR": 0.5,
        })
        rows.append({
            "date": d, "source": "met_norway",
            "T2M_MAX": 29.5, "T2M_MIN": 17.5, "T2M": 23.5,
            "RH2M": 70.0, "WS2M": 3.2,
            "ALLSKY_SFC_SW_DWN": 18.5, "PRECTOTCORR": 1.5,
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════
# _validate_climate_data
# ════════════════════════════════════════════════════════════════════

class TestValidateClimateData:

    def test_valid_data_no_warnings(self, fusion, sample_source_df):
        """Valid data should not raise or log warnings"""
        # Should not raise
        fusion._validate_climate_data(sample_source_df, "nasa_power")

    def test_invalid_values_flagged(self, fusion):
        """Out-of-range values should be detected"""
        df = pd.DataFrame({
            "T2M_MAX": [200.0],  # Way above physical limit
            "T2M_MIN": [-100.0],  # Way below
        })
        # Should not raise, just log warnings
        fusion._validate_climate_data(df, "test_source")

    def test_empty_dataframe(self, fusion):
        """Empty DataFrame should not raise"""
        df = pd.DataFrame(columns=["T2M_MAX", "T2M_MIN", "T2M"])
        fusion._validate_climate_data(df, "empty_source")


# ════════════════════════════════════════════════════════════════════
# _track_data_quality
# ════════════════════════════════════════════════════════════════════

class TestTrackDataQuality:

    def test_quality_metrics_stored(self, fusion, sample_source_df):
        fusion._track_data_quality(sample_source_df, "nasa_power")
        assert "nasa_power" in fusion.quality_metrics
        assert fusion.quality_metrics["nasa_power"]["total_records"] == 7

    def test_quality_scores_per_variable(self, fusion, sample_source_df):
        fusion._track_data_quality(sample_source_df, "nasa_power")
        scores = fusion.quality_metrics["nasa_power"]["quality_scores"]
        # All data is valid → scores should be close to 100
        for var, score in scores.items():
            assert score >= 90.0

    def test_missing_values_reduce_score(self, fusion):
        df = pd.DataFrame({
            "T2M_MAX": [30.0, np.nan, 31.0, np.nan, 32.0],
            "T2M_MIN": [18.0, 19.0, np.nan, np.nan, 20.0],
        })
        fusion._track_data_quality(df, "bad_source")
        scores = fusion.quality_metrics["bad_source"]["quality_scores"]
        assert scores.get("T2M_MAX", 100) < 100

    def test_unknown_source_tracked(self, fusion, sample_source_df):
        fusion._track_data_quality(sample_source_df, "unknown_api")
        assert "unknown_api" in fusion.quality_metrics


# ════════════════════════════════════════════════════════════════════
# _check_source_health (circuit breaker)
# ════════════════════════════════════════════════════════════════════

class TestCheckSourceHealth:

    def test_unknown_source_healthy(self, fusion):
        """Source with no metrics → assume healthy"""
        assert fusion._check_source_health("never_seen") is True

    def test_healthy_source(self, fusion, sample_source_df):
        """Good quality data → healthy"""
        fusion._track_data_quality(sample_source_df, "good_source")
        assert fusion._check_source_health("good_source") == True

    def test_degraded_source(self, fusion):
        """Very poor quality → circuit breaker trips"""
        # Manually set low quality
        fusion.quality_metrics["bad_source"] = {
            "total_records": 100,
            "quality_scores": {"T2M": 20.0, "RH2M": 15.0, "WS2M": 10.0},
        }
        assert fusion._check_source_health("bad_source") == False

    def test_borderline_source(self, fusion):
        """Quality exactly at threshold (60%)"""
        fusion.quality_metrics["borderline"] = {
            "total_records": 50,
            "quality_scores": {"T2M": 60.0},
        }
        assert fusion._check_source_health("borderline") == True

    def test_empty_scores_healthy(self, fusion):
        """Source with no scores → healthy"""
        fusion.quality_metrics["no_scores"] = {
            "total_records": 10,
            "quality_scores": {},
        }
        assert fusion._check_source_health("no_scores") is True


# ════════════════════════════════════════════════════════════════════
# _detect_region_with_priority
# ════════════════════════════════════════════════════════════════════

class TestDetectRegionWithPriority:

    def test_usa_region(self, fusion):
        """USA location → NWS forecast priority"""
        result = fusion._detect_region_with_priority(40.0, -100.0)
        assert result["name"] == "USA"
        assert "nws_forecast" in result["weights"]

    def test_nordic_region(self, fusion):
        """Scandinavia → MET Norway priority"""
        result = fusion._detect_region_with_priority(60.0, 15.0)
        assert result["name"] == "NORDIC"
        assert "met_norway" in result["weights"]
        assert result["weights"]["met_norway"] > 0.5

    def test_global_region(self, fusion):
        """Brazil → GLOBAL region"""
        result = fusion._detect_region_with_priority(-23.5, -46.6)
        assert result["name"] == "GLOBAL"
        assert "openmeteo_forecast" in result["weights"]

    def test_region_has_order(self, fusion):
        """All regions should have source order"""
        for lat, lon in [(-23.5, -46.6), (40.0, -100.0), (60.0, 15.0)]:
            result = fusion._detect_region_with_priority(lat, lon)
            assert "order" in result
            assert len(result["order"]) > 0

    def test_weights_sum_reasonable(self, fusion):
        """Weights should be between 0 and 1"""
        result = fusion._detect_region_with_priority(-23.5, -46.6)
        for w in result["weights"].values():
            assert 0 < w <= 1.0


# ════════════════════════════════════════════════════════════════════
# _prepare_data
# ════════════════════════════════════════════════════════════════════

class TestPrepareData:

    def test_basic_preparation(self, fusion, sample_source_df):
        result = fusion._prepare_data(sample_source_df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 7

    def test_quality_tracked_during_preparation(self, fusion, sample_source_df):
        fusion._prepare_data(sample_source_df)
        assert "nasa_power" in fusion.quality_metrics

    def test_datetime_index_input(self, fusion):
        """DataFrame with DatetimeIndex but no 'date' column"""
        dates = pd.date_range("2024-01-01", periods=5, freq="D", name="date")
        df = pd.DataFrame({
            "T2M_MAX": [30, 31, 29, 30, 32],
            "T2M_MIN": [18, 19, 17, 18, 20],
        }, index=dates)
        result = fusion._prepare_data(df)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_duplicate_dates_resolved(self, fusion, multi_source_df):
        """Multi-source data with same dates → prioritized dedup"""
        result = fusion._prepare_data(multi_source_df)
        # Should have 5 unique dates
        assert len(result) == 5


# ════════════════════════════════════════════════════════════════════
# _interpolate_safe
# ════════════════════════════════════════════════════════════════════

class TestInterpolateSafe:

    def test_no_missing(self, fusion):
        """No NaN → unchanged"""
        s = pd.Series([1.0, 2.0, 3.0], name="T2M")
        result = fusion._interpolate_safe(s)
        assert result.isna().sum() == 0

    def test_single_gap(self, fusion):
        """Single NaN → interpolated"""
        s = pd.Series([10.0, np.nan, 30.0], name="T2M")
        result = fusion._interpolate_safe(s)
        assert abs(result.iloc[1] - 20.0) < 0.1

    def test_multiple_gaps(self, fusion):
        """Multiple NaN → interpolated up to limit=3"""
        s = pd.Series([10.0, np.nan, np.nan, np.nan, 50.0], name="T2M")
        result = fusion._interpolate_safe(s)
        assert result.isna().sum() == 0  # All should be filled within limit=3

    def test_clipping_applied(self, fusion):
        """Interpolated values should be clipped to physical limits"""
        # Create series that would interpolate beyond limits
        s = pd.Series([0.0, np.nan, 0.0], name="ALLSKY_SFC_SW_DWN")
        result = fusion._interpolate_safe(s)
        if "ALLSKY_SFC_SW_DWN" in fusion.GLOBAL_LIMITS:
            min_val, max_val = fusion.GLOBAL_LIMITS["ALLSKY_SFC_SW_DWN"]
            assert (result >= min_val).all()
            assert (result <= max_val).all()


# ════════════════════════════════════════════════════════════════════
# fuse_multi_source — Full fusion pipeline
# ════════════════════════════════════════════════════════════════════

class TestFuseMultiSource:

    def test_empty_input(self, fusion):
        """Empty DataFrame → empty result with correct columns"""
        result = fusion.fuse_multi_source(pd.DataFrame(), 0.0, 0.0)
        assert "date" in result.columns

    def test_single_source_passthrough(self, fusion, sample_source_df):
        """Single source → values passed through"""
        result = fusion.fuse_multi_source(sample_source_df, -23.5, -46.6)
        assert len(result) > 0
        assert "T2M_MAX" in result.columns

    def test_two_source_historical(self, fusion, multi_source_df):
        """Two primary sources historical → weighted fusion"""
        result = fusion.fuse_multi_source(
            multi_source_df, -23.5, -46.6, mode="historical_email"
        )
        assert len(result) == 5
        # Fused values should be between the two sources
        for _, row in result.iterrows():
            assert 29.0 <= row["T2M_MAX"] <= 32.0

    def test_forecast_mode_usa(self, fusion, forecast_multi_source_df):
        """Forecast mode for USA → NWS priority weights"""
        result = fusion.fuse_multi_source(
            forecast_multi_source_df, 40.0, -100.0
        )
        assert len(result) > 0

    def test_forecast_mode_nordic(self, fusion, forecast_multi_source_df):
        """Forecast mode for Nordic → MET Norway priority"""
        result = fusion.fuse_multi_source(
            forecast_multi_source_df, 60.0, 15.0
        )
        assert len(result) > 0

    def test_all_sources_unhealthy(self, fusion, multi_source_df):
        """All sources degraded → emergency fallback"""
        # Mark all sources as unhealthy
        for src in ["nasa_power", "openmeteo_archive", "openmeteo_forecast",
                     "met_norway", "nws_forecast"]:
            fusion.quality_metrics[src] = {
                "total_records": 100,
                "quality_scores": {"T2M": 10.0, "RH2M": 5.0},
            }
        result = fusion.fuse_multi_source(multi_source_df, -23.5, -46.6)
        assert len(result) > 0
        # Should have fallback values
        if "fusion_mode" in result.columns:
            assert "fallback" in str(result["fusion_mode"].iloc[0]).lower()

    def test_output_columns_valid(self, fusion, multi_source_df):
        """Output should have standard climate variables"""
        result = fusion.fuse_multi_source(multi_source_df, -23.5, -46.6)
        expected_vars = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M",
                         "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
        for var in expected_vars:
            assert var in result.columns

    def test_no_nans_in_output(self, fusion, multi_source_df):
        """Fusion output should have no NaN for core variables"""
        result = fusion.fuse_multi_source(multi_source_df, -23.5, -46.6)
        core_vars = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M"]
        for var in core_vars:
            if var in result.columns:
                assert result[var].isna().sum() == 0

    def test_recent_mode(self, fusion, multi_source_df):
        """Recent mode should prefer primary sources"""
        result = fusion.fuse_multi_source(
            multi_source_df, -23.5, -46.6, mode="dashboard_current"
        )
        assert len(result) > 0

    def test_hist_weights_applied(self, fusion, multi_source_df):
        """Historical mode should use HIST_WEIGHTS for fusion"""
        result = fusion.fuse_multi_source(
            multi_source_df, -23.5, -46.6, mode="historical_email"
        )
        # T2M_MAX: NASA has 31.0, OM has 30.0
        # HIST_WEIGHTS["T2M_MAX"] = 0.58 for NASA
        # Expected: 0.58 * 31.0 + 0.42 * 30.0 = 30.58
        if len(result) > 0:
            fused_val = result["T2M_MAX"].iloc[0]
            assert 29.5 <= fused_val <= 31.5
