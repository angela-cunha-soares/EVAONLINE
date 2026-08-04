"""
Climate Data Physical Limits - Centralized Configuration

Fonte única de verdade para limites físicos de validação climática.
Usado por data_preprocessing.py e kalman_ensemble.py.

Referências:
- WMO (World Meteorological Organization) - Records mundiais
- NOAA (National Oceanic and Atmospheric Administration)
- Bureau of Meteorology Australia
- Xavier et al. (2016, 2022) - Limites para Brasil
"""

from typing import Dict, Tuple

# =============================================================================
# LIMITES GLOBAIS (Mundo)
# =============================================================================
# Records oficiais: Death Valley (56.7°C), Vostok (-89.2°C),
# Bridge Creek Tornado (113.3 m/s), Cilaos (1825 mm/dia)
#
# Formato GLOBAL_LIMITS_VALIDATION: {variável: (min, max, inclusive)}
# Parâmetro 'inclusive':
# - "both": Inclui min e max
# - "neither": Exclui min e max
# - "left": Inclui min, exclui max
# - "right": Exclui min, inclui max

GLOBAL_LIMITS_VALIDATION = {
    # ─────────────────────────────────────────────────────────────
    # NASA POWER
    # ─────────────────────────────────────────────────────────────
    "T2M_MAX": (-90, 60, "neither"),
    "T2M_MIN": (-90, 60, "neither"),
    "T2M": (-90, 60, "neither"),
    "RH2M": (0, 100, "both"),
    "WS2M": (0, 115, "left"),
    "PRECTOTCORR": (0, 2000, "left"),
    "ALLSKY_SFC_SW_DWN": (0, 35, "left"),
    # ─────────────────────────────────────────────────────────────
    # Open-Meteo Archive/Forecast
    # ─────────────────────────────────────────────────────────────
    "temperature_2m_max": (-90, 60, "neither"),
    "temperature_2m_min": (-90, 60, "neither"),
    "temperature_2m_mean": (-90, 60, "neither"),
    "relative_humidity_2m_max": (0, 100, "both"),
    "relative_humidity_2m_mean": (0, 100, "both"),
    "relative_humidity_2m_min": (0, 100, "both"),
    "wind_speed_10m_max": (0, 115, "left"),
    "wind_speed_10m_mean": (0, 115, "left"),
    "shortwave_radiation_sum": (0, 35, "left"),
    "daylight_duration": (0, 24, "both"),
    "sunshine_duration": (0, 24, "both"),
    "precipitation_sum": (0, 2000, "left"),
    "et0_fao_evapotranspiration": (0, 20, "left"),
    # ─────────────────────────────────────────────────────────────
    # MET Norway
    # ─────────────────────────────────────────────────────────────
    "pressure_mean_sea_level": (800, 1150, "both"),
    "temp_celsius": (-90, 60, "neither"),
    "humidity_percent": (0, 100, "both"),
    # ─────────────────────────────────────────────────────────────
    # NWS
    # ─────────────────────────────────────────────────────────────
    "wind_speed_ms": (0, 115, "left"),
    "precipitation_mm": (0, 2000, "left"),
}

# Formato GLOBAL_LIMITS_FUSION: {variável: (min, max)}
# Usado para:
# - Quality score calculation
# - Outlier detection durante fusão
# - Interpolação segura
GLOBAL_LIMITS_FUSION = {
    "T2M_MAX": (-90.0, 60.0),  # Death Valley 1913: 56.7°C
    "T2M_MIN": (-90.0, 60.0),  # Vostok 1983: -89.2°C
    "T2M": (-90.0, 60.0),
    "RH2M": (0.0, 100.0),  # Fisicamente impossível >100%
    "WS2M": (0.0, 115.0),  # Ilha Barrow, Austrália, 10 de abril de 1996 (Ciclone Olivia)
    "ALLSKY_SFC_SW_DWN": (0.0, 35.0),  # BOM Australia
    "PRECTOTCORR": (0.0, 2000.0),  # Cilaos 1952: 1825 mm/dia
}

# =============================================================================
# LIMITES BRASIL (Xavier et al. 2016, 2022)
# =============================================================================
# "New improved Brazilian daily weather gridded data (1961–2020)"

# Limites para validação de dados do Brasil
# Baseado em Xavier et al. (2016, 2022)
BRAZIL_LIMITS_VALIDATION = {
    # NASA POWER
    "T2M_MAX": (-30, 50, "left"),
    "T2M_MIN": (-30, 50, "left"),
    "T2M": (-30, 50, "left"),
    "RH2M": (0, 100, "both"),
    "WS2M": (0, 100, "left"),
    "PRECTOTCORR": (0, 450, "left"),
    # Solar radiation (ALLSKY_SFC_SW_DWN) is NOT bounded by a fixed cap here:
    # for Brazil it is validated against extraterrestrial radiation
    # (0.03*Ra <= Rs < Ra; Moradi et al., 2009) in data_preprocessing.py.
    # Open-Meteo Archive/Forecast
    "temperature_2m_max": (-30, 50, "left"),
    "temperature_2m_min": (-30, 50, "left"),
    "temperature_2m_mean": (-30, 50, "left"),
    "relative_humidity_2m_max": (0, 100, "both"),
    "relative_humidity_2m_mean": (0, 100, "both"),
    "relative_humidity_2m_min": (0, 100, "both"),
    "wind_speed_10m_max": (0, 100, "left"),
    "wind_speed_10m_mean": (0, 100, "left"),
    # shortwave_radiation_sum (solar) validated via 0.03*Ra <= Rs < Ra
    # (Moradi et al., 2009) in data_preprocessing.py, not a fixed cap.
    "daylight_duration": (0, 24, "both"),
    "sunshine_duration": (0, 24, "both"),
    "precipitation_sum": (0, 450, "left"),
    "et0_fao_evapotranspiration": (0, 15, "left"),
    # MET Norway
    "pressure_mean_sea_level": (900, 1100, "both"),
    "temp_celsius": (-30, 50, "left"),
    "humidity_percent": (0, 100, "left"),
    # NWS
    "wind_speed_ms": (0, 100, "left"),
    "precipitation_mm": (0, 450, "left"),
}


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def get_validation_limits(region: str = "global") -> Dict[str, Tuple]:
    """
    Retorna limites de validação para diferentes regiões.

    Args:
        region: "brazil" ou "global"

    Returns:
        Dict com limites no formato {variável: (min, max, inclusive)}
    """
    if region.lower() == "brazil":
        return BRAZIL_LIMITS_VALIDATION
    return GLOBAL_LIMITS_VALIDATION


def get_fusion_limits() -> Dict[str, Tuple[float, float]]:
    """
    Retorna limites para fusão Kalman (variáveis essenciais).

    Returns:
        Dict com limites no formato {variável: (min, max)}
    """
    return GLOBAL_LIMITS_FUSION


def convert_validation_to_fusion_format(
    validation_limits: Dict[str, Tuple],
) -> Dict[str, Tuple[float, float]]:
    """
    Converte limites de validação (3 valores) para formato de fusão (2 valores).

    Args:
        validation_limits: Dict no formato {var: (min, max, inclusive)}

    Returns:
        Dict no formato {var: (min, max)}
    """
    return {
        var: (float(limits[0]), float(limits[1]))
        for var, limits in validation_limits.items()
    }
