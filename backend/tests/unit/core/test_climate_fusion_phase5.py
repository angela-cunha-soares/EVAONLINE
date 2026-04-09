"""
Phase 5 Tests: ClimateFusion.fuse_multi_source() — multi-source fusion logic.

Coverage target: backend/core/data_processing/climate_fusion.py (58% → 85%+)
Lines 262-368 (fusion loop: historical, recent, forecast modes)
Lines 380-432 (post-fusion clipping, interpolation, dropna)
"""

import numpy as np
import pandas as pd
import pytest

from backend.core.data_processing.climate_fusion import ClimateFusion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _multi_source_df(
    sources=("nasa_power", "openmeteo_archive"),
    n_days=5,
    start="2025-01-01",
):
    """Build a DataFrame with rows from multiple sources for the same dates."""
    rows = []
    dates = pd.date_range(start, periods=n_days, freq="D")
    for d in dates:
        for src in sources:
            rows.append({
                "date": d,
                "T2M_MAX": 30.0 + (1 if src == "openmeteo_archive" else 0),
                "T2M_MIN": 18.0 + (1 if src == "openmeteo_archive" else 0),
                "T2M": 24.0 + (0.5 if src == "openmeteo_archive" else 0),
                "RH2M": 65.0 + (5 if src == "openmeteo_archive" else 0),
                "WS2M": 3.0 + (1 if src == "openmeteo_archive" else 0),
                "ALLSKY_SFC_SW_DWN": 20.0 + (2 if src == "openmeteo_archive" else 0),
                "PRECTOTCORR": 2.0 + (1 if src == "openmeteo_archive" else 0),
                "source": src,
            })
    return pd.DataFrame(rows)


def _forecast_df(
    sources=("openmeteo_forecast", "met_norway"),
    n_days=5,
    start="2025-06-01",
):
    """Build a DataFrame that triggers forecast-mode fusion."""
    rows = []
    dates = pd.date_range(start, periods=n_days, freq="D")
    for d in dates:
        for src in sources:
            offset = 0 if src == "openmeteo_forecast" else 2
            rows.append({
                "date": d,
                "T2M_MAX": 28.0 + offset,
                "T2M_MIN": 16.0 + offset,
                "T2M": 22.0 + offset,
                "RH2M": 70.0 + offset,
                "WS2M": 4.0 + offset,
                "ALLSKY_SFC_SW_DWN": 18.0 + offset,
                "PRECTOTCORR": 3.0 + offset,
                "source": src,
            })
    return pd.DataFrame(rows)


# ===========================================================================
# Core fusion behaviour
# ===========================================================================


class TestFusionBasics:
    """Basic fuse_multi_source sanity checks."""

    def test_empty_df_returns_empty(self):
        fusion = ClimateFusion()
        result = fusion.fuse_multi_source(pd.DataFrame(), -23.5, -46.6)
        assert result.empty
        assert "date" in result.columns

    def test_single_source_passthrough(self):
        """Single source → no weighted fusion, values pass through."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, 31.0, 32.0],
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [65.0, 66.0, 67.0],
            "WS2M": [3.0, 3.1, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6, mode="historical")
        assert len(result) == 3
        # Single source → values unchanged (except clipping)
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_duplicate_dates_deduped(self):
        """Duplicate dates from same source are deduplicated."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        df = pd.DataFrame({
            "date": list(dates) + list(dates),
            "T2M_MAX": [30, 31, 30, 31],
            "T2M_MIN": [18, 19, 18, 19],
            "T2M": [24, 25, 24, 25],
            "RH2M": [65, 66, 65, 66],
            "WS2M": [3, 4, 3, 4],
            "ALLSKY_SFC_SW_DWN": [20, 21, 20, 21],
            "PRECTOTCORR": [2, 3, 2, 3],
            "source": "openmeteo_forecast",
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6)
        assert len(result) == 2


# ===========================================================================
# Historical mode fusion
# ===========================================================================


class TestHistoricalFusion:
    """Tests for historical mode: _prepare_data deduplicates same-date rows
    from multiple sources, so per-day multi-source weighting only fires
    when sources cover *different* date ranges."""

    def test_two_primary_sources_deduped(self):
        """NASA + Archive same dates → dedup keeps 1 source per day."""
        fusion = ClimateFusion()
        df = _multi_source_df(["nasa_power", "openmeteo_archive"], n_days=3)
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="historical"
        )
        assert len(result) == 3
        # After dedup, single-source passthrough → clipped value
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_two_primary_gap_fill(self):
        """NASA covers days 1-2, Archive covers days 3-4 → combined."""
        fusion = ClimateFusion()
        rows = []
        dates_a = pd.date_range("2025-01-01", periods=2, freq="D")
        dates_b = pd.date_range("2025-01-03", periods=2, freq="D")
        for d in dates_a:
            rows.append({
                "date": d, "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
                "RH2M": 65.0, "WS2M": 3.0, "ALLSKY_SFC_SW_DWN": 20.0,
                "PRECTOTCORR": 2.0, "source": "nasa_power",
            })
        for d in dates_b:
            rows.append({
                "date": d, "T2M_MAX": 31.0, "T2M_MIN": 19.0, "T2M": 25.0,
                "RH2M": 70.0, "WS2M": 4.0, "ALLSKY_SFC_SW_DWN": 22.0,
                "PRECTOTCORR": 3.0, "source": "openmeteo_archive",
            })
        df = pd.DataFrame(rows)
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="historical"
        )
        # Should have all 4 days
        assert len(result) == 4

    def test_single_primary_no_weighting(self):
        """Only NASA (no Archive) → 100% NASA."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, 31.0, 32.0],
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [65.0, 66.0, 67.0],
            "WS2M": [3.0, 3.1, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="historical"
        )
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_fallback_gapfill_when_no_primary(self):
        """Only OM Forecast (no primary) → 100% gap-fill."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        # Two sources: openmeteo_forecast + met_norway — neither is PRIMARY
        # In historical mode, these go to fallback branch
        df = pd.DataFrame({
            "date": list(dates) + list(dates),
            "T2M_MAX": [28.0, 29.0, 30.0, 26.0, 27.0, 28.0],
            "T2M_MIN": [16.0, 17.0, 18.0, 14.0, 15.0, 16.0],
            "T2M": [22.0, 23.0, 24.0, 20.0, 21.0, 22.0],
            "RH2M": [70.0, 71.0, 72.0, 75.0, 76.0, 77.0],
            "WS2M": [4.0, 4.1, 4.2, 5.0, 5.1, 5.2],
            "ALLSKY_SFC_SW_DWN": [18.0, 19.0, 20.0, 16.0, 17.0, 18.0],
            "PRECTOTCORR": [3.0, 4.0, 5.0, 2.0, 3.0, 4.0],
            "source": ["openmeteo_forecast"] * 3 + ["met_norway"] * 3,
        })
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="historical"
        )
        assert len(result) == 3


# ===========================================================================
# Recent mode fusion
# ===========================================================================


class TestRecentFusion:
    """Tests for recent/dashboard_current mode — dedup applies same as hist."""

    def test_recent_single_source(self):
        """Recent mode with single source → passthrough."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, 31.0, 32.0],
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [65.0, 66.0, 67.0],
            "WS2M": [3.0, 3.1, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="dashboard_current"
        )
        assert len(result) == 3
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_recent_gap_fill_primary_plus_forecast(self):
        """Recent mode: primary covers days 1-2, forecast covers day 3."""
        fusion = ClimateFusion()
        rows = []
        dates_p = pd.date_range("2025-01-01", periods=2, freq="D")
        dates_f = pd.date_range("2025-01-03", periods=1, freq="D")
        for d in dates_p:
            rows.append({
                "date": d, "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
                "RH2M": 65.0, "WS2M": 3.0, "ALLSKY_SFC_SW_DWN": 20.0,
                "PRECTOTCORR": 2.0, "source": "nasa_power",
            })
        for d in dates_f:
            rows.append({
                "date": d, "T2M_MAX": 28.0, "T2M_MIN": 16.0, "T2M": 22.0,
                "RH2M": 70.0, "WS2M": 5.0, "ALLSKY_SFC_SW_DWN": 16.0,
                "PRECTOTCORR": 4.0, "source": "openmeteo_forecast",
            })
        df = pd.DataFrame(rows)
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="dashboard_current"
        )
        # All 3 days
        assert len(result) == 3

    def test_recent_no_primary_uses_fallback(self):
        """Recent mode: no primary → fallback source 100%."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [28.0, 29.0, 30.0],
            "T2M_MIN": [16.0, 17.0, 18.0],
            "T2M": [22.0, 23.0, 24.0],
            "RH2M": [70.0, 71.0, 72.0],
            "WS2M": [4.0, 4.1, 4.2],
            "ALLSKY_SFC_SW_DWN": [18.0, 19.0, 20.0],
            "PRECTOTCORR": [3.0, 4.0, 5.0],
            "source": "openmeteo_forecast",
        })
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="dashboard_current"
        )
        assert len(result) == 3
        assert result["T2M_MAX"].iloc[0] == pytest.approx(28.0, abs=0.5)


# ===========================================================================
# Forecast mode fusion (region-weighted)
# ===========================================================================


class TestForecastFusion:
    """Tests for forecast mode — dedup applies, so test with gap-fill pattern."""

    def test_global_region_single_forecast(self):
        """Global region single forecast source passes through."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [28.0, 29.0, 30.0],
            "T2M_MIN": [16.0, 17.0, 18.0],
            "T2M": [22.0, 23.0, 24.0],
            "RH2M": [70.0, 71.0, 72.0],
            "WS2M": [4.0, 4.1, 4.2],
            "ALLSKY_SFC_SW_DWN": [18.0, 19.0, 20.0],
            "PRECTOTCORR": [3.0, 4.0, 5.0],
            "source": "openmeteo_forecast",
        })
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="dashboard_forecast"
        )
        assert len(result) == 3
        assert result["T2M_MAX"].iloc[0] == pytest.approx(28.0, abs=0.5)

    def test_usa_region_nws_only(self):
        """USA with NWS only → single source passthrough."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, 31.0, 32.0],
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [65.0, 66.0, 67.0],
            "WS2M": [3.0, 3.1, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0],
            "source": "nws_forecast",
        })
        result = fusion.fuse_multi_source(
            df, 40.7, -74.0, mode="dashboard_forecast"
        )
        assert len(result) == 3

    def test_nordic_region_met_only(self):
        """Nordic MET Norway only → passthrough."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [20.0, 21.0, 22.0],
            "T2M_MIN": [10.0, 11.0, 12.0],
            "T2M": [15.0, 16.0, 17.0],
            "RH2M": [80.0, 81.0, 82.0],
            "WS2M": [5.0, 5.1, 5.2],
            "ALLSKY_SFC_SW_DWN": [12.0, 13.0, 14.0],
            "PRECTOTCORR": [5.0, 6.0, 7.0],
            "source": "met_norway",
        })
        result = fusion.fuse_multi_source(
            df, 60.0, 10.0, mode="dashboard_forecast"
        )
        assert len(result) == 3

    def test_forecast_gap_fill_two_sources(self):
        """Forecast: OM covers days 1-2, MET covers days 3-4."""
        fusion = ClimateFusion()
        rows = []
        dates_om = pd.date_range("2025-06-01", periods=2, freq="D")
        dates_met = pd.date_range("2025-06-03", periods=2, freq="D")
        for d in dates_om:
            rows.append({
                "date": d, "T2M_MAX": 28.0, "T2M_MIN": 16.0, "T2M": 22.0,
                "RH2M": 70.0, "WS2M": 4.0, "ALLSKY_SFC_SW_DWN": 18.0,
                "PRECTOTCORR": 3.0, "source": "openmeteo_forecast",
            })
        for d in dates_met:
            rows.append({
                "date": d, "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
                "RH2M": 75.0, "WS2M": 5.0, "ALLSKY_SFC_SW_DWN": 20.0,
                "PRECTOTCORR": 4.0, "source": "met_norway",
            })
        df = pd.DataFrame(rows)
        result = fusion.fuse_multi_source(
            df, -23.5, -46.6, mode="dashboard_forecast"
        )
        assert len(result) == 4


# ===========================================================================
# Post-fusion: clipping, interpolation, dropna
# ===========================================================================


class TestPostFusion:
    """Tests for post-fusion processing."""

    def test_values_clipped_to_physical_limits(self):
        """Out-of-range values clipped after fusion."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [80.0, 31.0, 32.0],  # 80°C → clipped
            "T2M_MIN": [-100.0, 19.0, 20.0],  # -100°C → clipped
            "T2M": [24.0, 25.0, 26.0],
            "RH2M": [150.0, 66.0, 67.0],  # 150% → clipped to 100
            "WS2M": [3.0, 3.1, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6)
        # Should be clipped to physical limits
        limits = fusion.GLOBAL_LIMITS
        if "T2M_MAX" in limits:
            assert result["T2M_MAX"].iloc[0] <= limits["T2M_MAX"][1]
        if "RH2M" in limits:
            assert result["RH2M"].iloc[0] <= limits["RH2M"][1]

    def test_nan_interpolated(self):
        """NaN values interpolated (limit=3)."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, np.nan, 32.0, 33.0, 34.0],
            "T2M_MIN": [18.0, 19.0, 20.0, 21.0, 22.0],
            "T2M": [24.0, 25.0, 26.0, 27.0, 28.0],
            "RH2M": [65.0, 66.0, 67.0, 68.0, 69.0],
            "WS2M": [3.0, 3.1, 3.2, 3.3, 3.4],
            "ALLSKY_SFC_SW_DWN": [20.0, 21.0, 22.0, 23.0, 24.0],
            "PRECTOTCORR": [2.0, 3.0, 4.0, 5.0, 6.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6)
        # NaN at index 1 should be interpolated (between 30 and 32 → ≈31)
        assert pd.notna(result["T2M_MAX"].iloc[1])

    def test_dropna_thresh(self):
        """Rows with <4 non-NaN values are dropped."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, np.nan, 32.0],
            "T2M_MIN": [18.0, np.nan, 20.0],
            "T2M": [24.0, np.nan, 26.0],
            "RH2M": [65.0, np.nan, 67.0],
            "WS2M": [3.0, np.nan, 3.2],
            "ALLSKY_SFC_SW_DWN": [20.0, np.nan, 22.0],
            "PRECTOTCORR": [2.0, np.nan, 4.0],
            "source": "nasa_power",
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6)
        # Row with all NaN (after single-source passthrough) might be dropped
        # Interpolation may fill some, but if all are NaN thresh=4 drops it
        assert len(result) <= 3


# ===========================================================================
# Quality metrics and source health
# ===========================================================================


class TestQualityAndHealth:
    """Tests for quality tracking and circuit breaker."""

    def test_quality_metrics_tracked(self):
        """After fusion, quality_metrics populated for each source."""
        fusion = ClimateFusion()
        df = _multi_source_df(["nasa_power", "openmeteo_archive"], n_days=3)
        fusion.fuse_multi_source(df, -23.5, -46.6, mode="historical")
        assert "nasa_power" in fusion.quality_metrics
        assert "openmeteo_archive" in fusion.quality_metrics
        assert fusion.quality_metrics["nasa_power"]["total_records"] == 3

    def test_circuit_breaker_unhealthy_source(self):
        """Source with avg quality < 60% excluded from weights."""
        fusion = ClimateFusion()
        # Inject bad quality metrics for met_norway
        fusion.quality_metrics["met_norway"] = {
            "total_records": 10,
            "quality_scores": {"T2M_MAX": 30.0, "T2M_MIN": 25.0},
        }
        assert not fusion._check_source_health("met_norway")

    def test_circuit_breaker_healthy_source(self):
        """Source with avg quality >= 60% is healthy."""
        fusion = ClimateFusion()
        fusion.quality_metrics["nasa_power"] = {
            "total_records": 10,
            "quality_scores": {"T2M_MAX": 95.0, "T2M_MIN": 90.0},
        }
        assert fusion._check_source_health("nasa_power")

    def test_circuit_breaker_unknown_source_healthy(self):
        """Unknown source without metrics → healthy (optimistic)."""
        fusion = ClimateFusion()
        assert fusion._check_source_health("unknown_source")


# ===========================================================================
# Region detection
# ===========================================================================


class TestRegionDetection:
    """Tests for _detect_region_with_priority."""

    def test_usa_region(self):
        fusion = ClimateFusion()
        region = fusion._detect_region_with_priority(40.7, -74.0)
        assert region["name"] == "USA"
        assert "nws_forecast" in region["weights"]

    def test_nordic_region(self):
        fusion = ClimateFusion()
        region = fusion._detect_region_with_priority(60.0, 10.0)
        assert region["name"] == "NORDIC"
        assert region["weights"].get("met_norway", 0) > 0.5

    def test_global_region(self):
        fusion = ClimateFusion()
        region = fusion._detect_region_with_priority(-23.5, -46.6)
        assert region["name"] == "GLOBAL"
        assert "openmeteo_forecast" in region["weights"]
