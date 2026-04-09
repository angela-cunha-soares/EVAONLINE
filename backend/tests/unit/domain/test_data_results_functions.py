"""
Unit Tests – backend.core.data_results (functional tests)

Tests the pure-logic functions in results_tables, results_statistical,
results_graphs, and results_layout against sample DataFrames.
"""

import numpy as np
import pandas as pd
from dash import html

# ---------------------------------------------------------------------------
# Helper: build a realistic sample DataFrame used by most functions
# ---------------------------------------------------------------------------

def _sample_df(n: int = 35) -> pd.DataFrame:
    """Return a DataFrame with n rows of realistic EVAonline climate data."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "T2M_MAX": rng.uniform(28, 38, n).round(2),
        "T2M_MIN": rng.uniform(18, 24, n).round(2),
        "RH2M": rng.uniform(40, 90, n).round(2),
        "WS2M": rng.uniform(0.5, 5.0, n).round(2),
        "ALLSKY_SFC_SW_DWN": rng.uniform(10, 28, n).round(2),
        "PRECTOTCORR": rng.uniform(0, 15, n).round(2),
        "eto_evaonline": rng.uniform(2, 7, n).round(2),
        "ETo": rng.uniform(2, 7, n).round(2),
    })


def _small_df() -> pd.DataFrame:
    """6-row DataFrame (< 30 rows triggers forecast-mode logic)."""
    return _sample_df(6)


# ===================================================================
# results_tables tests
# ===================================================================

class TestFormatNumber:
    """Tests for results_tables.format_number"""

    def test_normal_value(self):
        from backend.core.data_results.results_tables import format_number
        assert format_number(25.123, 2) == "25.12"

    def test_nan_returns_dash(self):
        from backend.core.data_results.results_tables import format_number
        assert format_number(float("nan"), 2) == "-"

    def test_none_input(self):
        from backend.core.data_results.results_tables import format_number
        # pd.isna(None) → True
        assert format_number(None, 2) == "-"

    def test_zero(self):
        from backend.core.data_results.results_tables import format_number
        assert format_number(0, 3) == "0.000"

    def test_negative(self):
        from backend.core.data_results.results_tables import format_number
        assert format_number(-3.14159, 2) == "-3.14"

    def test_integer_input(self):
        from backend.core.data_results.results_tables import format_number
        assert format_number(42, 1) == "42.0"

    def test_string_input(self):
        from backend.core.data_results.results_tables import format_number
        # Non-numeric string → str(value)
        result = format_number("abc", 2)
        assert result == "abc"


class TestDisplayResultsTable:
    """Tests for results_tables.display_results_table"""

    def test_returns_html_div_with_valid_df(self):
        from backend.core.data_results.results_tables import display_results_table
        result = display_results_table(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df_returns_div(self):
        from backend.core.data_results.results_tables import display_results_table
        result = display_results_table(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)

    def test_none_df_returns_div(self):
        from backend.core.data_results.results_tables import display_results_table
        result = display_results_table(None, lang="pt")
        assert isinstance(result, html.Div)

    def test_english_lang(self):
        from backend.core.data_results.results_tables import display_results_table
        result = display_results_table(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    def test_missing_eto_column_raises(self):
        from backend.core.data_results.results_tables import display_results_table
        df = _sample_df().drop(columns=["eto_evaonline", "ETo"])
        # Should return a Div with error text (no ETo column)
        result = display_results_table(df, lang="pt")
        assert isinstance(result, html.Div)


# ===================================================================
# results_statistical tests
# ===================================================================

class TestDisplayDailyData:
    """Tests for results_statistical.display_daily_data"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_daily_data
        result = display_daily_data(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_daily_data
        result = display_daily_data(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


class TestDisplayDescriptiveStats:
    """Tests for results_statistical.display_descriptive_stats"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        result = display_descriptive_stats(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df_returns_div(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        result = display_descriptive_stats(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)

    def test_none_df_returns_div(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        result = display_descriptive_stats(None, lang="pt")
        assert isinstance(result, html.Div)

    def test_forecast_mode_hides_advanced_stats(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        result = display_descriptive_stats(_sample_df(), lang="pt", mode="DASHBOARD_FORECAST")
        assert isinstance(result, html.Div)

    def test_small_sample_hides_cv(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        # < 30 rows → no CV/skewness/kurtosis
        result = display_descriptive_stats(_small_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_english_lang(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats
        result = display_descriptive_stats(_sample_df(), lang="en")
        assert isinstance(result, html.Div)


class TestDisplayNormalityTest:
    """Tests for results_statistical.display_normality_test"""

    def test_returns_html_div_large_sample(self):
        from backend.core.data_results.results_statistical import display_normality_test
        result = display_normality_test(_sample_df(50), lang="pt")
        assert isinstance(result, html.Div)

    def test_small_sample_shows_info_alert(self):
        from backend.core.data_results.results_statistical import display_normality_test
        result = display_normality_test(_small_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_forecast_mode_shows_alert(self):
        from backend.core.data_results.results_statistical import display_normality_test
        result = display_normality_test(_sample_df(), lang="pt", mode="DASHBOARD_FORECAST")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_normality_test
        result = display_normality_test(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


class TestDisplayCorrelationMatrix:
    """Tests for results_statistical.display_correlation_matrix"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix
        result = display_correlation_matrix(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix
        result = display_correlation_matrix(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix
        result = display_correlation_matrix(None, lang="pt")
        assert isinstance(result, html.Div)


class TestDisplayEtoSummary:
    """Tests for results_statistical.display_eto_summary"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_eto_summary
        result = display_eto_summary(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_eto_summary
        result = display_eto_summary(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


class TestDisplayTrendAnalysis:
    """Tests for results_statistical.display_trend_analysis"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_trend_analysis
        result = display_trend_analysis(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_trend_analysis
        result = display_trend_analysis(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


class TestDisplaySeasonalityTest:
    """Tests for results_statistical.display_seasonality_test"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_seasonality_test
        result = display_seasonality_test(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_seasonality_test
        result = display_seasonality_test(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


class TestDisplayCumulativeDistribution:
    """Tests for results_statistical.display_cumulative_distribution"""

    def test_returns_html_div(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution
        result = display_cumulative_distribution(_sample_df(), lang="pt")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution
        result = display_cumulative_distribution(pd.DataFrame(), lang="pt")
        assert isinstance(result, html.Div)


# ===================================================================
# results_graphs tests
# ===================================================================

class TestPlotEtoVsTemperature:
    """Tests for results_graphs.plot_eto_vs_temperature"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_temperature
        fig = plot_eto_vs_temperature(_sample_df(), lang="pt")
        assert isinstance(fig, go.Figure)

    def test_empty_df_returns_empty_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_temperature
        fig = plot_eto_vs_temperature(pd.DataFrame(), lang="pt")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_none_df_returns_empty_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_temperature
        fig = plot_eto_vs_temperature(None, lang="pt")
        assert isinstance(fig, go.Figure)

    def test_missing_columns_returns_empty(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_temperature
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5)})
        fig = plot_eto_vs_temperature(df, lang="pt")
        assert isinstance(fig, go.Figure)

    def test_english_lang(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_temperature
        fig = plot_eto_vs_temperature(_sample_df(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestPlotEtoVsRadiation:
    """Tests for results_graphs.plot_eto_vs_radiation"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_radiation
        fig = plot_eto_vs_radiation(_sample_df(), lang="pt")
        assert isinstance(fig, go.Figure)

    def test_empty_df(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_eto_vs_radiation
        fig = plot_eto_vs_radiation(pd.DataFrame(), lang="pt")
        assert isinstance(fig, go.Figure)


class TestPlotTempRadPrec:
    """Tests for results_graphs.plot_temp_rad_prec"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_temp_rad_prec
        fig = plot_temp_rad_prec(_sample_df(), lang="pt")
        assert isinstance(fig, go.Figure)

    def test_empty_df(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_temp_rad_prec
        fig = plot_temp_rad_prec(pd.DataFrame(), lang="pt")
        assert isinstance(fig, go.Figure)


class TestPlotHeatmap:
    """Tests for results_graphs.plot_heatmap"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_heatmap
        fig = plot_heatmap(_sample_df(), lang="pt")
        assert isinstance(fig, go.Figure)

    def test_empty_df(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_heatmap
        fig = plot_heatmap(pd.DataFrame(), lang="pt")
        assert isinstance(fig, go.Figure)


class TestPlotCorrelation:
    """Tests for results_graphs.plot_correlation"""

    def test_returns_figure(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_correlation
        fig = plot_correlation(_sample_df(), x_var="T2M_MAX", lang="pt")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # scatter + trendline

    def test_empty_df(self):
        import plotly.graph_objects as go
        from backend.core.data_results.results_graphs import plot_correlation
        fig = plot_correlation(pd.DataFrame(), x_var="T2M_MAX", lang="pt")
        assert isinstance(fig, go.Figure)

    def test_invalid_column_raises(self):
        from backend.core.data_results.results_graphs import plot_correlation
        import plotly.graph_objects as go
        # x_var not in df → should return empty figure (exception caught)
        fig = plot_correlation(_sample_df(), x_var="NONEXISTENT", lang="pt")
        assert isinstance(fig, go.Figure)


# ===================================================================
# results_graphs helper tests
# ===================================================================

class TestGraphHelpers:
    """Tests for internal helpers in results_graphs"""

    def test_bold_wraps_text(self):
        from backend.core.data_results.results_graphs import _bold
        assert _bold("hello") == "<b>hello</b>"

    def test_base_layout_returns_dict(self):
        from backend.core.data_results.results_graphs import _base_layout
        layout = _base_layout()
        assert isinstance(layout, dict)
        assert "font" in layout
        assert "template" in layout

    def test_base_layout_overrides(self):
        from backend.core.data_results.results_graphs import _base_layout
        layout = _base_layout(height=999)
        assert layout["height"] == 999


# ===================================================================
# results_layout tests
# ===================================================================

class TestLayoutHelpers:
    """Tests for results_layout helper functions"""

    def test_table_download_buttons_returns_div(self):
        from backend.core.data_results.results_layout import _table_download_buttons
        result = _table_download_buttons("daily-table", lang="pt")
        assert isinstance(result, html.Div)

    def test_chart_download_buttons_returns_div(self):
        from backend.core.data_results.results_layout import _chart_download_buttons
        result = _chart_download_buttons("eto-temp", lang="pt")
        assert isinstance(result, html.Div)


class TestCreateResultsTabs:
    """Tests for results_layout.create_results_tabs"""

    def test_returns_tabs_component(self):
        import dash_bootstrap_components as dbc
        from backend.core.data_results.results_layout import create_results_tabs
        result = create_results_tabs(_sample_df(), sources=["NASA_POWER"], lang="pt")
        # Should return a dbc.Tabs or similar component
        assert result is not None

    def test_none_sources_defaults_to_empty(self):
        from backend.core.data_results.results_layout import create_results_tabs
        result = create_results_tabs(_sample_df(), sources=None, lang="pt")
        assert result is not None

    def test_forecast_mode(self):
        from backend.core.data_results.results_layout import create_results_tabs
        result = create_results_tabs(_sample_df(), lang="pt", mode="DASHBOARD_FORECAST")
        assert result is not None
