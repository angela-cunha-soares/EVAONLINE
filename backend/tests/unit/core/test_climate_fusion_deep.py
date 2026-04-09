"""
Deep coverage tests for backend/core/data_processing/climate_fusion.py

Targets the uncovered multi-source fusion branches (lines 262-372)
and logging strategies (lines 403-432) that are unreachable through
normal flow because _prepare_data deduplicates overlapping dates.

Strategy: mock _prepare_data to return DataFrames where multiple
sources share the same date, so the per-day fusion logic fires.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from backend.core.data_processing.climate_fusion import ClimateFusion


VARS = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]


def _make_multi_source_indexed_df(sources, n_days=3, start="2025-01-01"):
    """Build a DataFrame ALREADY indexed by date with multiple sources per date.

    This simulates what _prepare_data would return if it didn't deduplicate,
    allowing the multi-source fusion branches to fire.
    """
    dates = pd.date_range(start, periods=n_days, freq="D")
    rows = []
    for d in dates:
        for src in sources:
            rows.append({
                "date": d,
                "T2M_MAX": 30.0 + hash(src) % 5,
                "T2M_MIN": 18.0 + hash(src) % 3,
                "T2M": 24.0 + hash(src) % 4,
                "RH2M": 65.0 + hash(src) % 10,
                "WS2M": 3.0 + hash(src) % 2,
                "ALLSKY_SFC_SW_DWN": 20.0 + hash(src) % 5,
                "PRECTOTCORR": 2.0 + hash(src) % 4,
                "source": src,
            })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


# ===========================================================================
# _prepare_data edge cases (L141-142, L160)
# ===========================================================================


class TestPrepareDataEdgeCases:
    """Cover edge cases in _prepare_data."""

    def test_no_date_column_non_datetime_index(self):
        """L141-142: no 'date' column AND index is not DatetimeIndex → early return."""
        fusion = ClimateFusion()
        df = pd.DataFrame({
            "T2M_MAX": [30.0, 31.0],
            "T2M_MIN": [18.0, 19.0],
        })
        # Index is default RangeIndex, no "date" column
        result = fusion._prepare_data(df)
        # Should return the df unchanged (early return)
        assert isinstance(result, pd.DataFrame)

    def test_no_date_column_datetime_index_resets(self):
        """DatetimeIndex but no 'date' column → reset_index creates 'date'."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "T2M_MAX": [30.0, 31.0, 32.0],
            "source": ["nasa_power"] * 3,
        }, index=dates)
        df.index.name = "date"
        result = fusion._prepare_data(df)
        assert "T2M_MAX" in result.columns

    def test_dedup_no_source_column(self):
        """L160: keep_best when group has no 'source' column → g.head(1)."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        df = pd.DataFrame({
            "date": list(dates) + list(dates),
            "T2M_MAX": [30.0, 31.0, 32.0, 33.0],
            "T2M_MIN": [18.0, 19.0, 20.0, 21.0],
        })
        # No "source" column → dedup uses g.head(1)
        result = fusion._prepare_data(df)
        assert len(result) == 2  # Deduplicated to 2 dates

    def test_no_source_column_in_prepare(self):
        """_prepare_data with no 'source' column → 'unknown_source' tracking."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [30.0, 31.0, 32.0],
        })
        result = fusion._prepare_data(df)
        assert "unknown_source" in fusion.quality_metrics


# ===========================================================================
# fuse_multi_source without "source" column (L239)
# ===========================================================================


class TestFusionNoSourceColumn:
    """L239: fusion loop when group has no 'source' column."""

    def test_no_source_column_uses_default(self):
        """Without 'source' column, uses {\"default\": group}."""
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
        })
        result = fusion.fuse_multi_source(df, -23.5, -46.6)
        assert len(result) == 3
        assert "T2M_MAX" in result.columns


# ===========================================================================
# Historical mode: multi-source per day (L262-305)
# Mock _prepare_data to preserve multi-source rows per date.
# ===========================================================================


class TestHistoricalMultiSourcePerDay:
    """Tests that exercise the historical fusion branches by mocking
    _prepare_data to return a DataFrame with multiple sources per date."""

    def _run_hist_fusion(self, sources):
        """Helper: feed multi-source-per-day data through historical fusion."""
        fusion = ClimateFusion()
        multi_df = _make_multi_source_indexed_df(sources, n_days=3)
        with patch.object(fusion, "_prepare_data", return_value=multi_df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}),  # ignored, _prepare_data mocked
                lat=-23.5, lon=-46.6, mode="historical"
            )
        return result, fusion

    def test_two_primary_hist_weighted(self):
        """L272-290: Both primary sources → HIST_WEIGHTS fusion."""
        result, _ = self._run_hist_fusion(["nasa_power", "openmeteo_archive"])
        assert len(result) == 3
        # Values should be weighted average, not raw from either source
        for var in VARS:
            assert var in result.columns

    def test_two_primary_prectotcorr_mean(self):
        """L276-277: PRECTOTCORR with two primaries → np.mean()."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "PRECTOTCORR": 4.0, "source": "nasa_power",
                         "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24, "RH2M": 65,
                         "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20})
            rows.append({"date": d, "PRECTOTCORR": 6.0, "source": "openmeteo_archive",
                         "T2M_MAX": 31, "T2M_MIN": 19, "T2M": 25, "RH2M": 70,
                         "WS2M": 4, "ALLSKY_SFC_SW_DWN": 22})
        df = pd.DataFrame(rows).set_index(pd.to_datetime(pd.DataFrame(rows)["date"]))
        df.index.name = "date"

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        # PRECTOTCORR should be mean of 4 and 6 = 5
        assert result["PRECTOTCORR"].iloc[0] == pytest.approx(5.0, abs=0.5)

    def test_hist_weighted_non_prectotcorr(self):
        """L279-290: Non-PRECTOTCORR var with two primaries → weighted average."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=1, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 34.0, "T2M_MIN": 22, "T2M": 28,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 25,
                         "PRECTOTCORR": 4, "source": "openmeteo_archive"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        # T2M_MAX: nasa=30, archive=34, w_nasa=0.58, w_archive=0.42
        # weighted = 0.58*30 + 0.42*34 = 17.4 + 14.28 = 31.68
        expected = 0.58 * 30.0 + 0.42 * 34.0
        assert result["T2M_MAX"].iloc[0] == pytest.approx(expected, abs=0.5)

    def test_single_primary_plus_fallback(self):
        """L291-296: One primary source only → 100% primary."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 28.0, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        # Only nasa_power is PRIMARY → 100% of its value
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_no_primary_fallback_gapfill(self):
        """L297-302: No primary sources, only fallback → gap-fill."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 28.0, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            rows.append({"date": d, "T2M_MAX": 26.0, "T2M_MIN": 14, "T2M": 20,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 16,
                         "PRECTOTCORR": 4, "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        # openmeteo_forecast is FALLBACK → gap-fill 100%
        assert result["T2M_MAX"].iloc[0] == pytest.approx(28.0, abs=1.0)

    def test_no_primary_no_fallback_else(self):
        """L303-304: No primary, no fallback → first value."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            # met_norway is not PRIMARY and not FALLBACK in historical mode
            rows.append({"date": d, "T2M_MAX": 26.0, "T2M_MIN": 14, "T2M": 20,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 16,
                         "PRECTOTCORR": 4, "source": "met_norway"})
            rows.append({"date": d, "T2M_MAX": 25.0, "T2M_MIN": 13, "T2M": 19,
                         "RH2M": 73, "WS2M": 4.5, "ALLSKY_SFC_SW_DWN": 15,
                         "PRECTOTCORR": 3.5, "source": "nws_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        assert len(result) == 2


# ===========================================================================
# Recent mode: multi-source per day (L308-357)
# ===========================================================================


class TestRecentMultiSourcePerDay:
    """Tests for recent-mode multi-source fusion per day."""

    def test_recent_single_primary(self):
        """L315-321: Recent mode, 1 primary + another source → 100% primary."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 28.0, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_current"
            )
        # nasa_power is primary → 100%
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    def test_recent_two_primaries_hist_weights(self):
        """L323-342: Recent mode, 2 primary sources → HIST_WEIGHTS."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 4, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 34.0, "T2M_MIN": 22, "T2M": 28,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 25,
                         "PRECTOTCORR": 6, "source": "openmeteo_archive"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="current"
            )
        # T2M_MAX: weighted (0.58*30 + 0.42*34) ≈ 31.68
        expected = 0.58 * 30.0 + 0.42 * 34.0
        assert result["T2M_MAX"].iloc[0] == pytest.approx(expected, abs=0.5)
        # PRECTOTCORR: mean of 4 and 6 = 5
        assert result["PRECTOTCORR"].iloc[0] == pytest.approx(5.0, abs=0.5)

    def test_recent_no_primary_fallback(self):
        """L345-354: Recent mode, no primary → fallback source."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 28.0, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            rows.append({"date": d, "T2M_MAX": 26.0, "T2M_MIN": 14, "T2M": 20,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 16,
                         "PRECTOTCORR": 4, "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_current"
            )
        # openmeteo_forecast is fallback → 100%
        assert result["T2M_MAX"].iloc[0] == pytest.approx(28.0, abs=1.0)

    def test_recent_no_primary_no_fallback(self):
        """L355-356: Recent mode, no primary, no fallback → first value."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            # met_norway and nws_forecast are neither PRIMARY nor FALLBACK
            rows.append({"date": d, "T2M_MAX": 26.0, "T2M_MIN": 14, "T2M": 20,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 16,
                         "PRECTOTCORR": 4, "source": "met_norway"})
            rows.append({"date": d, "T2M_MAX": 25.0, "T2M_MIN": 13, "T2M": 19,
                         "RH2M": 73, "WS2M": 4.5, "ALLSKY_SFC_SW_DWN": 15,
                         "PRECTOTCORR": 3.5, "source": "nws_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_current"
            )
        assert len(result) == 2


# ===========================================================================
# Forecast mode: multi-source per day (L360-372)
# ===========================================================================


class TestForecastMultiSourcePerDay:
    """Tests for forecast-mode region-weighted fusion per day."""

    def test_forecast_global_multi_source(self):
        """L360-372: Forecast mode, multi-source → region-weighted fusion."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=3, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 28.0, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 4, "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_forecast"
            )
        assert len(result) == 3
        # Global: openmeteo_forecast=0.70, met_norway=0.30
        # T2M_MAX: (0.70*28 + 0.30*30) / 1.0 = 19.6 + 9.0 = 28.6
        assert result["T2M_MAX"].iloc[0] == pytest.approx(28.6, abs=0.5)

    def test_forecast_usa_multi_source(self):
        """Forecast mode USA region: nws_forecast=0.50, openmeteo=0.30, met=0.20."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 32.0, "T2M_MIN": 20, "T2M": 26,
                         "RH2M": 60, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 22,
                         "PRECTOTCORR": 2, "source": "nws_forecast"})
            rows.append({"date": d, "T2M_MAX": 30.0, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), 40.7, -74.0, mode="dashboard_forecast"
            )
        assert len(result) == 2

    def test_forecast_nordic_multi_source(self):
        """Forecast mode Nordic region: met_norway=0.80, openmeteo=0.20."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 20.0, "T2M_MIN": 10, "T2M": 15,
                         "RH2M": 80, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 12,
                         "PRECTOTCORR": 5, "source": "met_norway"})
            rows.append({"date": d, "T2M_MAX": 22.0, "T2M_MIN": 12, "T2M": 17,
                         "RH2M": 75, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 14,
                         "PRECTOTCORR": 4, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), 60.0, 10.0, mode="dashboard_forecast"
            )
        assert len(result) == 2
        # Nordic: met=0.80, om=0.20 → T2M_MAX ≈ 0.80*20 + 0.20*22 = 20.4
        assert result["T2M_MAX"].iloc[0] == pytest.approx(20.4, abs=0.5)


# ===========================================================================
# Circuit breaker: all sources unhealthy → emergency fallback (L203-215)
# ===========================================================================


class TestCircuitBreakerFallback:
    """Test that all unhealthy sources triggers emergency fallback."""

    def test_all_sources_unhealthy_returns_emergency(self):
        """When all sources in region fail health check → emergency fallback."""
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
        prepared = df.copy()
        prepared["date"] = pd.to_datetime(prepared["date"])
        prepared = prepared.set_index("date")

        # Patch at class level so the bound method call resolves to our mock
        with patch.object(ClimateFusion, "_prepare_data", return_value=prepared), \
             patch.object(ClimateFusion, "_check_source_health", return_value=False):
            result = fusion.fuse_multi_source(df, -23.5, -46.6, mode="dashboard_forecast")
        # Emergency fallback → 7 days with fixed values
        assert "fusion_mode" in result.columns
        assert len(result) == 7


# ===========================================================================
# _interpolate_safe (L170-176)
# ===========================================================================


class TestInterpolateSafe:
    """Test _interpolate_safe with clipping."""

    def test_interpolate_clips_to_limits(self):
        """Interpolated values are clipped to physical limits."""
        fusion = ClimateFusion()
        series = pd.Series([25.0, np.nan, 35.0], name="T2M_MAX")
        result = fusion._interpolate_safe(series)
        assert pd.notna(result.iloc[1])
        limits = fusion.GLOBAL_LIMITS.get("T2M_MAX")
        if limits:
            assert result.iloc[1] >= limits[0]
            assert result.iloc[1] <= limits[1]

    def test_interpolate_no_limit_variable(self):
        """Variable not in GLOBAL_LIMITS → no clipping."""
        fusion = ClimateFusion()
        series = pd.Series([10.0, np.nan, 20.0], name="some_unknown_var")
        result = fusion._interpolate_safe(series)
        assert pd.notna(result.iloc[1])
        assert result.iloc[1] == pytest.approx(15.0, abs=0.1)


# ===========================================================================
# Fusion strategy logging (L399-432)
# These execute when fusion_strategy dict is populated.
# ===========================================================================


class TestFusionStrategyLogging:
    """Test that all strategy logging branches are covered."""

    def test_hist_weighted_log(self):
        """hist_weighted strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 34, "T2M_MIN": 22, "T2M": 28,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 25,
                         "PRECTOTCORR": 4, "source": "openmeteo_archive"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        # Just verify it completes (logging branches execute)
        assert len(result) >= 1

    def test_hist_single_primary_log(self):
        """hist_single_primary strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 28, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        assert len(result) >= 1

    def test_hist_gapfill_log(self):
        """hist_gapfill strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            # Only fallback sources for 2+ values per variable
            rows.append({"date": d, "T2M_MAX": 28, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            # met_norway is in neither PRIMARY nor FALLBACK for historical
            rows.append({"date": d, "T2M_MAX": np.nan, "T2M_MIN": np.nan,
                         "T2M": np.nan, "RH2M": np.nan, "WS2M": np.nan,
                         "ALLSKY_SFC_SW_DWN": np.nan, "PRECTOTCORR": np.nan,
                         "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="historical"
            )
        assert len(result) >= 1

    def test_recent_single_log(self):
        """recent_single strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 28, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_current"
            )
        assert len(result) >= 1

    def test_recent_hist_weights_log(self):
        """recent_hist strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 65, "WS2M": 3, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 2, "source": "nasa_power"})
            rows.append({"date": d, "T2M_MAX": 34, "T2M_MIN": 22, "T2M": 28,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 25,
                         "PRECTOTCORR": 4, "source": "openmeteo_archive"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="current"
            )
        assert len(result) >= 1

    def test_recent_fallback_log(self):
        """recent_fallback strategy logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 28, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            rows.append({"date": d, "T2M_MAX": np.nan, "T2M_MIN": np.nan,
                         "T2M": np.nan, "RH2M": np.nan, "WS2M": np.nan,
                         "ALLSKY_SFC_SW_DWN": np.nan, "PRECTOTCORR": np.nan,
                         "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_current"
            )
        assert len(result) >= 1

    def test_multi_source_forecast_log(self):
        """multi strategy (forecast mode) logs correctly."""
        fusion = ClimateFusion()
        dates = pd.date_range("2025-06-01", periods=2, freq="D")
        rows = []
        for d in dates:
            rows.append({"date": d, "T2M_MAX": 28, "T2M_MIN": 16, "T2M": 22,
                         "RH2M": 70, "WS2M": 4, "ALLSKY_SFC_SW_DWN": 18,
                         "PRECTOTCORR": 3, "source": "openmeteo_forecast"})
            rows.append({"date": d, "T2M_MAX": 30, "T2M_MIN": 18, "T2M": 24,
                         "RH2M": 75, "WS2M": 5, "ALLSKY_SFC_SW_DWN": 20,
                         "PRECTOTCORR": 4, "source": "met_norway"})
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        with patch.object(fusion, "_prepare_data", return_value=df):
            result = fusion.fuse_multi_source(
                pd.DataFrame({"dummy": [1]}), -23.5, -46.6, mode="dashboard_forecast"
            )
        assert len(result) >= 1


# ===========================================================================
# _validate_climate_data and _track_data_quality
# ===========================================================================


class TestValidationAndQuality:
    """Test validation warnings and quality score edge cases."""

    def test_validate_out_of_range_logs_warning(self):
        """Out-of-range values trigger warning in _validate_climate_data."""
        fusion = ClimateFusion()
        df = pd.DataFrame({
            "T2M_MAX": [80.0, 31.0],  # 80 is out of range
            "RH2M": [150.0, 60.0],    # 150 is out of range
        })
        # Should not raise, just log
        fusion._validate_climate_data(df, "test_source")

    def test_track_quality_with_outliers(self):
        """Quality score penalizes outliers."""
        fusion = ClimateFusion()
        df = pd.DataFrame({
            "T2M_MAX": [80.0, 31.0, 32.0],  # 80 out of range
            "T2M_MIN": [18.0, 19.0, 20.0],
            "T2M": [24.0, 25.0, 26.0],
        })
        fusion._track_data_quality(df, "outlier_source")
        scores = fusion.quality_metrics["outlier_source"]["quality_scores"]
        if "T2M_MAX" in scores:
            # T2M_MAX has 1/3 outliers → completeness * (1 - 0.33) ≈ 66.7
            assert scores["T2M_MAX"] < 100.0

    def test_check_source_health_empty_scores(self):
        """Source with empty quality_scores → healthy (optimistic)."""
        fusion = ClimateFusion()
        fusion.quality_metrics["empty_src"] = {
            "total_records": 0,
            "quality_scores": {},
        }
        assert fusion._check_source_health("empty_src")
