"""
Phase 7 – results_graphs.py comprehensive tests.

Covers all 5 plot functions:
- plot_eto_vs_temperature
- plot_eto_vs_radiation
- plot_temp_rad_prec
- plot_heatmap
- plot_correlation
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from unittest.mock import patch

_TRANSLATIONS = {
    "data_variables": {
        "temp_max": "Temp Max (°C)",
        "temp_min": "Temp Min (°C)",
        "temp_mean": "Temp Mean (°C)",
        "humidity": "Humidity (%)",
        "wind_speed": "Wind (m/s)",
        "radiation": "Radiation (MJ/m²/day)",
        "precipitation": "Precipitation (mm)",
        "eto": "ETo (mm/day)",
        "eto_evaonline": "ETo EVAonline",
        "eto_openmeteo": "ETo Open-Meteo",
    },
    "charts": {
        "temperature": "Temperature (°C)",
        "date_label": "Date",
        "legend": "Legend",
        "trend_line": "Trend Line",
    },
    "statistics": {},
}


def _get_translations_mock(lang="pt"):
    return _TRANSLATIONS


def _sample_df(n=14, with_eto_col="eto_evaonline"):
    """Return a realistic weather DataFrame for graph tests."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "date": dates,
            "T2M_MAX": rng.uniform(28, 38, n),
            "T2M_MIN": rng.uniform(15, 22, n),
            "T2M": rng.uniform(20, 30, n),
            "RH2M": rng.uniform(40, 80, n),
            "WS2M": rng.uniform(1, 5, n),
            "ALLSKY_SFC_SW_DWN": rng.uniform(10, 25, n),
            "PRECTOTCORR": rng.uniform(0, 10, n),
            with_eto_col: rng.uniform(2, 7, n),
        }
    )
    # Also add "ETo" for correlation tests
    df["ETo"] = df[with_eto_col]
    return df


_PATCHES = {
    "get_translations": _get_translations_mock
}


# ═══════════════════════════════════════════════════════════════
# plot_eto_vs_temperature
# ═══════════════════════════════════════════════════════════════

class TestPlotEtoVsTemperature:
    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_valid_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_temperature,
        )

        fig = plot_eto_vs_temperature(_sample_df(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 3  # bar + 2 scatter

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_none_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_temperature,
        )

        fig = plot_eto_vs_temperature(None)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_empty_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_temperature,
        )

        fig = plot_eto_vs_temperature(pd.DataFrame())
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_missing_columns(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_temperature,
        )

        df = pd.DataFrame({"date": [1, 2]})  # no T2M_MAX, T2M_MIN, ETo
        fig = plot_eto_vs_temperature(df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_old_eto_column_name(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_temperature,
        )

        df = _sample_df(with_eto_col="ETo")
        df.drop(columns=["eto_evaonline"], errors="ignore", inplace=True)
        fig = plot_eto_vs_temperature(df, lang="pt")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 3


# ═══════════════════════════════════════════════════════════════
# plot_eto_vs_radiation
# ═══════════════════════════════════════════════════════════════

class TestPlotEtoVsRadiation:
    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_valid_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_radiation,
        )

        fig = plot_eto_vs_radiation(_sample_df(), lang="pt")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_none_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_radiation,
        )

        fig = plot_eto_vs_radiation(None)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_missing_radiation_col(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_eto_vs_radiation,
        )

        df = pd.DataFrame({"date": [1], "eto_evaonline": [3.5]})
        fig = plot_eto_vs_radiation(df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0


# ═══════════════════════════════════════════════════════════════
# plot_temp_rad_prec
# ═══════════════════════════════════════════════════════════════

class TestPlotTempRadPrec:
    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_valid_df(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_temp_rad_prec,
        )

        fig = plot_temp_rad_prec(_sample_df(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 3  # bar ETo + scatter T2M_MAX + bar precip

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_none_empty(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_temp_rad_prec,
        )

        assert len(plot_temp_rad_prec(None).data) == 0
        assert len(plot_temp_rad_prec(pd.DataFrame()).data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_missing_prec_col(self, **_):
        from backend.core.data_results.results_graphs import (
            plot_temp_rad_prec,
        )

        df = pd.DataFrame({"date": [1], "T2M_MAX": [35], "eto_evaonline": [4]})
        fig = plot_temp_rad_prec(df)
        assert len(fig.data) == 0


# ═══════════════════════════════════════════════════════════════
# plot_heatmap
# ═══════════════════════════════════════════════════════════════

class TestPlotHeatmap:
    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_valid_df(self, **_):
        from backend.core.data_results.results_graphs import plot_heatmap

        fig = plot_heatmap(_sample_df(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1  # heatmap trace

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_none_df(self, **_):
        from backend.core.data_results.results_graphs import plot_heatmap

        fig = plot_heatmap(None)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_empty_df(self, **_):
        from backend.core.data_results.results_graphs import plot_heatmap

        fig = plot_heatmap(pd.DataFrame())
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_only_excluded_columns(self, **_):
        from backend.core.data_results.results_graphs import plot_heatmap

        df = pd.DataFrame({"date": ["2024-01-01"], "PRECTOTCORR": [5.0]})
        # all columns excluded → raises ValueError internally → returns empty fig
        fig = plot_heatmap(df)
        assert isinstance(fig, go.Figure)


# ═══════════════════════════════════════════════════════════════
# plot_correlation
# ═══════════════════════════════════════════════════════════════

class TestPlotCorrelation:
    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_valid(self, **_):
        from backend.core.data_results.results_graphs import plot_correlation

        df = _sample_df()
        fig = plot_correlation(df, "T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # scatter + trend line

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_none_df(self, **_):
        from backend.core.data_results.results_graphs import plot_correlation

        fig = plot_correlation(None, "T2M_MAX")
        assert len(fig.data) == 0

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_invalid_x_var(self, **_):
        from backend.core.data_results.results_graphs import plot_correlation

        df = _sample_df()
        fig = plot_correlation(df, "NONEXISTENT")
        # raises ValueError → caught → returns empty figure
        assert isinstance(fig, go.Figure)

    @patch.multiple("backend.core.data_results.results_graphs", **_PATCHES)
    def test_temperature_correlation(self, **_):
        from backend.core.data_results.results_graphs import plot_correlation

        df = _sample_df()
        fig = plot_correlation(df, "ALLSKY_SFC_SW_DWN", lang="pt")
        assert len(fig.data) >= 2
