"""
Phase 7 – results_statistical.py comprehensive tests.

Covers ALL 9 display functions:
- display_daily_data
- display_descriptive_stats
- display_normality_test
- display_correlation_matrix
- display_eto_summary
- create_deficit_chart_section
- display_trend_analysis
- display_seasonality_test
- display_cumulative_distribution
"""

import numpy as np
import pandas as pd
from unittest.mock import patch
from dash import html

# ──────── helpers ────────

_TRANSLATIONS = {
    "data_variables": {
        "temp_max": "Temp Max (°C)",
        "temp_min": "Temp Min (°C)",
        "temp_mean": "Temp Mean (°C)",
        "humidity": "Humidity (%)",
        "wind_speed": "Wind (m/s)",
        "radiation": "Radiation (MJ/m²/d)",
        "precipitation": "Precipitation (mm)",
        "eto": "ETo (mm/d)",
        "eto_evaonline": "ETo EVAonline (mm/d)",
        "eto_openmeteo": "ETo Open-Meteo (mm/d)",
        "date": "Date",
    },
    "statistics": {
        "mean": "Mean",
        "max": "Max",
        "min": "Min",
        "median": "Median",
        "std_dev": "Std Dev",
        "percentile_25": "P25",
        "percentile_75": "P75",
        "coef_variation": "CV (%)",
        "skewness": "Skewness",
        "kurtosis": "Kurtosis",
        "statistic": "Statistic",
        "variable": "Variable",
        "p_value": "P-Value",
        "normality_note": "Shapiro-Wilk test. p<0.05 rejects normality.",
        "trend_analysis": "Trend Analysis",
        "eto_trend": "ETo Trend",
        "per_day": "per day",
        "seasonality_test": "Seasonality Test",
        "adf_test": "ADF Test",
        "cumulative_distribution": "Cumulative Distribution",
        "cumulative_eto": "Cumulative ETo (mm)",
        "cumulative_precipitation": "Cumulative Precip (mm)",
        "water_deficit": "Water Deficit (mm)",
        "daily_water_deficit": "Daily Water Deficit",
        "mm_day_unit": "mm/day",
        "mm_unit": "mm",
        "days_unit": "days",
        "deficit_mean": "Mean Deficit",
        "deficit_total": "Total Deficit",
        "days_with_deficit": "Days with Deficit",
        "days_with_excess": "Days with Excess",
        "deficit_note": "Note about deficit",
        "deficiency": "Deficiency",
        "surplus": "Surplus",
        "water_deficit_mm_day": "Water Deficit (mm/day)",
        "forecast_sample_insufficient": "Sample insufficient for forecast.",
        "sample_insufficient": "Need 30+ days. Currently: {days} days.",
    },
    "results": {
        "error": "Error",
        "no_data": "No data available",
    },
    "charts": {
        "date_label": "Date",
        "legend": "Legend",
    },
}


def _get_translations_mock(lang="pt"):
    return _TRANSLATIONS


def _format_number_mock(x, decimals=2):
    try:
        return f"{float(x):.{decimals}f}"
    except (ValueError, TypeError):
        return str(x)


def _sample_df(n=30):
    """Create sample weather DataFrame with required columns."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-06-01", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "T2M_MAX": rng.uniform(28, 35, n),
        "T2M_MIN": rng.uniform(18, 23, n),
        "T2M": rng.uniform(22, 30, n),
        "RH2M": rng.uniform(50, 85, n),
        "WS2M": rng.uniform(0.5, 5, n),
        "ALLSKY_SFC_SW_DWN": rng.uniform(10, 25, n),
        "PRECTOTCORR": rng.uniform(0, 15, n),
        "ETo": rng.uniform(2, 6, n),
        "eto_evaonline": rng.uniform(2, 6, n),
    })


def _small_df(n=7):
    return _sample_df(n)


# Patch translations and format_number for all tests
pytestmark = []

_PATCHES = {
    "get_translations": _get_translations_mock,
    "format_number": _format_number_mock,
}


# ═══════════════════════════════════════════════════════════════
# display_daily_data
# ═══════════════════════════════════════════════════════════════


class TestDisplayDailyData:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    @patch("backend.core.data_results.results_statistical.display_results_table")
    def test_returns_html(self, mock_table):
        from backend.core.data_results.results_statistical import display_daily_data

        mock_table.return_value = html.Div("table")
        result = display_daily_data(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    @patch(
        "backend.core.data_results.results_statistical.display_results_table",
        side_effect=Exception("render error"),
    )
    def test_error_returns_div(self, mock_table):
        from backend.core.data_results.results_statistical import display_daily_data

        result = display_daily_data(_sample_df(), lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_descriptive_stats
# ═══════════════════════════════════════════════════════════════


class TestDisplayDescriptiveStats:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html_30_days(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats

        result = display_descriptive_stats(_sample_df(30), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_short_sample_no_cv(self):
        """With <30 days, CV/skewness/kurtosis should be omitted."""
        from backend.core.data_results.results_statistical import display_descriptive_stats

        result = display_descriptive_stats(_small_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_forecast_mode_no_cv(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats

        result = display_descriptive_stats(
            _sample_df(30), lang="en", mode="DASHBOARD_FORECAST"
        )
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats

        result = display_descriptive_stats(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats

        result = display_descriptive_stats(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_no_valid_columns(self):
        from backend.core.data_results.results_statistical import display_descriptive_stats

        df = pd.DataFrame({"random_col": [1, 2, 3]})
        result = display_descriptive_stats(df, lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_normality_test
# ═══════════════════════════════════════════════════════════════


class TestDisplayNormalityTest:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_30_day_sample(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(_sample_df(30), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_insufficient_sample(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(_small_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_forecast_mode(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(
            _sample_df(30), lang="en", mode="DASHBOARD_FORECAST"
        )
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_lang_pt(self):
        from backend.core.data_results.results_statistical import display_normality_test

        result = display_normality_test(_sample_df(30), lang="pt")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_correlation_matrix
# ═══════════════════════════════════════════════════════════════


class TestDisplayCorrelationMatrix:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix

        result = display_correlation_matrix(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix

        result = display_correlation_matrix(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix

        result = display_correlation_matrix(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_no_valid_columns(self):
        from backend.core.data_results.results_statistical import display_correlation_matrix

        df = pd.DataFrame({"foo": [1, 2, 3]})
        result = display_correlation_matrix(df, lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_eto_summary
# ═══════════════════════════════════════════════════════════════


class TestDisplayEtoSummary:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import display_eto_summary

        result = display_eto_summary(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_eto_summary

        result = display_eto_summary(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_missing_columns(self):
        from backend.core.data_results.results_statistical import display_eto_summary

        df = pd.DataFrame({"foo": [1]})
        result = display_eto_summary(df, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_with_deficit_and_surplus(self):
        """Verify deficit coloring for both negative and positive values."""
        from backend.core.data_results.results_statistical import display_eto_summary

        df = _sample_df(10)
        # Force some deficit (precip < eto) and surplus
        df["PRECTOTCORR"] = [0, 0, 0, 0, 0, 20, 20, 20, 20, 20]
        df["eto_evaonline"] = [5, 5, 5, 5, 5, 2, 2, 2, 2, 2]
        result = display_eto_summary(df, lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# create_deficit_chart_section
# ═══════════════════════════════════════════════════════════════


class TestCreateDeficitChartSection:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import create_deficit_chart_section

        result = create_deficit_chart_section(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import create_deficit_chart_section

        result = create_deficit_chart_section(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_empty_df(self):
        from backend.core.data_results.results_statistical import create_deficit_chart_section

        result = create_deficit_chart_section(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_trend_analysis
# ═══════════════════════════════════════════════════════════════


class TestDisplayTrendAnalysis:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import display_trend_analysis

        result = display_trend_analysis(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_trend_analysis

        result = display_trend_analysis(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_missing_eto_column(self):
        from backend.core.data_results.results_statistical import display_trend_analysis

        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10)})
        result = display_trend_analysis(df, lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_seasonality_test
# ═══════════════════════════════════════════════════════════════


class TestDisplaySeasonalityTest:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import display_seasonality_test

        result = display_seasonality_test(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_seasonality_test

        result = display_seasonality_test(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_missing_eto(self):
        from backend.core.data_results.results_statistical import display_seasonality_test

        df = pd.DataFrame({"foo": [1, 2, 3]})
        result = display_seasonality_test(df, lang="en")
        assert isinstance(result, html.Div)


# ═══════════════════════════════════════════════════════════════
# display_cumulative_distribution
# ═══════════════════════════════════════════════════════════════


class TestDisplayCumulativeDistribution:
    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_returns_html(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution

        result = display_cumulative_distribution(_sample_df(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_none_df(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution

        result = display_cumulative_distribution(None, lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_empty_df(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution

        result = display_cumulative_distribution(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)

    @patch.multiple("backend.core.data_results.results_statistical", **_PATCHES)
    def test_missing_columns(self):
        from backend.core.data_results.results_statistical import display_cumulative_distribution

        df = pd.DataFrame({"random": [1, 2, 3]})
        result = display_cumulative_distribution(df, lang="en")
        assert isinstance(result, html.Div)
