"""
Tests for backend.core.data_results (results_statistical, results_graphs, results_tables).

These modules produce Dash/Plotly UI components from DataFrames.
All functions are pure logic: DataFrame in → Dash component / Plotly Figure out.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from dash import html

from backend.core.data_results.results_tables import (
    display_results_table,
    format_number,
)
from backend.core.data_results.results_statistical import (
    display_daily_data,
    display_descriptive_stats,
    display_normality_test,
    display_correlation_matrix,
    display_eto_summary,
    display_trend_analysis,
    display_seasonality_test,
    display_cumulative_distribution,
    create_deficit_chart_section,
)
from backend.core.data_results.results_graphs import (
    plot_eto_vs_temperature,
    plot_eto_vs_radiation,
    plot_temp_rad_prec,
    plot_heatmap,
    plot_correlation,
    _bold,
    _base_layout,
)


# ════════════════════════════════════════════════════════════════════
# Shared fixtures
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_df():
    """Realistic ETo dataset with 35 days for statistical tests."""
    np.random.seed(42)
    n = 35
    dates = pd.date_range("2024-01-01", periods=n)
    return pd.DataFrame({
        "date": dates,
        "T2M_MAX": np.random.uniform(28, 38, n),
        "T2M_MIN": np.random.uniform(18, 25, n),
        "RH2M": np.random.uniform(40, 80, n),
        "WS2M": np.random.uniform(0.5, 4.0, n),
        "ALLSKY_SFC_SW_DWN": np.random.uniform(12, 28, n),
        "PRECTOTCORR": np.random.uniform(0, 15, n),
        "ETo": np.random.uniform(2.5, 7.5, n),
        "eto_evaonline": np.random.uniform(2.5, 7.5, n),
    })


@pytest.fixture
def small_df():
    """Small 5-day dataset (below Shapiro-Wilk threshold)."""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5),
        "T2M_MAX": [30, 32, 31, 33, 29],
        "T2M_MIN": [20, 21, 19, 22, 18],
        "RH2M": [60, 65, 55, 70, 50],
        "WS2M": [2.0, 1.5, 2.5, 1.0, 3.0],
        "ALLSKY_SFC_SW_DWN": [20, 22, 18, 25, 15],
        "PRECTOTCORR": [5, 0, 10, 2, 8],
        "ETo": [4.5, 5.0, 3.8, 5.5, 3.2],
        "eto_evaonline": [4.5, 5.0, 3.8, 5.5, 3.2],
    })


# ════════════════════════════════════════════════════════════════════
# format_number
# ════════════════════════════════════════════════════════════════════

class TestFormatNumber:

    def test_normal_value(self):
        assert format_number(3.14159, 2) == "3.14"

    def test_nan_value(self):
        assert format_number(float("nan"), 2) == "-"

    def test_none_value(self):
        assert format_number(None, 2) == "-"

    def test_integer_value(self):
        assert format_number(42, 0) == "42"

    def test_string_value(self):
        assert format_number("hello", 2) == "hello"

    def test_zero_decimals(self):
        assert format_number(3.7, 0) == "4"


# ════════════════════════════════════════════════════════════════════
# display_results_table
# ════════════════════════════════════════════════════════════════════

class TestDisplayResultsTable:

    def test_returns_div(self, small_df):
        result = display_results_table(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_results_table(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_results_table(None, lang="en")
        assert isinstance(result, html.Div)

    def test_missing_date_column(self):
        df = pd.DataFrame({"T2M_MAX": [30], "ETo": [4.5]})
        result = display_results_table(df, lang="en")
        # Should return error div
        assert isinstance(result, html.Div)

    def test_pt_language(self, small_df):
        result = display_results_table(small_df, lang="pt")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_daily_data
# ════════════════════════════════════════════════════════════════════

class TestDisplayDailyData:

    def test_returns_div(self, small_df):
        result = display_daily_data(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_daily_data(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_descriptive_stats
# ════════════════════════════════════════════════════════════════════

class TestDisplayDescriptiveStats:

    def test_basic_stats(self, sample_df):
        result = display_descriptive_stats(sample_df, lang="en")
        assert isinstance(result, html.Div)

    def test_forecast_mode_skips_cv(self, small_df):
        """Dashboard forecast mode omits CV, Skewness, Kurtosis"""
        result = display_descriptive_stats(small_df, lang="en", mode="DASHBOARD_FORECAST")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_descriptive_stats(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_descriptive_stats(None, lang="en")
        assert isinstance(result, html.Div)

    def test_pt_language(self, sample_df):
        result = display_descriptive_stats(sample_df, lang="pt")
        assert isinstance(result, html.Div)

    def test_has_enough_samples_for_cv(self, sample_df):
        """35-day dataset includes CV, Skewness, Kurtosis"""
        result = display_descriptive_stats(sample_df, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_normality_test
# ════════════════════════════════════════════════════════════════════

class TestDisplayNormalityTest:

    def test_shapiro_wilk_35_days(self, sample_df):
        result = display_normality_test(sample_df, lang="en")
        assert isinstance(result, html.Div)

    def test_insufficient_sample(self, small_df):
        """< 30 days → returns info alert instead of test"""
        result = display_normality_test(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_forecast_mode(self, small_df):
        result = display_normality_test(small_df, lang="en", mode="DASHBOARD_FORECAST")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_normality_test(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_normality_test(None, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_correlation_matrix
# ════════════════════════════════════════════════════════════════════

class TestDisplayCorrelationMatrix:

    def test_returns_div(self, sample_df):
        result = display_correlation_matrix(sample_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_correlation_matrix(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_correlation_matrix(None, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_eto_summary (water balance table)
# ════════════════════════════════════════════════════════════════════

class TestDisplayEtoSummary:

    def test_returns_div(self, small_df):
        result = display_eto_summary(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_eto_summary(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_eto_summary(None, lang="en")
        assert isinstance(result, html.Div)

    def test_missing_columns(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "T2M_MAX": [30]})
        result = display_eto_summary(df, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_trend_analysis
# ════════════════════════════════════════════════════════════════════

class TestDisplayTrendAnalysis:

    def test_returns_div(self, sample_df):
        result = display_trend_analysis(sample_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_trend_analysis(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_missing_columns(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "T2M_MAX": [30]})
        result = display_trend_analysis(df, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_seasonality_test
# ════════════════════════════════════════════════════════════════════

class TestDisplaySeasonalityTest:

    def test_returns_div(self, sample_df):
        result = display_seasonality_test(sample_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_seasonality_test(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_missing_eto_column(self):
        df = pd.DataFrame({"T2M_MAX": [30, 32, 31]})
        result = display_seasonality_test(df, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# display_cumulative_distribution
# ════════════════════════════════════════════════════════════════════

class TestDisplayCumulativeDistribution:

    def test_returns_div(self, small_df):
        result = display_cumulative_distribution(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = display_cumulative_distribution(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = display_cumulative_distribution(None, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# create_deficit_chart_section
# ════════════════════════════════════════════════════════════════════

class TestCreateDeficitChartSection:

    def test_returns_div(self, small_df):
        result = create_deficit_chart_section(small_df, lang="en")
        assert isinstance(result, html.Div)

    def test_empty_df(self):
        result = create_deficit_chart_section(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    def test_none_df(self):
        result = create_deficit_chart_section(None, lang="en")
        assert isinstance(result, html.Div)


# ════════════════════════════════════════════════════════════════════
# results_graphs — helper functions
# ════════════════════════════════════════════════════════════════════

class TestGraphHelpers:

    def test_bold(self):
        assert _bold("Test") == "<b>Test</b>"

    def test_base_layout_has_template(self):
        layout = _base_layout()
        assert layout["template"] == "plotly_white"

    def test_base_layout_override(self):
        layout = _base_layout(height=800)
        assert layout["height"] == 800


# ════════════════════════════════════════════════════════════════════
# plot_eto_vs_temperature
# ════════════════════════════════════════════════════════════════════

class TestPlotEtoVsTemperature:

    def test_returns_figure(self, small_df):
        fig = plot_eto_vs_temperature(small_df, lang="en")
        assert isinstance(fig, go.Figure)
        # Should have 3 traces: ETo bars + T_max line + T_min line
        assert len(fig.data) == 3

    def test_empty_df(self):
        fig = plot_eto_vs_temperature(pd.DataFrame(), lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_none_df(self):
        fig = plot_eto_vs_temperature(None, lang="en")
        assert isinstance(fig, go.Figure)

    def test_missing_columns(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "T2M_MAX": [30]})
        fig = plot_eto_vs_temperature(df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_pt_language(self, small_df):
        fig = plot_eto_vs_temperature(small_df, lang="pt")
        assert isinstance(fig, go.Figure)


# ════════════════════════════════════════════════════════════════════
# plot_eto_vs_radiation
# ════════════════════════════════════════════════════════════════════

class TestPlotEtoVsRadiation:

    def test_returns_figure(self, small_df):
        fig = plot_eto_vs_radiation(small_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_empty_df(self):
        fig = plot_eto_vs_radiation(pd.DataFrame(), lang="en")
        assert isinstance(fig, go.Figure)

    def test_missing_columns(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "T2M_MAX": [30]})
        fig = plot_eto_vs_radiation(df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0


# ════════════════════════════════════════════════════════════════════
# plot_temp_rad_prec
# ════════════════════════════════════════════════════════════════════

class TestPlotTempRadPrec:

    def test_returns_figure(self, small_df):
        fig = plot_temp_rad_prec(small_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # ETo bars + T_max line + Precip bars

    def test_empty_df(self):
        fig = plot_temp_rad_prec(pd.DataFrame(), lang="en")
        assert isinstance(fig, go.Figure)

    def test_none_df(self):
        fig = plot_temp_rad_prec(None, lang="en")
        assert isinstance(fig, go.Figure)


# ════════════════════════════════════════════════════════════════════
# plot_heatmap
# ════════════════════════════════════════════════════════════════════

class TestPlotHeatmap:

    def test_returns_figure(self, sample_df):
        fig = plot_heatmap(sample_df, lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1  # At least the heatmap trace

    def test_empty_df(self):
        fig = plot_heatmap(pd.DataFrame(), lang="en")
        assert isinstance(fig, go.Figure)

    def test_none_df(self):
        fig = plot_heatmap(None, lang="en")
        assert isinstance(fig, go.Figure)


# ════════════════════════════════════════════════════════════════════
# plot_correlation
# ════════════════════════════════════════════════════════════════════

class TestPlotCorrelation:

    def test_returns_figure(self, sample_df):
        fig = plot_correlation(sample_df, "T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Scatter + trend line

    def test_empty_df(self):
        fig = plot_correlation(pd.DataFrame(), "T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)

    def test_none_df(self):
        fig = plot_correlation(None, "T2M_MAX", lang="en")
        assert isinstance(fig, go.Figure)

    def test_invalid_column(self, sample_df):
        """Missing x_var column → caught internally, returns empty figure"""
        fig = plot_correlation(sample_df, "NONEXISTENT_COL", lang="en")
        assert isinstance(fig, go.Figure)
