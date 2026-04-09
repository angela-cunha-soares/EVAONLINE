"""
Phase 5 Tests: EToProcessingService — process_location() full pipeline.

Coverage target: backend/core/eto_calculation/eto_services.py (60% → 85%+)
Lines 297-473 (process_location), L507-580 (elevation, raw_eto helpers).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from backend.core.eto_calculation.eto_services import (
    EToProcessingService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_climate_df(n=5, start="2025-01-01"):
    """Build a minimal multi-source DataFrame that looks like download output."""
    dates = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "T2M_MAX": np.random.uniform(28, 35, n),
        "T2M_MIN": np.random.uniform(15, 22, n),
        "T2M": np.random.uniform(22, 28, n),
        "RH2M": np.random.uniform(50, 80, n),
        "WS2M": np.random.uniform(1, 5, n),
        "ALLSKY_SFC_SW_DWN": np.random.uniform(15, 25, n),
        "PRECTOTCORR": np.random.uniform(0, 10, n),
        "source": "nasa_power",
    })


def _preprocessed_df(n=5, start="2025-01-01"):
    """Simulate preprocessing output (same schema, clean)."""
    dates = pd.date_range(start, periods=n, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "T2M_MAX": np.linspace(30, 32, n),
        "T2M_MIN": np.linspace(18, 20, n),
        "T2M": np.linspace(24, 26, n),
        "RH2M": np.full(n, 65.0),
        "WS2M": np.full(n, 3.0),
        "ALLSKY_SFC_SW_DWN": np.full(n, 20.0),
        "PRECTOTCORR": np.full(n, 2.0),
        "source": "nasa_power",
        "fusion_mode": "single_source",
        "fusion_description": "test",
        "fusion_sources": "nasa_power",
    })
    return df


# ===========================================================================
# EToProcessingService._get_best_elevation
# ===========================================================================


class TestGetBestElevation:
    """Tests for _get_best_elevation (async)."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    def test_user_provided_elevation(self):
        """User-supplied elevation used directly."""
        svc = EToProcessingService()
        elev, info = _run(svc._get_best_elevation(-23.5, -46.6, 800.0, True))
        assert elev == 800.0
        assert info["source"] == "usuário"
        assert info["no_data"] is False

    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_opentopo_success(self, mock_cls):
        """OpenTopo returns elevation successfully."""
        svc = EToProcessingService()
        mock_client = AsyncMock()
        mock_client.get_elevation.return_value = MagicMock(elevation=750.0)
        mock_client.close = AsyncMock()
        mock_cls.return_value = mock_client

        elev, info = _run(svc._get_best_elevation(-23.5, -46.6, None, True))
        assert elev == 750.0
        assert info["source"] == "OpenTopo"

    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_opentopo_returns_none_fallback(self, mock_cls):
        """OpenTopo returns None → fallback to 0.0."""
        svc = EToProcessingService()
        mock_client = AsyncMock()
        mock_client.get_elevation.return_value = MagicMock(elevation=None)
        mock_client.close = AsyncMock()
        mock_cls.return_value = mock_client

        elev, info = _run(svc._get_best_elevation(-23.5, -46.6, None, True))
        assert elev == 0.0
        assert info["no_data"] is True

    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_opentopo_exception_fallback(self, mock_cls):
        """OpenTopo raises → fallback to 0.0."""
        svc = EToProcessingService()
        mock_cls.side_effect = ConnectionError("API down")

        elev, info = _run(svc._get_best_elevation(-23.5, -46.6, None, True))
        assert elev == 0.0
        assert info["no_data"] is True

    def test_no_precise_elevation(self):
        """use_precise_elevation=False → immediate fallback."""
        svc = EToProcessingService()
        elev, info = _run(svc._get_best_elevation(-23.5, -46.6, None, False))
        assert elev == 0.0
        assert info["source"] == "padrão"


# ===========================================================================
# EToProcessingService._calculate_raw_eto
# ===========================================================================


class TestCalculateRawETo:
    """Tests for _calculate_raw_eto (row-by-row FAO-56)."""

    def test_normal_calculation(self):
        """All rows get valid ETo values."""
        svc = EToProcessingService()
        df = _preprocessed_df(5)
        factors = {"gamma": 0.0665, "pressure": 101.3, "solar_factor": 1.0}

        result = svc._calculate_raw_eto(df, -23.5, -46.6, 760.0, factors)
        assert "et0_mm" in result.columns
        assert result["et0_mm"].notna().all()
        assert (result["et0_mm"] >= 0).all()

    def test_nat_date_skipped(self):
        """Rows with NaT date produce NaN ETo."""
        svc = EToProcessingService()
        df = _preprocessed_df(3)
        df.loc[1, "date"] = pd.NaT
        factors = {"gamma": 0.0665}

        result = svc._calculate_raw_eto(df, -23.5, -46.6, 760.0, factors)
        assert pd.isna(result["et0_mm"].iloc[1])

    def test_datetimeindex_fallback(self):
        """When 'date' col missing but index is DatetimeIndex, creates it."""
        svc = EToProcessingService()
        df = _preprocessed_df(3)
        df = df.set_index("date")  # Remove 'date' column, make it index
        factors = {"gamma": 0.0665}

        result = svc._calculate_raw_eto(df, -23.5, -46.6, 760.0, factors)
        assert "et0_mm" in result.columns
        assert result["et0_mm"].notna().all()

    def test_no_date_column_or_index_raises(self):
        """Neither 'date' column nor DatetimeIndex → ValueError."""
        svc = EToProcessingService()
        df = _preprocessed_df(3)
        df = df.drop(columns=["date"])
        df.index = range(3)  # Integer index
        factors = {"gamma": 0.0665}

        with pytest.raises(ValueError, match="sem coluna 'date'"):
            svc._calculate_raw_eto(df, -23.5, -46.6, 760.0, factors)


# ===========================================================================
# EToProcessingService.process_location — full pipeline
# ===========================================================================


class TestProcessLocation:
    """Integration-style tests for process_location (all deps mocked)."""

    @pytest.fixture(autouse=True)
    def _fresh_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()

    def _mock_download(self, df=None):
        if df is None:
            df = _make_climate_df(5)
        return AsyncMock(return_value=(df, []))

    def _mock_preprocessing(self, df=None):
        if df is None:
            df = _preprocessed_df(5)
        return MagicMock(return_value=(df, []))

    @patch("backend.core.eto_calculation.eto_services.ElevationUtils")
    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_process_location_single_source(self, mock_topo_cls, mock_elev):
        """Full pipeline: single source, no fusion, returns valid response."""
        svc = EToProcessingService()

        # Elevation
        mock_topo = AsyncMock()
        mock_topo.get_elevation.return_value = MagicMock(elevation=760.0)
        mock_topo.close = AsyncMock()
        mock_topo_cls.return_value = mock_topo
        mock_elev.get_elevation_correction_factor.return_value = {
            "gamma": 0.0665, "pressure": 92.5, "solar_factor": 1.02,
        }

        download_df = _make_climate_df(5)
        prep_df = _preprocessed_df(5)

        with patch(
            "backend.api.services.data_download.download_weather_data",
            new=self._mock_download(download_df),
        ), patch(
            "backend.core.data_processing.data_preprocessing.preprocessing",
            new=self._mock_preprocessing(prep_df),
        ):
            result = _run(
                svc.process_location(
                    latitude=-23.5,
                    longitude=-46.6,
                    start_date="2025-01-01",
                    end_date="2025-01-05",
                    sources=["nasa_power"],
                    enable_fusion=False,
                )
            )

        assert "error" not in result or result.get("error") is None
        assert "et0_series" in result
        assert len(result["et0_series"]) == 5
        assert "summary" in result
        assert "recommendations" in result

    @patch("backend.core.eto_calculation.eto_services.ElevationUtils")
    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_process_location_with_fusion(self, mock_topo_cls, mock_elev):
        """Full pipeline: enable_fusion=True → calls ensemble.process()."""
        svc = EToProcessingService()

        mock_topo = AsyncMock()
        mock_topo.get_elevation.return_value = MagicMock(elevation=760.0)
        mock_topo.close = AsyncMock()
        mock_topo_cls.return_value = mock_topo
        mock_elev.get_elevation_correction_factor.return_value = {
            "gamma": 0.0665, "pressure": 92.5, "solar_factor": 1.02,
        }

        download_df = _make_climate_df(5)
        prep_df = _preprocessed_df(5)

        # Mock ensemble
        fused = prep_df.copy()
        fused["et0_mm"] = np.linspace(4.0, 5.0, 5)
        fused["eto_final"] = fused["et0_mm"]
        fused["eto_evaonline"] = fused["et0_mm"]
        svc.ensemble = MagicMock()
        svc.ensemble.process.return_value = fused
        svc.ensemble.loader.get_reference_for_location.return_value = (False, None)

        with patch(
            "backend.api.services.data_download.download_weather_data",
            new=self._mock_download(download_df),
        ), patch(
            "backend.core.data_processing.data_preprocessing.preprocessing",
            new=self._mock_preprocessing(prep_df),
        ):
            result = _run(
                svc.process_location(
                    latitude=-23.5,
                    longitude=-46.6,
                    start_date="2025-01-01",
                    end_date="2025-01-05",
                    sources=["nasa_power", "openmeteo_archive"],
                    enable_fusion=True,
                    mode="historical_email",
                )
            )

        svc.ensemble.process.assert_called_once()
        assert "et0_series" in result

    @patch("backend.core.eto_calculation.eto_services.ElevationUtils")
    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_process_location_empty_download_error(self, mock_topo_cls, mock_elev):
        """Empty download returns error dict."""
        svc = EToProcessingService()

        mock_topo = AsyncMock()
        mock_topo.get_elevation.return_value = MagicMock(elevation=760.0)
        mock_topo.close = AsyncMock()
        mock_topo_cls.return_value = mock_topo
        mock_elev.get_elevation_correction_factor.return_value = {
            "gamma": 0.0665,
        }

        empty_df = pd.DataFrame()

        with patch(
            "backend.api.services.data_download.download_weather_data",
            new=AsyncMock(return_value=(empty_df, [])),
        ):
            result = _run(
                svc.process_location(
                    latitude=-23.5,
                    longitude=-46.6,
                    start_date="2025-01-01",
                    end_date="2025-01-05",
                    sources=["nasa_power"],
                )
            )

        assert "error" in result

    @patch("backend.core.eto_calculation.eto_services.ElevationUtils")
    @patch("backend.core.eto_calculation.eto_services.OpenTopoClient")
    def test_process_location_with_kalman_eto(self, mock_topo_cls, mock_elev):
        """With fusion and historical reference → Kalman ETo is applied."""
        svc = EToProcessingService()

        mock_topo = AsyncMock()
        mock_topo.get_elevation.return_value = MagicMock(elevation=760.0)
        mock_topo.close = AsyncMock()
        mock_topo_cls.return_value = mock_topo
        mock_elev.get_elevation_correction_factor.return_value = {
            "gamma": 0.0665,
        }

        download_df = _make_climate_df(5)
        prep_df = _preprocessed_df(5)

        fused = prep_df.copy()
        fused["et0_mm"] = np.linspace(4.0, 5.0, 5)
        fused["eto_final"] = fused["et0_mm"]
        fused["eto_evaonline"] = fused["et0_mm"]

        svc.ensemble = MagicMock()
        svc.ensemble.process.return_value = fused
        svc.ensemble.loader.get_reference_for_location.return_value = (
            True,
            {"eto_normals": {1: 5.0}, "eto_stds": {1: 1.0}},
        )
        svc.ensemble.kalman.apply_eto_filter.return_value = fused

        with patch(
            "backend.api.services.data_download.download_weather_data",
            new=AsyncMock(return_value=(download_df, [])),
        ), patch(
            "backend.core.data_processing.data_preprocessing.preprocessing",
            new=MagicMock(return_value=(prep_df, [])),
        ):
            result = _run(
                svc.process_location(
                    latitude=-23.5,
                    longitude=-46.6,
                    start_date="2025-01-01",
                    end_date="2025-01-05",
                    sources=["nasa_power", "openmeteo_archive"],
                    enable_fusion=True,
                )
            )

        svc.ensemble.kalman.apply_eto_filter.assert_called_once()
        assert "et0_series" in result


# ===========================================================================
# Summarize and recommendations
# ===========================================================================


class TestSummarizeAndRecommendations:
    """Tests for _summarize and _generate_recommendations."""

    def test_summarize_basic(self):
        svc = EToProcessingService()
        df = pd.DataFrame({"et0_mm_day": [3.0, 4.0, 5.0, 6.0, 7.0]})
        summary = svc._summarize(df)
        assert summary["total_days"] == 5
        assert summary["et0_total_mm"] == 25.0
        assert summary["et0_mean_mm_day"] == 5.0
        assert summary["et0_max_mm_day"] == 7.0
        assert summary["et0_min_mm_day"] == 3.0

    def test_recommendations_high_eto(self):
        svc = EToProcessingService()
        df = pd.DataFrame({"et0_mm_day": [7.0, 8.0, 9.0]})
        recs = svc._generate_recommendations(df)
        assert any("alta" in r.lower() or "aumentar" in r.lower() for r in recs)

    def test_recommendations_low_eto(self):
        svc = EToProcessingService()
        df = pd.DataFrame({"et0_mm_day": [1.0, 2.0, 2.5]})
        recs = svc._generate_recommendations(df)
        assert any("baixa" in r.lower() or "reduzir" in r.lower() for r in recs)

    def test_recommendations_normal_eto(self):
        svc = EToProcessingService()
        df = pd.DataFrame({"et0_mm_day": [4.0, 4.5, 5.0]})
        recs = svc._generate_recommendations(df)
        # Should only have irrigation estimate, no "alta" or "baixa"
        assert len(recs) == 1
        assert "Irrigação" in recs[0]
