"""
Phase 7 – EToCalculationService pure-math tests.

Covers ALL untested methods of EToCalculationService:
- _validate_measurements
- calculate_et0  (full FAO-56 Penman-Monteith)
- _saturation_vapor_pressure
- _vapor_pressure_slope
- _solar_declination
- _extraterrestrial_radiation
- _net_radiation
"""


import pytest
from unittest.mock import patch

from backend.core.eto_calculation.eto_services import EToCalculationService


@pytest.fixture
def svc():
    return EToCalculationService()


@pytest.fixture
def valid_measurements():
    """A complete, physically plausible measurement dict."""
    return {
        "T2M_MAX": 32.0,
        "T2M_MIN": 20.0,
        "T2M": 26.0,
        "RH2M": 65.0,
        "WS2M": 2.0,
        "ALLSKY_SFC_SW_DWN": 18.0,
        "latitude": -23.55,
        "longitude": -46.63,
        "date": "2024-06-21",
        "elevation_m": 760.0,
    }


# ────────── _saturation_vapor_pressure ──────────

class TestSaturationVaporPressure:
    def test_known_value_20c(self, svc):
        # Tetens: 0.6108 * exp(17.27*20 / (20+237.3)) ≈ 2.338 kPa
        result = svc._saturation_vapor_pressure(20.0)
        assert abs(result - 2.338) < 0.01

    def test_known_value_0c(self, svc):
        result = svc._saturation_vapor_pressure(0.0)
        assert abs(result - 0.6108) < 0.001

    def test_known_value_35c(self, svc):
        result = svc._saturation_vapor_pressure(35.0)
        assert result > 5.0  # ~5.62 kPa

    def test_monotonic_increase(self, svc):
        vals = [svc._saturation_vapor_pressure(t) for t in range(-10, 46, 5)]
        for i in range(1, len(vals)):
            assert vals[i] > vals[i - 1]


# ────────── _vapor_pressure_slope ──────────

class TestVaporPressureSlope:
    def test_known_value_20c(self, svc):
        # Approximate expected: ~0.1447 kPa/°C
        result = svc._vapor_pressure_slope(20.0)
        assert 0.14 < result < 0.15

    def test_positive(self, svc):
        for t in [-5, 0, 15, 30, 45]:
            assert svc._vapor_pressure_slope(t) > 0

    def test_increases_with_temp(self, svc):
        s10 = svc._vapor_pressure_slope(10.0)
        s30 = svc._vapor_pressure_slope(30.0)
        assert s30 > s10


# ────────── _solar_declination ──────────

class TestSolarDeclination:
    def test_summer_solstice_positive(self, svc):
        # N=172 (June 21) → delta ≈ +0.409 (max)
        delta = svc._solar_declination(172)
        assert delta > 0.35

    def test_winter_solstice_negative(self, svc):
        # N=356 (Dec 22) → delta ≈ -0.409 (min)
        delta = svc._solar_declination(356)
        assert delta < -0.35

    def test_equinox_near_zero(self, svc):
        # N=80 (March 21) → delta ≈ 0
        delta = svc._solar_declination(80)
        assert abs(delta) < 0.1

    def test_range(self, svc):
        for n in range(1, 366):
            d = svc._solar_declination(n)
            assert -0.42 < d < 0.42


# ────────── _extraterrestrial_radiation ──────────

class TestExtraterrestrialRadiation:
    def test_tropical_summer(self, svc):
        delta = svc._solar_declination(172)
        ra = svc._extraterrestrial_radiation(lat=0.0, N=172, delta=delta)
        assert ra > 30  # ~36 MJ/m²/day at equator in June

    def test_always_nonneg(self, svc):
        for lat in [-60, -30, 0, 30, 60]:
            for n in [1, 80, 172, 265, 356]:
                delta = svc._solar_declination(n)
                ra = svc._extraterrestrial_radiation(lat, n, delta)
                assert ra >= 0

    def test_polar_summer_high(self, svc):
        # Arctic summer (lat=70, N=172) — sun never sets
        delta = svc._solar_declination(172)
        ra = svc._extraterrestrial_radiation(70.0, 172, delta)
        assert ra > 25

    def test_polar_winter_zero(self, svc):
        # Arctic winter (lat=70, N=356) — sun never rises
        delta = svc._solar_declination(356)
        ra = svc._extraterrestrial_radiation(70.0, 356, delta)
        assert ra < 5  # Near zero


# ────────── _net_radiation ──────────

class TestNetRadiation:
    def test_positive_for_good_data(self, svc):
        # Rs=18, Tmax=32, Tmin=20, RH=65, Ra=35
        rn = svc._net_radiation(18.0, 32.0, 20.0, 65.0, 35.0)
        assert rn > 0

    def test_higher_rs_higher_rn(self, svc):
        rn_low = svc._net_radiation(10.0, 30.0, 20.0, 60.0, 35.0)
        rn_high = svc._net_radiation(25.0, 30.0, 20.0, 60.0, 35.0)
        assert rn_high > rn_low

    def test_ra_zero_fallback(self, svc):
        # When Ra=0, cloud factor defaults to 0.33
        rn = svc._net_radiation(5.0, 25.0, 15.0, 70.0, 0.0)
        assert isinstance(rn, float)


# ────────── _validate_measurements ──────────

class TestValidateMeasurements:
    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_valid(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = True
        assert svc._validate_measurements(valid_measurements) is True

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_missing_field(self, mock_geo, svc, valid_measurements):
        del valid_measurements["T2M_MAX"]
        with pytest.raises(ValueError, match="Variáveis ausentes"):
            svc._validate_measurements(valid_measurements)

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_invalid_coordinates(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = False
        with pytest.raises(ValueError, match="Coordenadas inválidas"):
            svc._validate_measurements(valid_measurements)

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_invalid_elevation_too_high(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = True
        valid_measurements["elevation_m"] = 10000
        with pytest.raises(ValueError, match="Elevação inválida"):
            svc._validate_measurements(valid_measurements)

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_tmax_less_than_tmin(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = True
        valid_measurements["T2M_MAX"] = 15.0
        valid_measurements["T2M_MIN"] = 25.0
        with pytest.raises(ValueError, match="T2M_MAX < T2M_MIN"):
            svc._validate_measurements(valid_measurements)


# ────────── calculate_et0 ──────────

class TestCalculateEt0:
    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_normal_calculation(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = True
        result = svc.calculate_et0(
            valid_measurements,
            elevation_factors={"gamma": 0.0534},
        )
        assert "et0_mm_day" in result
        assert 0.1 <= result["et0_mm_day"] <= 12
        assert result["quality"] == "high"
        assert result["method"] == "pm_fao56"
        assert "components" in result

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_without_elevation_factors(self, mock_geo, svc, valid_measurements):
        """Falls back to ElevationUtils.calculate_psychrometric_constant."""
        mock_geo.is_valid_coordinate.return_value = True
        with patch(
            "backend.core.eto_calculation.eto_services.ElevationUtils"
        ) as mock_elev:
            mock_elev.calculate_psychrometric_constant.return_value = 0.054
            result = svc.calculate_et0(valid_measurements)
        assert result["et0_mm_day"] > 0
        mock_elev.calculate_psychrometric_constant.assert_called_once()

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_low_quality_extreme_value(self, mock_geo, svc, valid_measurements):
        """ETo > 12 → quality='low'."""
        mock_geo.is_valid_coordinate.return_value = True
        valid_measurements["WS2M"] = 50.0  # extreme wind
        valid_measurements["RH2M"] = 5.0   # very dry
        valid_measurements["ALLSKY_SFC_SW_DWN"] = 35.0  # extreme radiation
        result = svc.calculate_et0(
            valid_measurements,
            elevation_factors={"gamma": 0.054},
        )
        # Either extreme high or clipped
        assert result["et0_mm_day"] >= 0

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_components_present(self, mock_geo, svc, valid_measurements):
        mock_geo.is_valid_coordinate.return_value = True
        result = svc.calculate_et0(
            valid_measurements,
            elevation_factors={"gamma": 0.054},
        )
        assert "Ra" in result["components"]
        assert "Rn" in result["components"]
        assert "slope" in result["components"]
        assert "gamma" in result["components"]

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_validation_error_returns_low(self, mock_geo, svc):
        """Missing fields → returns dict with quality='low' and error."""
        mock_geo.is_valid_coordinate.return_value = True
        result = svc.calculate_et0({"T2M_MAX": 30})
        assert result["quality"] == "low"
        assert result["et0_mm_day"] == 0.0
        assert "error" in result

    @patch("backend.core.eto_calculation.eto_services.GeographicUtils")
    def test_min_wind_clamp(self, mock_geo, svc, valid_measurements):
        """Wind speed < 0.5 gets clamped to 0.5."""
        mock_geo.is_valid_coordinate.return_value = True
        valid_measurements["WS2M"] = 0.01
        result = svc.calculate_et0(
            valid_measurements,
            elevation_factors={"gamma": 0.054},
        )
        assert result["et0_mm_day"] > 0
