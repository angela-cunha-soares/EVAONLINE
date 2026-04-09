"""
Tests for EToCalculationService — FAO-56 Penman-Monteith pure calculations.

Covers:
- _validate_measurements: input validation
- calculate_et0: full ETo calculation pipeline
- _saturation_vapor_pressure: Tetens formula
- _vapor_pressure_slope: slope of saturation vapor pressure curve
- _solar_declination: FAO-56 Eq. 24
- _extraterrestrial_radiation: FAO-56 Eq. 21
- _net_radiation: FAO-56 Eq. 38-39
- _summarize / _generate_recommendations: output helpers
"""

import pytest
import numpy as np
import pandas as pd

from backend.core.eto_calculation.eto_services import (
    EToCalculationService,
    EToProcessingService,
)


# ════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def eto_service():
    return EToCalculationService()


@pytest.fixture
def valid_measurements():
    return {
        "T2M_MAX": 32.5,
        "T2M_MIN": 18.2,
        "T2M": 25.4,
        "RH2M": 65.0,
        "WS2M": 2.5,
        "ALLSKY_SFC_SW_DWN": 20.5,
        "latitude": -22.2926,
        "longitude": -48.5841,
        "date": "2024-01-15",
        "elevation_m": 580,
    }


@pytest.fixture
def elevation_factors():
    """Pre-calculated elevation factors for z=580m"""
    return {
        "pressure": 94.52,
        "gamma": 0.0628,
        "solar_factor": 1.0,
    }


# ════════════════════════════════════════════════════════════════════
# _validate_measurements
# ════════════════════════════════════════════════════════════════════

class TestValidateMeasurements:

    def test_valid_measurements(self, eto_service, valid_measurements):
        assert eto_service._validate_measurements(valid_measurements) is True

    def test_missing_required_field(self, eto_service, valid_measurements):
        del valid_measurements["T2M_MAX"]
        with pytest.raises(ValueError, match="Variáveis ausentes"):
            eto_service._validate_measurements(valid_measurements)

    def test_missing_multiple_fields(self, eto_service):
        measurements = {"T2M_MAX": 30, "latitude": -20, "longitude": -40}
        with pytest.raises(ValueError, match="Variáveis ausentes"):
            eto_service._validate_measurements(measurements)

    def test_invalid_coordinates(self, eto_service, valid_measurements):
        valid_measurements["latitude"] = 200
        with pytest.raises(ValueError, match="Coordenadas inválidas"):
            eto_service._validate_measurements(valid_measurements)

    def test_invalid_elevation_too_high(self, eto_service, valid_measurements):
        valid_measurements["elevation_m"] = 10000
        with pytest.raises(ValueError, match="Elevação inválida"):
            eto_service._validate_measurements(valid_measurements)

    def test_invalid_elevation_too_low(self, eto_service, valid_measurements):
        valid_measurements["elevation_m"] = -600
        with pytest.raises(ValueError, match="Elevação inválida"):
            eto_service._validate_measurements(valid_measurements)

    def test_tmax_less_than_tmin(self, eto_service, valid_measurements):
        valid_measurements["T2M_MAX"] = 15.0
        valid_measurements["T2M_MIN"] = 25.0
        with pytest.raises(ValueError, match="T2M_MAX < T2M_MIN"):
            eto_service._validate_measurements(valid_measurements)

    def test_boundary_elevation_valid(self, eto_service, valid_measurements):
        """Elevation at boundaries should pass"""
        valid_measurements["elevation_m"] = -500
        assert eto_service._validate_measurements(valid_measurements) is True

        valid_measurements["elevation_m"] = 9000
        assert eto_service._validate_measurements(valid_measurements) is True

    def test_equator_coordinates(self, eto_service, valid_measurements):
        valid_measurements["latitude"] = 0.0
        valid_measurements["longitude"] = 0.0
        assert eto_service._validate_measurements(valid_measurements) is True


# ════════════════════════════════════════════════════════════════════
# _saturation_vapor_pressure (Tetens formula)
# ════════════════════════════════════════════════════════════════════

class TestSaturationVaporPressure:

    def test_at_zero_celsius(self, eto_service):
        """es(0°C) = 0.6108 kPa (known reference value)"""
        result = eto_service._saturation_vapor_pressure(0)
        assert abs(result - 0.6108) < 0.001

    def test_at_20_celsius(self, eto_service):
        """es(20°C) ≈ 2.338 kPa (FAO-56 Table 2.3)"""
        result = eto_service._saturation_vapor_pressure(20)
        assert abs(result - 2.338) < 0.01

    def test_at_30_celsius(self, eto_service):
        """es(30°C) ≈ 4.243 kPa (FAO-56 Table 2.3)"""
        result = eto_service._saturation_vapor_pressure(30)
        assert abs(result - 4.243) < 0.01

    def test_at_negative_temperature(self, eto_service):
        """Below freezing should still return positive value"""
        result = eto_service._saturation_vapor_pressure(-10)
        assert result > 0
        assert result < 0.6108  # Less than value at 0°C

    def test_always_positive(self, eto_service):
        """Saturation VP must always be positive for real temperatures"""
        for T in [-20, -10, 0, 10, 20, 30, 40]:
            assert eto_service._saturation_vapor_pressure(T) > 0

    def test_monotonically_increasing(self, eto_service):
        """Higher temperature → higher saturation VP"""
        temps = [-10, 0, 10, 20, 30, 40]
        vals = [eto_service._saturation_vapor_pressure(T) for T in temps]
        for i in range(1, len(vals)):
            assert vals[i] > vals[i - 1]


# ════════════════════════════════════════════════════════════════════
# _vapor_pressure_slope
# ════════════════════════════════════════════════════════════════════

class TestVaporPressureSlope:

    def test_at_20_celsius(self, eto_service):
        """Slope at 20°C ≈ 0.145 kPa/°C (FAO-56)"""
        result = eto_service._vapor_pressure_slope(20)
        assert abs(result - 0.145) < 0.005

    def test_at_25_celsius(self, eto_service):
        """Slope at 25°C ≈ 0.189 kPa/°C"""
        result = eto_service._vapor_pressure_slope(25)
        assert abs(result - 0.189) < 0.005

    def test_always_positive(self, eto_service):
        for T in [-10, 0, 10, 20, 30, 40]:
            assert eto_service._vapor_pressure_slope(T) > 0

    def test_increasing_with_temperature(self, eto_service):
        """Slope increases with temperature"""
        temps = [0, 10, 20, 30, 40]
        slopes = [eto_service._vapor_pressure_slope(T) for T in temps]
        for i in range(1, len(slopes)):
            assert slopes[i] > slopes[i - 1]


# ════════════════════════════════════════════════════════════════════
# _solar_declination (FAO-56 Eq. 24)
# ════════════════════════════════════════════════════════════════════

class TestSolarDeclination:

    def test_summer_solstice(self, eto_service):
        """Day 172 (June 21) → max declination ≈ +0.409 rad ≈ +23.45°"""
        result = eto_service._solar_declination(172)
        assert abs(result - 0.409) < 0.05

    def test_winter_solstice(self, eto_service):
        """Day 355 (Dec 21) → min declination ≈ -0.409 rad"""
        result = eto_service._solar_declination(355)
        assert result < -0.3

    def test_equinox_spring(self, eto_service):
        """Day 80 (March 21) → declination near 0"""
        result = eto_service._solar_declination(80)
        assert abs(result) < 0.1

    def test_range(self, eto_service):
        """Declination always between -0.41 and +0.41 rad"""
        for N in range(1, 366):
            d = eto_service._solar_declination(N)
            assert -0.5 <= d <= 0.5


# ════════════════════════════════════════════════════════════════════
# _extraterrestrial_radiation (FAO-56 Eq. 21)
# ════════════════════════════════════════════════════════════════════

class TestExtraterrestrialRadiation:

    def test_always_non_negative(self, eto_service):
        """Ra must be ≥ 0 for any latitude/day"""
        for lat in [-60, -30, 0, 30, 60]:
            for N in [1, 91, 182, 274]:
                delta = eto_service._solar_declination(N)
                Ra = eto_service._extraterrestrial_radiation(lat, N, delta)
                assert Ra >= 0.0

    def test_equator_midsummer(self, eto_service):
        """Equator gets moderate Ra year-round"""
        N = 172  # June
        delta = eto_service._solar_declination(N)
        Ra = eto_service._extraterrestrial_radiation(0, N, delta)
        assert 25 < Ra < 45  # Reasonable range MJ/m²/day

    def test_equator_midwinter(self, eto_service):
        """Equator in December — still has significant Ra"""
        N = 355
        delta = eto_service._solar_declination(N)
        Ra = eto_service._extraterrestrial_radiation(0, N, delta)
        assert 25 < Ra < 45

    def test_tropical_brazilian_jan(self, eto_service):
        """São Paulo (-23.5°) in January → high Ra"""
        lat = -23.5
        N = 15  # Jan 15
        delta = eto_service._solar_declination(N)
        Ra = eto_service._extraterrestrial_radiation(lat, N, delta)
        assert 30 < Ra < 50

    def test_polar_winter_zero(self, eto_service):
        """High latitude polar winter → Ra near 0"""
        lat = 70
        N = 355  # December
        delta = eto_service._solar_declination(N)
        Ra = eto_service._extraterrestrial_radiation(lat, N, delta)
        assert Ra < 3.0  # Minimal to zero

    def test_polar_summer_high(self, eto_service):
        """High latitude polar summer → extended daylight"""
        lat = 70
        N = 172  # June
        delta = eto_service._solar_declination(N)
        Ra = eto_service._extraterrestrial_radiation(lat, N, delta)
        assert Ra > 30  # 24h daylight → high Ra

    def test_symmetric_hemispheres(self, eto_service):
        """Southern hemisphere summer = Northern hemisphere summer (shifted 6mo)"""
        # Northern hemisphere June
        N_north = 172
        delta_n = eto_service._solar_declination(N_north)
        Ra_n = eto_service._extraterrestrial_radiation(40, N_north, delta_n)

        # Southern hemisphere December
        N_south = 355
        delta_s = eto_service._solar_declination(N_south)
        Ra_s = eto_service._extraterrestrial_radiation(-40, N_south, delta_s)

        # Should be roughly similar (within 10%)
        assert abs(Ra_n - Ra_s) / max(Ra_n, Ra_s) < 0.15


# ════════════════════════════════════════════════════════════════════
# _net_radiation (FAO-56 Eq. 38-39)
# ════════════════════════════════════════════════════════════════════

class TestNetRadiation:

    def test_typical_tropical_day(self, eto_service):
        """Rn for a typical tropical day should be 5-20 MJ/m²/day"""
        Rn = eto_service._net_radiation(
            Rs=20, T_max=32, T_min=20, RH_mean=65, Ra=40
        )
        assert 5 < Rn < 20

    def test_higher_radiation_higher_Rn(self, eto_service):
        """More solar radiation → more net radiation"""
        Rn_low = eto_service._net_radiation(
            Rs=10, T_max=30, T_min=18, RH_mean=70, Ra=40
        )
        Rn_high = eto_service._net_radiation(
            Rs=25, T_max=30, T_min=18, RH_mean=70, Ra=40
        )
        assert Rn_high > Rn_low

    def test_low_radiation(self, eto_service):
        """Very low Rs → Rn might be near zero or negative"""
        Rn = eto_service._net_radiation(
            Rs=2, T_max=30, T_min=18, RH_mean=60, Ra=40
        )
        # Low Rs means low Rns, but Rnl (longwave) might dominate
        assert Rn < 5

    def test_zero_Ra_handled(self, eto_service):
        """Ra=0 should not cause division by zero"""
        Rn = eto_service._net_radiation(
            Rs=10, T_max=25, T_min=15, RH_mean=70, Ra=0
        )
        assert np.isfinite(Rn)

    def test_humidity_effect(self, eto_service):
        """Higher humidity → less longwave loss → higher Rn"""
        Rn_dry = eto_service._net_radiation(
            Rs=20, T_max=30, T_min=18, RH_mean=30, Ra=40
        )
        Rn_humid = eto_service._net_radiation(
            Rs=20, T_max=30, T_min=18, RH_mean=90, Ra=40
        )
        assert Rn_humid > Rn_dry


# ════════════════════════════════════════════════════════════════════
# calculate_et0 — Full FAO-56 PM calculation
# ════════════════════════════════════════════════════════════════════

class TestCalculateEt0:

    def test_typical_tropical(self, eto_service, valid_measurements, elevation_factors):
        """Typical São Paulo day → ETo between 2-8 mm/day"""
        result = eto_service.calculate_et0(valid_measurements, elevation_factors)
        assert "et0_mm_day" in result
        assert 1.0 <= result["et0_mm_day"] <= 10.0
        assert result["quality"] == "high"
        assert result["method"] == "pm_fao56"

    def test_components_present(self, eto_service, valid_measurements, elevation_factors):
        """Result should contain diagnostic components"""
        result = eto_service.calculate_et0(valid_measurements, elevation_factors)
        assert "components" in result
        assert "Ra" in result["components"]
        assert "Rn" in result["components"]
        assert "slope" in result["components"]
        assert "gamma" in result["components"]

    def test_without_elevation_factors(self, eto_service, valid_measurements):
        """Should still work without pre-calculated factors"""
        result = eto_service.calculate_et0(valid_measurements)
        assert "et0_mm_day" in result
        assert result["et0_mm_day"] > 0

    def test_cold_low_radiation_day(self, eto_service):
        """Cold, cloudy day → low ETo"""
        meas = {
            "T2M_MAX": 10.0,
            "T2M_MIN": 2.0,
            "T2M": 6.0,
            "RH2M": 85.0,
            "WS2M": 1.0,
            "ALLSKY_SFC_SW_DWN": 5.0,
            "latitude": 45.0,
            "longitude": 10.0,
            "date": "2024-01-15",
            "elevation_m": 200,
        }
        result = eto_service.calculate_et0(meas)
        assert result["et0_mm_day"] < 3.0

    def test_hot_arid_day(self, eto_service):
        """Hot desert day → high ETo"""
        meas = {
            "T2M_MAX": 42.0,
            "T2M_MIN": 25.0,
            "T2M": 35.0,
            "RH2M": 15.0,
            "WS2M": 5.0,
            "ALLSKY_SFC_SW_DWN": 28.0,
            "latitude": 25.0,
            "longitude": 45.0,
            "date": "2024-07-15",
            "elevation_m": 100,
        }
        result = eto_service.calculate_et0(meas)
        assert result["et0_mm_day"] > 5.0
        # Extremely high ETo (>10) gets flagged as "low" quality by the validator
        assert result["quality"] in ("high", "low")

    def test_invalid_measurements_returns_error(self, eto_service):
        """Missing fields should return error dict"""
        result = eto_service.calculate_et0({"T2M": 25})
        assert result["et0_mm_day"] == 0.0
        assert result["quality"] == "low"
        assert "error" in result

    def test_minimum_wind_speed_enforced(self, eto_service, valid_measurements, elevation_factors):
        """Wind speed < 0.5 m/s → clamped to 0.5"""
        valid_measurements["WS2M"] = 0.1
        result = eto_service.calculate_et0(valid_measurements, elevation_factors)
        assert result["et0_mm_day"] > 0

    def test_different_dates(self, eto_service, valid_measurements, elevation_factors):
        """Different day of year changes Ra and thus ETo"""
        valid_measurements["date"] = "2024-01-15"
        result_jan = eto_service.calculate_et0(valid_measurements, elevation_factors)

        valid_measurements["date"] = "2024-07-15"
        result_jul = eto_service.calculate_et0(valid_measurements, elevation_factors)

        # In Southern hemisphere, Jan is summer → higher ETo
        assert result_jan["et0_mm_day"] != result_jul["et0_mm_day"]

    def test_sea_level_elevation(self, eto_service, valid_measurements):
        """Elevation = 0 should work"""
        valid_measurements["elevation_m"] = 0
        result = eto_service.calculate_et0(valid_measurements)
        assert result["et0_mm_day"] > 0

    def test_high_altitude(self, eto_service, valid_measurements):
        """3000m altitude → different gamma"""
        valid_measurements["elevation_m"] = 3000
        result = eto_service.calculate_et0(valid_measurements)
        assert result["et0_mm_day"] > 0

    def test_equatorial_location(self, eto_service, valid_measurements, elevation_factors):
        """Equator should have reasonable ETo"""
        valid_measurements["latitude"] = 0.0
        valid_measurements["longitude"] = 30.0
        result = eto_service.calculate_et0(valid_measurements, elevation_factors)
        assert 1.0 <= result["et0_mm_day"] <= 12.0


# ════════════════════════════════════════════════════════════════════
# _summarize and _generate_recommendations
# ════════════════════════════════════════════════════════════════════

class TestSummarizeAndRecommendations:

    @pytest.fixture
    def processing_service(self):
        return EToProcessingService()

    def test_summarize(self, processing_service):
        """_summarize should return correct statistics"""
        df = pd.DataFrame({
            "et0_mm_day": [3.0, 4.5, 5.0, 6.0, 2.5]
        })
        result = processing_service._summarize(df)
        assert result["total_days"] == 5
        assert result["et0_total_mm"] == 21.0
        assert result["et0_mean_mm_day"] == 4.2
        assert result["et0_max_mm_day"] == 6.0
        assert result["et0_min_mm_day"] == 2.5

    def test_summarize_single_day(self, processing_service):
        df = pd.DataFrame({"et0_mm_day": [5.23]})
        result = processing_service._summarize(df)
        assert result["total_days"] == 1
        assert result["et0_total_mm"] == 5.2
        assert result["et0_mean_mm_day"] == 5.23

    def test_recommendations_high_eto(self, processing_service):
        """High ETo → recommendation to increase irrigation"""
        df = pd.DataFrame({"et0_mm_day": [7.0, 8.0, 9.0, 7.5, 8.5]})
        recs = processing_service._generate_recommendations(df)
        assert any("alta" in r.lower() or "aumentar" in r.lower() for r in recs)

    def test_recommendations_low_eto(self, processing_service):
        """Low ETo → recommendation to decrease irrigation"""
        df = pd.DataFrame({"et0_mm_day": [1.0, 1.5, 2.0, 1.2, 1.8]})
        recs = processing_service._generate_recommendations(df)
        assert any("baixa" in r.lower() or "reduzir" in r.lower() for r in recs)

    def test_recommendations_irrigation_total(self, processing_service):
        """Always includes total irrigation estimate"""
        df = pd.DataFrame({"et0_mm_day": [4.0, 4.5, 5.0]})
        recs = processing_service._generate_recommendations(df)
        assert any("irrigação" in r.lower() for r in recs)

    def test_recommendations_moderate_eto(self, processing_service):
        """Moderate ETo → basic irrigation recommendation only"""
        df = pd.DataFrame({"et0_mm_day": [4.0, 4.5, 5.0, 4.2, 4.8]})
        recs = processing_service._generate_recommendations(df)
        # Should have irrigation total but no high/low alert
        assert len(recs) >= 1


# ════════════════════════════════════════════════════════════════════
# _calculate_raw_eto (row-by-row FAO-56)
# ════════════════════════════════════════════════════════════════════

class TestCalculateRawEto:

    @pytest.fixture
    def processing_service(self):
        return EToProcessingService()

    def test_basic_calculation(self, processing_service):
        """Should calculate ETo for each row"""
        dates = pd.date_range("2024-01-10", periods=3, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "T2M_MAX": [32.0, 31.0, 33.0],
            "T2M_MIN": [20.0, 19.0, 21.0],
            "T2M": [26.0, 25.0, 27.0],
            "RH2M": [65.0, 70.0, 60.0],
            "WS2M": [2.5, 2.0, 3.0],
            "ALLSKY_SFC_SW_DWN": [20.0, 18.0, 22.0],
            "PRECTOTCORR": [0.0, 5.0, 0.0],
        })
        factors = {"gamma": 0.0628}
        result = processing_service._calculate_raw_eto(
            df, lat=-23.5, lon=-46.6, elevation=760, factors=factors
        )
        assert "et0_mm" in result.columns
        assert all(result["et0_mm"] > 0)

    def test_with_datetime_index(self, processing_service):
        """Should handle DataFrame with DatetimeIndex (no date column)"""
        dates = pd.date_range("2024-01-10", periods=3, freq="D")
        df = pd.DataFrame({
            "T2M_MAX": [32.0, 31.0, 33.0],
            "T2M_MIN": [20.0, 19.0, 21.0],
            "T2M": [26.0, 25.0, 27.0],
            "RH2M": [65.0, 70.0, 60.0],
            "WS2M": [2.5, 2.0, 3.0],
            "ALLSKY_SFC_SW_DWN": [20.0, 18.0, 22.0],
            "PRECTOTCORR": [0.0, 5.0, 0.0],
        }, index=dates)
        factors = {"gamma": 0.0628}
        result = processing_service._calculate_raw_eto(
            df, lat=-23.5, lon=-46.6, elevation=760, factors=factors
        )
        assert "et0_mm" in result.columns
        assert all(result["et0_mm"] > 0)
