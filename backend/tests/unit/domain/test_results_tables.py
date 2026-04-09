"""
Unit Tests – backend.core.data_results.results_tables

Tests for format_number() and display_results_table().

Reference columns (NASA POWER API names):
  date, T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN,
  PRECTOTCORR, eto_evaonline (or legacy ETo)
"""

import numpy as np
import pandas as pd
import pytest
from dash import html
from unittest.mock import patch

from backend.core.data_results.results_tables import (
    display_results_table,
    format_number,
)


# ============================================================================
# Helpers / Fixtures
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
    },
    "results": {"error": "Error", "no_data": "No data available"},
}


@pytest.fixture
def climate_df():
    """Minimal valid climate DataFrame (7 days)."""
    dates = pd.date_range("2024-01-01", periods=7, freq="D")
    np.random.seed(0)
    return pd.DataFrame(
        {
            "date": dates,
            "T2M_MAX": np.random.uniform(28, 36, 7),
            "T2M_MIN": np.random.uniform(18, 24, 7),
            "RH2M": np.random.uniform(50, 80, 7),
            "WS2M": np.random.uniform(1, 5, 7),
            "ALLSKY_SFC_SW_DWN": np.random.uniform(12, 25, 7),
            "PRECTOTCORR": np.random.uniform(0, 10, 7),
            "eto_evaonline": np.random.uniform(3, 7, 7),
        }
    )


@pytest.fixture
def climate_df_legacy_eto():
    """DataFrame using the legacy 'ETo' column name."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    np.random.seed(1)
    return pd.DataFrame(
        {
            "date": dates,
            "T2M_MAX": np.random.uniform(28, 36, 5),
            "T2M_MIN": np.random.uniform(18, 24, 5),
            "RH2M": np.random.uniform(50, 80, 5),
            "WS2M": np.random.uniform(1, 5, 5),
            "ALLSKY_SFC_SW_DWN": np.random.uniform(12, 25, 5),
            "PRECTOTCORR": np.random.uniform(0, 10, 5),
            "ETo": np.random.uniform(3, 7, 5),
        }
    )


# ============================================================================
# Tests – format_number
# ============================================================================


class TestFormatNumber:
    """Tests for the format_number() helper."""

    def test_formats_integer(self):
        assert format_number(5) == "5.00"

    def test_formats_float(self):
        assert format_number(3.14159, 3) == "3.142"

    def test_nan_returns_dash(self):
        assert format_number(np.nan) == "-"
        assert format_number(float("nan")) == "-"

    def test_none_returns_dash(self):
        assert format_number(None) == "-"

    def test_zero(self):
        assert format_number(0) == "0.00"

    def test_negative(self):
        assert format_number(-2.5, 1) == "-2.5"

    def test_string_numeric(self):
        assert format_number("3.7", 2) == "3.70"

    def test_non_numeric_string(self):
        assert format_number("abc") == "abc"

    def test_custom_decimals(self):
        assert format_number(1.23456, 4) == "1.2346"


# ============================================================================
# Tests – display_results_table
# ============================================================================


class TestDisplayResultsTable:
    """Tests for display_results_table()."""

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_returns_html_div(self, _mock_t, climate_df):
        result = display_results_table(climate_df, lang="en")
        assert isinstance(result, html.Div)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_empty_dataframe(self, _mock_t):
        result = display_results_table(pd.DataFrame(), lang="en")
        assert isinstance(result, html.Div)
        # Should contain a warning message, not a table
        assert "Nenhum dado" in str(result) or "disponível" in str(result)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_none_dataframe(self, _mock_t):
        result = display_results_table(None, lang="en")
        assert isinstance(result, html.Div)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_missing_date_column(self, _mock_t):
        df = pd.DataFrame({"eto_evaonline": [1, 2, 3]})
        result = display_results_table(df, lang="en")
        assert isinstance(result, html.Div)
        # Error because 'date' is mandatory
        assert "date" in str(result).lower() or "erro" in str(result).lower() or "Erro" in str(result)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_missing_eto_column(self, _mock_t):
        df = pd.DataFrame(
            {"date": pd.date_range("2024-01-01", periods=3), "T2M_MAX": [30, 31, 32]}
        )
        result = display_results_table(df, lang="en")
        assert isinstance(result, html.Div)
        # Error because at least one ETo column is required
        assert "ETo" in str(result) or "Erro" in str(result)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_legacy_eto_column(self, _mock_t, climate_df_legacy_eto):
        """The function should accept legacy 'ETo' column."""
        result = display_results_table(climate_df_legacy_eto, lang="en")
        assert isinstance(result, html.Div)
        # Should contain a table, not an error
        assert "Erro" not in str(result) or "table" in str(result).lower()

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_partial_columns(self, _mock_t):
        """Only date + eto_evaonline should still produce a table."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "eto_evaonline": [4.1, 5.2, 3.8],
            }
        )
        result = display_results_table(df, lang="en")
        assert isinstance(result, html.Div)

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_date_formatted_as_dd_mm_yyyy(self, _mock_t, climate_df):
        """Dates should be formatted as dd/mm/YYYY in the output."""
        result = display_results_table(climate_df, lang="en")
        rendered = str(result)
        assert "01/01/2024" in rendered

    @patch(
        "backend.core.data_results.results_tables.get_translations",
        return_value=MOCK_TRANSLATIONS,
    )
    def test_lang_parameter_forwarded(self, mock_t, climate_df):
        display_results_table(climate_df, lang="pt")
        mock_t.assert_called_with("pt")
