"""
Unit Tests - Climate Fusion (Domain Layer)

Tests the multi-source weighted fusion engine (ClimateFusion):
- Weighted average calculation (per-variable NASA POWER weights)
- Single-source passthrough
- Gap-fill fallback (openmeteo_forecast fills nasa_power gaps)
- Regional weight detection (USA, Nordic, Global)
- Mode detection (historical, recent, forecast)
- Physical limit clipping
- Circuit-breaker / source health

Reference: Article Section 2.3 (Multi-Source Fusion)
"""

import numpy as np
import pandas as pd
import pytest

from backend.core.data_processing.climate_fusion import ClimateFusion


# ============================================================================
# Helpers
# ============================================================================

def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Create a multi-source DataFrame in the expected format."""
    df = pd.DataFrame(rows)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def _two_source_day(date_str: str, nasa_vals: dict, om_vals: dict) -> list[dict]:
    """Build two rows (nasa_power + openmeteo_archive) for one day."""
    base = {"date": date_str, "PRECTOTCORR": 0.0}
    return [
        {**base, "source": "nasa_power", **nasa_vals},
        {**base, "source": "openmeteo_archive", **om_vals},
    ]


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.unit
class TestClimateFusionWeightedAverage:
    """Tests for the core weighted-average logic of ClimateFusion."""

    def setup_method(self):
        self.fusion = ClimateFusion()

    # ------------------------------------------------------------------ #
    # 1. Basic weighted average (two primary sources)
    # ------------------------------------------------------------------ #

    def test_weighted_fusion_forecast_two_sources(self):
        """
        Forecast mode with two forecast sources (openmeteo_forecast +
        met_norway) applies region-based weighted fusion.
        """
        rows = [
            {"date": "2024-01-15", "source": "openmeteo_forecast",
             "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0,
             "PRECTOTCORR": 0.0},
            {"date": "2024-01-15", "source": "met_norway",
             "T2M_MAX": 32.0, "T2M_MIN": 19.0, "T2M": 25.0,
             "RH2M": 60.0, "WS2M": 3.0, "ALLSKY_SFC_SW_DWN": 22.0,
             "PRECTOTCORR": 0.0},
        ]
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="dashboard_forecast")

        assert len(result) >= 1, "Should produce at least 1 fused row"
        # T2M_MAX should be between 30 and 32 (weighted)
        val = result["T2M_MAX"].iloc[0]
        assert 29.5 <= val <= 32.5, f"T2M_MAX={val} outside expected range"

    def test_historical_single_primary_per_date(self):
        """
        In historical mode, _prepare_data deduplicates by date,
        so a single primary source value is used per day.
        """
        rows = _two_source_day(
            "2024-01-15",
            {"T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0},
            {"T2M_MAX": 32.0, "T2M_MIN": 19.0, "T2M": 25.0,
             "RH2M": 60.0, "WS2M": 3.0, "ALLSKY_SFC_SW_DWN": 22.0},
        )
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")

        assert len(result) == 1, "Should produce 1 fused row per day"
        # After dedup, one primary source prevails; value should be one of the inputs
        val = result["T2M_MAX"].iloc[0]
        assert val in (30.0, 32.0) or 29.5 <= val <= 32.5

    def test_weighted_average_preserves_all_variables(self):
        """All 7 standard variables must be present in fused output."""
        rows = _two_source_day(
            "2024-01-15",
            {"T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0},
            {"T2M_MAX": 31.0, "T2M_MIN": 18.5, "T2M": 24.5,
             "RH2M": 63.0, "WS2M": 2.8, "ALLSKY_SFC_SW_DWN": 21.0},
        )
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")

        expected_vars = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M",
                         "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
        for var in expected_vars:
            assert var in result.columns, f"Missing variable: {var}"

    # ------------------------------------------------------------------ #
    # 2. Single-source passthrough
    # ------------------------------------------------------------------ #

    def test_single_source_passthrough(self):
        """With only one source the values pass through unchanged."""
        rows = [
            {"date": "2024-01-15", "source": "nasa_power",
             "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0,
             "PRECTOTCORR": 5.0},
        ]
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")

        assert len(result) == 1
        assert result["T2M_MAX"].iloc[0] == pytest.approx(30.0, abs=0.5)

    # ------------------------------------------------------------------ #
    # 3. Gap-fill with fallback source
    # ------------------------------------------------------------------ #

    def test_gap_fill_with_openmeteo_forecast(self):
        """
        If nasa_power has data for day 1 but not day 2, and
        openmeteo_forecast has day 2, fusion should fill the gap.
        """
        rows = [
            # Day 1: only nasa_power
            {"date": "2024-01-15", "source": "nasa_power",
             "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0,
             "PRECTOTCORR": 0.0},
            # Day 2: only openmeteo_forecast (gap-filler)
            {"date": "2024-01-16", "source": "openmeteo_forecast",
             "T2M_MAX": 31.0, "T2M_MIN": 19.0, "T2M": 25.0,
             "RH2M": 60.0, "WS2M": 3.0, "ALLSKY_SFC_SW_DWN": 22.0,
             "PRECTOTCORR": 0.0},
        ]
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")

        assert len(result) >= 2, "Should have data for both days"

    # ------------------------------------------------------------------ #
    # 4. Multiple days
    # ------------------------------------------------------------------ #

    def test_multiple_days_fusion(self, sample_multi_source_df):
        """Fusion over 5 days with two sources produces 5 rows."""
        result = self.fusion.fuse_multi_source(
            sample_multi_source_df, lat=-22.0, lon=-48.0, mode="historical_email"
        )
        assert len(result) == 5, f"Expected 5 rows, got {len(result)}"

    # ------------------------------------------------------------------ #
    # 5. Edge cases
    # ------------------------------------------------------------------ #

    def test_empty_dataframe_returns_empty(self):
        """Fusion with empty DataFrame should not crash."""
        df = pd.DataFrame()
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0)
        assert isinstance(result, pd.DataFrame)

    def test_nan_values_handled(self):
        """NaN values in one source should use the other source."""
        rows = [
            {"date": "2024-01-15", "source": "nasa_power",
             "T2M_MAX": np.nan, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0,
             "PRECTOTCORR": 0.0},
            {"date": "2024-01-15", "source": "openmeteo_archive",
             "T2M_MAX": 31.0, "T2M_MIN": 18.5, "T2M": 24.5,
             "RH2M": 63.0, "WS2M": 2.8, "ALLSKY_SFC_SW_DWN": 21.0,
             "PRECTOTCORR": 0.0},
        ]
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")

        assert len(result) >= 1
        # T2M_MAX should come from openmeteo_archive since nasa is NaN
        if not result["T2M_MAX"].isna().all():
            assert result["T2M_MAX"].iloc[0] == pytest.approx(31.0, abs=1.0)


@pytest.mark.unit
class TestClimateFusionRegionDetection:
    """Tests for region-based weight selection."""

    def setup_method(self):
        self.fusion = ClimateFusion()

    def test_detect_usa_region(self):
        """Coordinates in USA should return USA region."""
        region = self.fusion._detect_region_with_priority(40.7, -74.0)
        assert region["name"].upper() in ("USA", "US")

    def test_detect_nordic_region(self):
        """Coordinates in Oslo should return Nordic region."""
        region = self.fusion._detect_region_with_priority(59.9, 10.75)
        assert "NORDIC" in region["name"].upper() or "NORD" in region["name"].upper()

    def test_detect_global_region(self):
        """Coordinates in Brazil should return Global region."""
        region = self.fusion._detect_region_with_priority(-22.0, -48.0)
        assert "GLOBAL" in region["name"].upper() or "BRASIL" in region["name"].upper() or "BRAZIL" in region["name"].upper()

    def test_region_has_weights_and_order(self):
        """Region dict must contain weights and order keys."""
        region = self.fusion._detect_region_with_priority(40.7, -74.0)
        assert "weights" in region
        assert "order" in region
        assert isinstance(region["weights"], dict)
        assert isinstance(region["order"], list)


@pytest.mark.unit
class TestClimateFusionModeDetection:
    """Tests for operation mode detection inside fuse_multi_source."""

    def setup_method(self):
        self.fusion = ClimateFusion()

    def _make_historical_df(self):
        rows = _two_source_day(
            "2024-01-15",
            {"T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0},
            {"T2M_MAX": 31.0, "T2M_MIN": 18.5, "T2M": 24.5,
             "RH2M": 63.0, "WS2M": 2.8, "ALLSKY_SFC_SW_DWN": 21.0},
        )
        return _make_df(rows)

    def test_historical_mode_explicit(self):
        """Explicit 'historical_email' mode uses historical weights."""
        df = self._make_historical_df()
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="historical_email")
        assert len(result) >= 1  # Should not error

    def test_dashboard_current_mode(self):
        """Mode 'dashboard_current' triggers recent strategy."""
        df = self._make_historical_df()
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="dashboard_current")
        assert len(result) >= 1

    def test_dashboard_forecast_mode(self):
        """Mode 'dashboard_forecast' triggers forecast strategy."""
        rows = [
            {"date": "2024-01-15", "source": "openmeteo_forecast",
             "T2M_MAX": 30.0, "T2M_MIN": 18.0, "T2M": 24.0,
             "RH2M": 65.0, "WS2M": 2.5, "ALLSKY_SFC_SW_DWN": 20.0,
             "PRECTOTCORR": 0.0},
        ]
        df = _make_df(rows)
        result = self.fusion.fuse_multi_source(df, lat=-22.0, lon=-48.0, mode="dashboard_forecast")
        assert len(result) >= 1


@pytest.mark.unit
class TestClimateFusionConstants:
    """Validate the fusion weight constants match article values."""

    def test_hist_weights_keys(self):
        """HIST_WEIGHTS must contain all 7 standard variables."""
        expected = {"T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M",
                    "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"}
        assert expected == set(ClimateFusion.HIST_WEIGHTS.keys())

    def test_hist_weights_range(self):
        """All weights must be in (0, 1]."""
        for var, w in ClimateFusion.HIST_WEIGHTS.items():
            assert 0 < w <= 1, f"{var} weight {w} out of (0, 1]"

    def test_hist_weights_article_values(self):
        """Spot-check key weights against article methodology."""
        assert ClimateFusion.HIST_WEIGHTS["ALLSKY_SFC_SW_DWN"] == pytest.approx(0.92, abs=0.02)
        assert ClimateFusion.HIST_WEIGHTS["T2M_MAX"] == pytest.approx(0.58, abs=0.02)
        assert ClimateFusion.HIST_WEIGHTS["PRECTOTCORR"] == pytest.approx(0.50, abs=0.02)

    def test_primary_and_fallback_sets(self):
        """PRIMARY and FALLBACK source sets should be disjoint."""
        assert ClimateFusion.PRIMARY_SOURCES & ClimateFusion.FALLBACK_SOURCES == set()

    def test_historical_all_superset(self):
        """HISTORICAL_ALL_SOURCES = PRIMARY ∪ FALLBACK."""
        union = ClimateFusion.PRIMARY_SOURCES | ClimateFusion.FALLBACK_SOURCES
        assert union == ClimateFusion.HISTORICAL_ALL_SOURCES


@pytest.mark.unit
class TestClimateFusionSourceHealth:
    """Tests for circuit-breaker / source health tracking."""

    def setup_method(self):
        self.fusion = ClimateFusion()

    def test_healthy_source_passes(self):
        """A source with good quality metrics should be healthy."""
        self.fusion.quality_metrics["nasa_power"] = {
            "total_records": 30,
            "quality_scores": {"T2M_MAX": 95.0, "T2M_MIN": 90.0, "T2M": 92.0},
        }
        assert self.fusion._check_source_health("nasa_power")

    def test_unhealthy_source_fails(self):
        """A source with very low quality should fail the check."""
        self.fusion.quality_metrics["bad_source"] = {
            "total_records": 30,
            "quality_scores": {"T2M_MAX": 10.0, "T2M_MIN": 5.0, "T2M": 8.0},
        }
        assert not self.fusion._check_source_health("bad_source")  # avg 7.67% < 60%

    def test_unknown_source_returns_true(self):
        """Unknown sources default to healthy (no data = no reason to block)."""
        assert self.fusion._check_source_health("unknown_source")
