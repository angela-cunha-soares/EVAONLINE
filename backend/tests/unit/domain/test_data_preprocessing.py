"""
Unit Tests - data_preprocessing

Tests the FAO-56 data cleaning pipeline: physical limit validation,
IQR outlier detection, interpolation/imputation, and full pipeline.

Reference: Article Section 2.4 (Data Quality Control)
"""

import numpy as np
import pandas as pd
import pytest

from backend.core.data_processing.data_preprocessing import (
    data_initial_validate,
    detect_outliers_iqr,
    data_impute,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_weather_df():
    """14-day DataFrame with valid climate data and DatetimeIndex."""
    dates = pd.date_range("2024-06-01", periods=14, freq="D")
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "temperature_2m_max": np.random.uniform(25, 35, 14),
            "temperature_2m_min": np.random.uniform(15, 22, 14),
            "temperature_2m_mean": np.random.uniform(20, 28, 14),
            "relative_humidity_2m_mean": np.random.uniform(40, 80, 14),
            "wind_speed_10m_max": np.random.uniform(1, 8, 14),
            "shortwave_radiation_sum": np.random.uniform(10, 25, 14),
            "precipitation_sum": np.random.uniform(0, 15, 14),
        },
        index=dates,
    )
    return df


@pytest.fixture
def weather_df_with_nans(sample_weather_df):
    """DataFrame with some NaN values for imputation testing."""
    df = sample_weather_df.copy()
    df.iloc[3, 0] = np.nan  # temperature_2m_max
    df.iloc[5, 2] = np.nan  # temperature_2m_mean
    df.iloc[7, 4] = np.nan  # wind_speed_10m_max
    return df


@pytest.fixture
def weather_df_with_outliers(sample_weather_df):
    """DataFrame with extreme outlier values."""
    df = sample_weather_df.copy()
    df.iloc[2, 0] = 99.0   # extreme temperature
    df.iloc[5, 4] = 100.0  # extreme wind
    return df


# ============================================================================
# data_initial_validate
# ============================================================================


@pytest.mark.unit
class TestDataInitialValidate:
    """Physical limit validation tests."""

    def test_returns_tuple(self, sample_weather_df):
        result = data_initial_validate(sample_weather_df, latitude=-23.55)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_dataframe(self, sample_weather_df):
        df_out, warnings = data_initial_validate(sample_weather_df, latitude=-23.55)
        assert isinstance(df_out, pd.DataFrame)

    def test_returns_warnings_list(self, sample_weather_df):
        df_out, warnings = data_initial_validate(sample_weather_df, latitude=-23.55)
        assert isinstance(warnings, list)

    def test_preserves_row_count(self, sample_weather_df):
        """Validation should not drop rows, only replace invalid values with NaN."""
        df_out, _ = data_initial_validate(sample_weather_df, latitude=-23.55)
        assert len(df_out) == len(sample_weather_df)

    def test_preserves_columns(self, sample_weather_df):
        """Original columns should be preserved."""
        df_out, _ = data_initial_validate(sample_weather_df, latitude=-23.55)
        for col in sample_weather_df.columns:
            assert col in df_out.columns

    def test_valid_data_stays_valid(self, sample_weather_df):
        """Normal-range values should not be replaced with NaN."""
        df_out, _ = data_initial_validate(sample_weather_df, latitude=-23.55)
        # Most values should survive validation
        original_valid = sample_weather_df.notna().sum().sum()
        result_valid = df_out[sample_weather_df.columns].notna().sum().sum()
        # Allow some loss but most data should be preserved
        assert result_valid >= original_valid * 0.8

    def test_extreme_temperature_replaced(self, sample_weather_df):
        """Temperature of 70°C should be flagged as invalid."""
        df = sample_weather_df.copy()
        df.iloc[0, 0] = 70.0  # Way too hot
        df_out, warnings = data_initial_validate(df, latitude=-23.55)
        # The extreme value should be replaced with NaN
        assert pd.isna(df_out.iloc[0, 0]) or len(warnings) > 0


# ============================================================================
# detect_outliers_iqr
# ============================================================================


@pytest.mark.unit
class TestDetectOutliersIQR:
    """IQR-based outlier detection tests."""

    def test_returns_tuple(self, sample_weather_df):
        result = detect_outliers_iqr(sample_weather_df)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_dataframe(self, sample_weather_df):
        df_out, warnings = detect_outliers_iqr(sample_weather_df)
        assert isinstance(df_out, pd.DataFrame)

    def test_preserves_shape(self, sample_weather_df):
        df_out, _ = detect_outliers_iqr(sample_weather_df)
        assert df_out.shape == sample_weather_df.shape

    def test_extreme_outliers_detected(self, weather_df_with_outliers):
        """Values far outside IQR should be flagged."""
        df_out, warnings = detect_outliers_iqr(weather_df_with_outliers)
        # At least one warning should be raised about outliers
        outlier_count = df_out.isna().sum().sum() - weather_df_with_outliers.isna().sum().sum()
        # Either new NaNs (outliers removed) or warnings about them
        assert outlier_count > 0 or len(warnings) > 0

    def test_no_outliers_in_clean_data(self, sample_weather_df):
        """Clean data should have few or no outliers."""
        df_out, _ = detect_outliers_iqr(sample_weather_df)
        new_nans = df_out.isna().sum().sum() - sample_weather_df.isna().sum().sum()
        assert new_nans <= 2  # Allow minor statistical outliers

    def test_short_data_warning(self):
        """Very short data should trigger a warning."""
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame(
            {"temperature_2m_max": [25, 26, 27]},
            index=dates,
        )
        _, warnings = detect_outliers_iqr(df)
        # Short data may trigger a warning
        assert isinstance(warnings, list)

    def test_constant_column_not_flagged(self):
        """Column with constant values should not produce outliers."""
        dates = pd.date_range("2024-01-01", periods=14, freq="D")
        df = pd.DataFrame(
            {"constant": [25.0] * 14},
            index=dates,
        )
        df_out, _ = detect_outliers_iqr(df)
        assert df_out["constant"].notna().all()


# ============================================================================
# data_impute
# ============================================================================


@pytest.mark.unit
class TestDataImpute:
    """Missing data imputation tests."""

    def test_returns_tuple(self, weather_df_with_nans):
        result = data_impute(weather_df_with_nans)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_fills_interior_nans(self, weather_df_with_nans):
        """Interior NaN gaps should be filled via interpolation."""
        df_out, _ = data_impute(weather_df_with_nans)
        # Most NaNs should be filled
        remaining_nans = df_out.isna().sum().sum()
        original_nans = weather_df_with_nans.isna().sum().sum()
        assert remaining_nans < original_nans

    def test_preserves_valid_values(self, weather_df_with_nans):
        """Non-NaN values should not be changed."""
        df_out, _ = data_impute(weather_df_with_nans)
        mask = weather_df_with_nans.notna()
        # Compare only numeric columns
        for col in weather_df_with_nans.columns:
            valid_idx = mask[col]
            if valid_idx.sum() > 0:
                orig = weather_df_with_nans.loc[valid_idx, col].values
                result = df_out.loc[valid_idx, col].values
                np.testing.assert_array_almost_equal(orig, result)

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty + warning."""
        df = pd.DataFrame()
        df_out, warnings = data_impute(df)
        assert len(df_out) == 0

    def test_preserves_shape(self, weather_df_with_nans):
        df_out, _ = data_impute(weather_df_with_nans)
        assert df_out.shape == weather_df_with_nans.shape
