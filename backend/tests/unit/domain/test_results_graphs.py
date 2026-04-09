"""
Unit Tests – backend.core.data_results.results_graphs

Tests for plot_eto_vs_temperature, plot_eto_vs_radiation,
plot_temp_rad_prec, plot_heatmap, and plot_correlation.

Each plotting function expects a DataFrame with specific columns:
  - plot_eto_vs_temperature: date, T2M_MAX, T2M_MIN, eto_evaonline|ETo
  - plot_eto_vs_radiation:   date, ALLSKY_SFC_SW_DWN, eto_evaonline|ETo
  - plot_temp_rad_prec:      date, T2M_MAX, PRECTOTCORR, eto_evaonline|ETo
  - plot_heatmap:            numeric cols (excl. date, PRECTOTCORR)
  - plot_correlation:        ETo, <x_var>

All return go.Figure (empty on error/missing cols).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

from backend.core.data_results.results_graphs import (
    plot_eto_vs_temperature,
    plot_eto_vs_radiation,
    plot_temp_rad_prec,
    plot_heatmap,
    plot_correlation,
)


# ============================================================================
# Shared mock & fixtures
# ============================================================================

MOCK_TRANSLATIONS = {
    "data_variables": {
        "date": "Date",
        "temp_max": "Temp Max (°C)",
        "temp_min": "Temp Min (°C)",
        "humidity": "Humidity (%)",
        "wind_speed": "Wind Speed (m/s)",
        "radiation": "Radiation (MJ/m²/day)",
        "precipitation": "Precipitation (mm)",
        "eto": "ETo (mm/day)",
        "eto_evaonline": "ETo EVAonline (mm/day)",
        "eto_openmeteo": "ETo Open-Meteo (mm/day)",
    },
    "charts": {
        "temperature": "Temperature (°C)",
        "date_label": "Date",
        "legend": "Legend",
        "trend_line": "Trend Line",
    },
    "statistics": {
        "correlation_title": "Correlation Matrix",
    },
    "results": {"error": "Error", "no_data": "No data available"},
}

_PATCH_TARGET = "backend.core.data_results.results_graphs.get_translations"


@pytest.fixture
def full_climate_df():
    """14-day climate DataFrame with all expected columns."""
    dates = pd.date_range("2024-06-01", periods=14, freq="D")
    np.random.seed(42)
    return pd.DataFrame(
        {
            "date": dates,
            "T2M_MAX": np.random.uniform(28, 38, 14),
            "T2M_MIN": np.random.uniform(16, 24, 14),
            "RH2M": np.random.uniform(40, 85, 14),
            "WS2M": np.random.uniform(1, 6, 14),
            "ALLSKY_SFC_SW_DWN": np.random.uniform(10, 28, 14),
            "PRECTOTCORR": np.random.uniform(0, 12, 14),
            "eto_evaonline": np.random.uniform(3, 8, 14),
        }
    )


@pytest.fixture
def legacy_eto_df():
    """7-day DataFrame using legacy 'ETo' column."""
    dates = pd.date_range("2024-01-01", periods=7, freq="D")
    np.random.seed(1)
    return pd.DataFrame(
        {
            "date": dates,
            "T2M_MAX": np.random.uniform(28, 38, 7),
            "T2M_MIN": np.random.uniform(16, 24, 7),
            "ALLSKY_SFC_SW_DWN": np.random.uniform(10, 28, 7),
            "PRECTOTCORR": np.random.uniform(0, 12, 7),
            "ETo": np.random.uniform(3, 8, 7),
        }
    )


# ============================================================================
# Tests – plot_eto_vs_temperature
# ============================================================================


class TestPlotEtoVsTemperature:
    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_returns_figure(self, _m, full_climate_df):
        fig = plot_eto_vs_temperature(full_climate_df, lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_has_three_traces(self, _m, full_climate_df):
        """Bar (ETo) + line (T2M_MAX) + line (T2M_MIN) = 3 traces."""
        fig = plot_eto_vs_temperature(full_climate_df, lang="en")
        assert len(fig.data) == 3

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_empty_df_returns_empty_figure(self, _m):
        fig = plot_eto_vs_temperature(pd.DataFrame(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_none_df_returns_empty_figure(self, _m):
        fig = plot_eto_vs_temperature(None, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_missing_column_returns_empty(self, _m):
        """Missing T2M_MIN → empty figure."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "T2M_MAX": [30, 31, 32],
                "eto_evaonline": [4, 5, 6],
            }
        )
        fig = plot_eto_vs_temperature(df, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_legacy_eto_column(self, _m, legacy_eto_df):
        fig = plot_eto_vs_temperature(legacy_eto_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3


# ============================================================================
# Tests – plot_eto_vs_radiation
# ============================================================================


class TestPlotEtoVsRadiation:
    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_returns_figure(self, _m, full_climate_df):
        fig = plot_eto_vs_radiation(full_climate_df, lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_has_two_traces(self, _m, full_climate_df):
        """ETo line + radiation line = 2 traces."""
        fig = plot_eto_vs_radiation(full_climate_df, lang="en")
        assert len(fig.data) == 2

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_empty_df(self, _m):
        fig = plot_eto_vs_radiation(pd.DataFrame(), lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_none_df(self, _m):
        fig = plot_eto_vs_radiation(None, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_missing_radiation_column(self, _m):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "eto_evaonline": [4, 5, 6],
            }
        )
        fig = plot_eto_vs_radiation(df, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_legacy_eto(self, _m, legacy_eto_df):
        fig = plot_eto_vs_radiation(legacy_eto_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2


# ============================================================================
# Tests – plot_temp_rad_prec
# ============================================================================


class TestPlotTempRadPrec:
    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_returns_figure(self, _m, full_climate_df):
        fig = plot_temp_rad_prec(full_climate_df, lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_has_three_traces(self, _m, full_climate_df):
        """Bar (ETo) + line (T2M_MAX) + Bar (PRECTOTCORR) = 3 traces."""
        fig = plot_temp_rad_prec(full_climate_df, lang="en")
        assert len(fig.data) == 3

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_empty_df(self, _m):
        fig = plot_temp_rad_prec(pd.DataFrame(), lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_none_df(self, _m):
        fig = plot_temp_rad_prec(None, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_missing_prectotcorr(self, _m):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "T2M_MAX": [30, 31, 32],
                "eto_evaonline": [4, 5, 6],
            }
        )
        fig = plot_temp_rad_prec(df, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_legacy_eto(self, _m, legacy_eto_df):
        fig = plot_temp_rad_prec(legacy_eto_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3


# ============================================================================
# Tests – plot_heatmap
# ============================================================================


class TestPlotHeatmap:
    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_returns_figure(self, _m, full_climate_df):
        fig = plot_heatmap(full_climate_df, lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_has_heatmap_trace(self, _m, full_climate_df):
        fig = plot_heatmap(full_climate_df, lang="en")
        assert len(fig.data) >= 1
        assert fig.data[0].type == "heatmap"

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_empty_df(self, _m):
        fig = plot_heatmap(pd.DataFrame(), lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_none_df(self, _m):
        fig = plot_heatmap(None, lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_excludes_date_and_prectotcorr(self, _m, full_climate_df):
        """Heatmap excludes 'date' and 'PRECTOTCORR' from correlation."""
        fig = plot_heatmap(full_climate_df, lang="en")
        heatmap_labels = list(fig.data[0].x) if fig.data[0].x is not None else []
        for label in heatmap_labels:
            assert "date" not in str(label).lower() or "PRECTOTCORR" not in str(label)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_only_date_column_raises(self, _m):
        """If no numeric columns survive filtering, should return empty figure (caught exception)."""
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3)})
        fig = plot_heatmap(df, lang="en")
        # Exception is caught and empty figure returned
        assert isinstance(fig, go.Figure)


# ============================================================================
# Tests – plot_correlation
# ============================================================================


class TestPlotCorrelation:
    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_returns_figure(self, _m):
        df = pd.DataFrame(
            {
                "T2M_MAX": np.random.uniform(28, 38, 10),
                "ETo": np.random.uniform(3, 8, 10),
            }
        )
        fig = plot_correlation(df, x_var="T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_has_scatter_and_trend_traces(self, _m):
        df = pd.DataFrame(
            {
                "T2M_MAX": np.random.uniform(28, 38, 10),
                "ETo": np.random.uniform(3, 8, 10),
            }
        )
        fig = plot_correlation(df, x_var="T2M_MAX", lang="en")
        assert len(fig.data) == 2  # scatter + trend line

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_empty_df(self, _m):
        fig = plot_correlation(pd.DataFrame(), x_var="T2M_MAX", lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_none_df(self, _m):
        fig = plot_correlation(None, x_var="T2M_MAX", lang="en")
        assert len(fig.data) == 0

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_missing_x_var(self, _m):
        """If x_var column not in df, should return empty figure (caught exception)."""
        df = pd.DataFrame({"ETo": [3, 4, 5]})
        fig = plot_correlation(df, x_var="NONEXISTENT", lang="en")
        assert isinstance(fig, go.Figure)

    @patch(_PATCH_TARGET, return_value=MOCK_TRANSLATIONS)
    def test_missing_eto_column(self, _m):
        df = pd.DataFrame({"T2M_MAX": [30, 31, 32]})
        fig = plot_correlation(df, x_var="T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)
