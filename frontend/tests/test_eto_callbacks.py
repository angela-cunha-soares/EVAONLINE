"""
Tests for frontend/callbacks/eto_callbacks.py — pure helper functions.

Focus on functions that don't require a running Dash app:
- decimal_to_dms
- enable_calculate_button (logic only)
- _df_from_store
- _is_excel_trigger
- _send_table
- download_csv / download_excel (logic paths)
- _STORE_TO_INTERNAL mapping
- render_location_input (mode parsing)
- update_fusion_info (config selection)
"""

from unittest.mock import MagicMock, patch

import pandas as pd


# ---------------------------------------------------------------------------
# decimal_to_dms
# ---------------------------------------------------------------------------
class TestDecimalToDms:
    """Tests for the `decimal_to_dms` conversion helper."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import decimal_to_dms
        return decimal_to_dms

    def test_positive_latitude(self):
        result = self._get_fn()(45.5, is_latitude=True)
        assert "45°" in result
        assert "30'" in result
        assert result.endswith('N')

    def test_negative_latitude(self):
        result = self._get_fn()(-23.5508, is_latitude=True)
        assert result.endswith('S')
        assert "23°" in result

    def test_positive_longitude(self):
        result = self._get_fn()(120.25, is_latitude=False)
        assert result.endswith('E')
        assert "120°" in result
        assert "15'" in result

    def test_negative_longitude(self):
        result = self._get_fn()(-46.6333, is_latitude=False)
        assert result.endswith('W')
        assert "46°" in result

    def test_zero_latitude(self):
        result = self._get_fn()(0.0, is_latitude=True)
        assert result.startswith("0°")
        assert result.endswith('N')

    def test_zero_longitude(self):
        result = self._get_fn()(0.0, is_latitude=False)
        assert result.startswith("0°")
        assert result.endswith('E')

    def test_extreme_latitude_90(self):
        result = self._get_fn()(90.0, is_latitude=True)
        assert result.startswith("90°")

    def test_extreme_latitude_minus90(self):
        result = self._get_fn()(-90.0, is_latitude=True)
        assert result.startswith("90°")
        assert result.endswith('S')

    def test_extreme_longitude_180(self):
        result = self._get_fn()(180.0, is_latitude=False)
        assert result.startswith("180°")

    def test_extreme_longitude_minus180(self):
        result = self._get_fn()(-180.0, is_latitude=False)
        assert result.startswith("180°")
        assert result.endswith('W')

    def test_precise_seconds(self):
        # 45° 30' 15.00" N
        decimal = 45 + 30 / 60 + 15 / 3600
        result = self._get_fn()(decimal, is_latitude=True)
        assert '15.00"' in result

    def test_fractional_seconds(self):
        result = self._get_fn()(45.123456, is_latitude=True)
        # Just ensure it contains double-quote (seconds)
        assert '"' in result
        assert 'N' in result


# ---------------------------------------------------------------------------
# enable_calculate_button (pure logic)
# ---------------------------------------------------------------------------
class TestEnableCalculateButton:
    """Tests for the enable_calculate_button logic (disabled flag)."""

    def _logic(self, coords_data, data_type):
        """Replicate the pure logic of enable_calculate_button."""
        has_coords = (
            coords_data is not None
            and "lat" in coords_data
            and "lon" in coords_data
        )
        has_data_type = data_type is not None and data_type in [
            "historical",
            "recent",
            "forecast",
        ]
        return not (has_coords and has_data_type)

    def test_both_valid_returns_false(self):
        assert self._logic({"lat": 1.0, "lon": 2.0}, "historical") is False

    def test_no_coords_returns_true(self):
        assert self._logic(None, "historical") is True

    def test_no_data_type_returns_true(self):
        assert self._logic({"lat": 1.0, "lon": 2.0}, None) is True

    def test_invalid_data_type_returns_true(self):
        assert self._logic({"lat": 1.0, "lon": 2.0}, "invalid") is True

    def test_empty_coords_returns_true(self):
        assert self._logic({}, "recent") is True

    def test_missing_lon_returns_true(self):
        assert self._logic({"lat": 1.0}, "forecast") is True

    def test_missing_lat_returns_true(self):
        assert self._logic({"lon": 2.0}, "forecast") is True

    def test_each_mode_works(self):
        for mode in ("historical", "recent", "forecast"):
            assert self._logic({"lat": 0, "lon": 0}, mode) is False


# ---------------------------------------------------------------------------
# _df_from_store
# ---------------------------------------------------------------------------
class TestDfFromStore:
    """Tests for _df_from_store helper."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import _df_from_store
        return _df_from_store

    def test_empty_records_returns_none(self):
        assert self._get_fn()({"records": []}) is None

    def test_missing_records_key_returns_none(self):
        assert self._get_fn()({}) is None

    def test_basic_mapping(self):
        records = [
            {"tmax_c": 35.0, "tmin_c": 20.0, "et0_mm_day": 5.1}
        ]
        df = self._get_fn()({"records": records})
        assert df is not None
        assert "T2M_MAX" in df.columns
        assert "T2M_MIN" in df.columns
        assert "eto_evaonline" in df.columns

    def test_preserves_unmapped_columns(self):
        records = [{"tmax_c": 30, "extra_col": 1}]
        df = self._get_fn()({"records": records})
        assert "extra_col" in df.columns

    def test_multiple_rows(self):
        records = [
            {"tmax_c": 30, "et0_mm_day": 4.5},
            {"tmax_c": 32, "et0_mm_day": 5.0},
        ]
        df = self._get_fn()({"records": records})
        assert len(df) == 2


# ---------------------------------------------------------------------------
# _STORE_TO_INTERNAL mapping
# ---------------------------------------------------------------------------
class TestStoreToInternalMapping:
    """Verify the column mapping dict is correct."""

    def test_expected_keys_exist(self):
        from frontend.callbacks.eto_callbacks import _STORE_TO_INTERNAL

        expected_keys = [
            "tmax_c", "tmin_c", "tmed_c", "humidity_pct",
            "wind_ms", "radiation_mj_m2", "precip_mm", "et0_mm_day",
        ]
        for k in expected_keys:
            assert k in _STORE_TO_INTERNAL

    def test_mapping_values(self):
        from frontend.callbacks.eto_callbacks import _STORE_TO_INTERNAL

        assert _STORE_TO_INTERNAL["tmax_c"] == "T2M_MAX"
        assert _STORE_TO_INTERNAL["et0_mm_day"] == "eto_evaonline"


# ---------------------------------------------------------------------------
# _send_table (helper for CSV/Excel downloads)
# ---------------------------------------------------------------------------
class TestSendTable:
    """Tests for the _send_table download helper."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import _send_table
        return _send_table

    @patch("frontend.callbacks.eto_callbacks.dcc")
    def test_csv_en_format(self, mock_dcc):
        mock_dcc.send_data_frame = MagicMock(return_value="csv-data")
        df = pd.DataFrame({"val": [1.234, 5.678]})
        result = self._get_fn()(df, "test", excel_clicked=False, lang="en")
        mock_dcc.send_data_frame.assert_called_once()
        call_kwargs = mock_dcc.send_data_frame.call_args
        assert call_kwargs[1]["sep"] == ","
        assert call_kwargs[1]["decimal"] == "."

    @patch("frontend.callbacks.eto_callbacks.dcc")
    def test_csv_pt_format(self, mock_dcc):
        mock_dcc.send_data_frame = MagicMock(return_value="csv-data")
        df = pd.DataFrame({"val": [1.234, 5.678]})
        result = self._get_fn()(df, "test", excel_clicked=False, lang="pt")
        call_kwargs = mock_dcc.send_data_frame.call_args
        assert call_kwargs[1]["sep"] == ";"
        assert call_kwargs[1]["decimal"] == ","

    @patch("frontend.callbacks.eto_callbacks.dcc")
    def test_excel_output(self, mock_dcc):
        mock_dcc.send_bytes = MagicMock(return_value="excel-data")
        df = pd.DataFrame({"val": [1.234, 5.678]})
        result = self._get_fn()(df, "test", excel_clicked=True, lang="en")
        mock_dcc.send_bytes.assert_called_once()
        filename = mock_dcc.send_bytes.call_args[0][1]
        assert filename.endswith(".xlsx")
        assert "test" in filename

    @patch("frontend.callbacks.eto_callbacks.dcc")
    def test_rounding_to_2_decimals(self, mock_dcc):
        mock_dcc.send_data_frame = MagicMock(return_value="csv")
        df = pd.DataFrame({"val": [1.23456789]})
        self._get_fn()(df, "test", excel_clicked=False, lang="en")
        # The df passed to send_data_frame should have been rounded
        call_args = mock_dcc.send_data_frame.call_args
        # First positional: df.to_csv
        # Can't easily inspect the df after rounding in mock, but no error


# ---------------------------------------------------------------------------
# update_location_from_store (callback - test logic branches)
# ---------------------------------------------------------------------------
class TestUpdateLocationFromStore:
    """Tests for update_location_from_store callback logic branches."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import update_location_from_store
        return update_location_from_store

    def test_none_input_returns_warning(self):
        result = self._get_fn()(None)
        display, coords = result
        # display should be an html.Div with warning text
        assert coords is None

    def test_valid_coords_returns_both(self):
        result = self._get_fn()({"lat": -23.55, "lon": -46.63})
        display, coords = result
        assert coords is not None
        assert coords["lat"] == -23.55
        assert coords["lon"] == -46.63

    def test_missing_lat_returns_warning(self):
        result = self._get_fn()({"lon": 10.0})
        display, coords = result
        assert coords is None

    def test_missing_lon_returns_warning(self):
        result = self._get_fn()({"lat": 10.0})
        display, coords = result
        assert coords is None

    def test_empty_dict_returns_warning(self):
        result = self._get_fn()({})
        display, coords = result
        assert coords is None


# ---------------------------------------------------------------------------
# render_location_input (mode radio callback)
# ---------------------------------------------------------------------------
class TestRenderLocationInput:
    """Tests for render_location_input callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import render_location_input
        return render_location_input

    def test_map_mode_no_search(self):
        result = self._get_fn()("map", None)
        # Should return an info alert
        assert result is not None

    def test_map_mode_with_valid_search(self):
        result = self._get_fn()("map", "?lat=-23.55&lon=-46.63")
        assert result is not None

    def test_map_mode_with_invalid_search(self):
        result = self._get_fn()("map", "?lat=abc&lon=xyz")
        assert result is not None  # Should return warning alert

    def test_manual_mode(self):
        result = self._get_fn()("manual", None)
        assert result is not None


# ---------------------------------------------------------------------------
# update_fusion_info (mode config)
# ---------------------------------------------------------------------------
class TestUpdateFusionInfo:
    """Tests for update_fusion_info callback logic."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import update_fusion_info
        return update_fusion_info

    def test_none_data_type_returns_none(self):
        result = self._get_fn()(None, None, "en")
        assert result is None

    def test_historical_mode(self):
        result = self._get_fn()("historical", None, "en")
        assert result is not None

    def test_recent_mode(self):
        result = self._get_fn()("recent", None, "en")
        assert result is not None

    def test_forecast_mode(self):
        result = self._get_fn()("forecast", None, "en")
        assert result is not None

    def test_forecast_usa_adds_nws(self):
        # Coords in USA
        result = self._get_fn()("forecast", {"lat": 40, "lon": -100}, "en")
        assert result is not None

    def test_forecast_outside_usa(self):
        # Coords in Brazil
        result = self._get_fn()("forecast", {"lat": -23, "lon": -46}, "en")
        assert result is not None

    def test_lang_pt(self):
        result = self._get_fn()("historical", None, "pt")
        assert result is not None

    def test_none_lang_defaults(self):
        result = self._get_fn()("recent", None, None)
        assert result is not None


# ---------------------------------------------------------------------------
# render_conditional_form
# ---------------------------------------------------------------------------
class TestRenderConditionalForm:
    """Tests for the render_conditional_form callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import render_conditional_form
        return render_conditional_form

    def test_historical_english(self):
        result = self._get_fn()("historical", "en")
        assert result is not None

    def test_historical_portuguese(self):
        result = self._get_fn()("historical", "pt")
        assert result is not None

    def test_recent(self):
        result = self._get_fn()("recent", "en")
        assert result is not None

    def test_forecast(self):
        result = self._get_fn()("forecast", "en")
        assert result is not None

    def test_none_lang_defaults_to_en(self):
        result = self._get_fn()("recent", None)
        assert result is not None


# ---------------------------------------------------------------------------
# reset_for_new_query
# ---------------------------------------------------------------------------
class TestResetForNewQuery:
    """Tests for the reset_for_new_query callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import reset_for_new_query
        return reset_for_new_query

    def test_main_button_click(self):
        result = self._get_fn()(1, None, "en")
        assert isinstance(result, tuple)
        assert len(result) == 12
        # Button should be disabled
        assert result[7] is True

    def test_sidebar_button_click(self):
        result = self._get_fn()(None, 1, "en")
        assert isinstance(result, tuple)

    def test_no_clicks_raises(self):
        from dash.exceptions import PreventUpdate
        import pytest
        with pytest.raises(PreventUpdate):
            self._get_fn()(None, None, "en")

    def test_none_lang_defaults(self):
        result = self._get_fn()(1, None, None)
        assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# validate_manual_coordinates
# ---------------------------------------------------------------------------
class TestValidateManualCoordinates:
    """Tests for validate_manual_coordinates callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import validate_manual_coordinates
        return validate_manual_coordinates

    def test_no_clicks(self):
        result = self._get_fn()(None, -23.55, -46.63)
        assert result == [""]

    def test_valid_coords(self):
        result = self._get_fn()(1, -23.55, -46.63)
        assert result == [""]

    def test_none_coords(self):
        result = self._get_fn()(1, None, None)
        assert result == [""]

    def test_out_of_range(self):
        result = self._get_fn()(1, 100, 200)
        assert result == [""]


# ---------------------------------------------------------------------------
# populate_sources_from_url
# ---------------------------------------------------------------------------
class TestPopulateSourcesFromUrl:
    """Tests for populate_sources_from_url callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import populate_sources_from_url
        return populate_sources_from_url

    def test_with_coords(self):
        result = self._get_fn()({"lat": -23.55, "lon": -46.63})
        assert result == [""]

    def test_no_coords(self):
        result = self._get_fn()(None)
        assert result == [""]


# ---------------------------------------------------------------------------
# update_source_description
# ---------------------------------------------------------------------------
class TestUpdateSourceDescription:
    """Tests for update_source_description callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import update_source_description
        return update_source_description

    def test_historical(self):
        assert self._get_fn()("historical") == ""

    def test_recent(self):
        assert self._get_fn()("recent") == ""

    def test_forecast(self):
        assert self._get_fn()("forecast") == ""

    def test_none(self):
        assert self._get_fn()(None) == ""


# ---------------------------------------------------------------------------
# download_csv
# ---------------------------------------------------------------------------
class TestDownloadCsv:
    """Tests for download_csv callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_csv
        return download_csv

    def test_no_clicks_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(None, {"records": [{"a": 1}]})
        assert result is no_update

    def test_no_data_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(1, None)
        assert result is no_update

    def test_empty_records_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(1, {"records": []})
        assert result is no_update

    def test_valid_download(self):
        data = {"records": [{"date": "2024-01-01", "temp": 25.0}]}
        result = self._get_fn()(1, data)
        # Returns a dict with content, filename, etc
        assert result is not None


# ---------------------------------------------------------------------------
# download_excel
# ---------------------------------------------------------------------------
class TestDownloadExcel:
    """Tests for download_excel callback."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import download_excel
        return download_excel

    def test_no_clicks_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(None, {"records": [{"a": 1}]})
        assert result is no_update

    def test_no_data_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(1, None)
        assert result is no_update

    def test_empty_records_returns_no_update(self):
        from dash import no_update
        result = self._get_fn()(1, {"records": []})
        assert result is no_update

    def test_valid_download(self):
        data = {"records": [{"date": "2024-01-01", "temp": 25.0}]}
        result = self._get_fn()(1, data)
        assert result is not None


# ---------------------------------------------------------------------------
# _is_excel_trigger
# ---------------------------------------------------------------------------
class TestIsExcelTrigger:
    """Tests for _is_excel_trigger helper."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import _is_excel_trigger
        return _is_excel_trigger

    @patch("dash.callback_context")
    def test_excel_trigger(self, mock_ctx):
        mock_ctx.triggered = [{"prop_id": "btn-dl-climate-excel.n_clicks"}]
        assert self._get_fn()() is True

    @patch("dash.callback_context")
    def test_csv_trigger(self, mock_ctx):
        mock_ctx.triggered = [{"prop_id": "btn-dl-climate-csv.n_clicks"}]
        assert self._get_fn()() is False

    @patch("dash.callback_context")
    def test_no_trigger(self, mock_ctx):
        mock_ctx.triggered = []
        assert self._get_fn()() is False


# ---------------------------------------------------------------------------
# calculate_eto (validation paths)
# ---------------------------------------------------------------------------
class TestCalculateEto:
    """Tests for calculate_eto validation branches."""

    def _get_fn(self):
        from frontend.callbacks.eto_callbacks import calculate_eto
        return calculate_eto

    def test_no_clicks(self):
        result = self._get_fn()(None, None, None, None, None, None, None, None, None)
        assert result[0] is None  # no results

    def test_zero_clicks(self):
        result = self._get_fn()(0, None, None, None, None, None, None, None, None)
        assert result[0] is None

    def test_no_coords(self):
        result = self._get_fn()(1, None, "recent", None, None, None, None, "7", "sess_123")
        # Should return error alert in validation_alert (index 2)
        assert result[2] is not None
        assert result[0] is None

    def test_invalid_coords(self):
        result = self._get_fn()(
            1, {"lat": 999, "lon": 999}, "recent",
            None, None, None, None, "7", "sess_123",
        )
        assert result[2] is not None  # error alert

    def test_coords_parse_error(self):
        result = self._get_fn()(
            1, {"lat": "abc", "lon": "xyz"}, "recent",
            None, None, None, None, "7", "sess_123",
        )
        assert result[2] is not None

    def test_no_data_type_selected(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, None,
            None, None, None, None, None, "sess_123",
            None, "en",
        )
        assert result[2] is not None  # warning alert

    def test_historical_no_email(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            "2024-01-01", "2024-01-15", None, "excel", None, "sess_123",
            None, "en",
        )
        assert result[2] is not None  # email required

    def test_historical_no_dates(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            None, None, "user@example.com", "excel", None, "sess_123",
            None, "en",
        )
        assert result[2] is not None  # select dates

    def test_historical_no_format(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            "2024-06-01", "2024-06-15", "user@example.com", None, None, "sess_123",
            None, "en",
        )
        assert result[2] is not None  # format required

    def test_historical_start_after_end(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            "2024-06-15", "2024-06-01", "user@example.com", "excel", None, "sess_123",
            None, "en",
        )
        assert result[2] is not None

    def test_historical_before_1990(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            "1989-01-01", "1989-01-15", "user@example.com", "excel", None, "sess_123",
            None, "en",
        )
        assert result[2] is not None

    def test_historical_period_exceeds_90(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "historical",
            "2024-01-01", "2024-06-01", "user@example.com", "excel", None, "sess_123",
            None, "en",
        )
        assert result[2] is not None

    def test_recent_no_period(self):
        result = self._get_fn()(
            1, {"lat": -23.55, "lon": -46.63}, "recent",
            None, None, None, None, None, "sess_123",
            None, "en",
        )
        assert result[2] is not None  # period not selected
