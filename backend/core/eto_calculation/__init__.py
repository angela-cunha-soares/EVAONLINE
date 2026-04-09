"""
ETo Calculation Module - FAO-56 Penman-Monteith.

This module provides services for calculating reference evapotranspiration
(ETo) using the FAO-56 Penman-Monteith method.

Architecture:
- EToCalculationService: Pure FAO-56 calculation (no I/O, no fusion)
- EToProcessingService: Full pipeline with multi-source fusion, Kalman
  filtering, and elevation correction

Components:
- calculate_et0(): Compatibility function for standalone ETo calculation
- EToCalculationService: Core FAO-56 implementation
- EToProcessingService: Complete processing pipeline with ClimateKalman
  Ensemble

Dependencies:
- ClimateKalmanEnsemble: Multi-source data fusion with Kalman filtering
- ElevationUtils: FAO-56 elevation corrections (pressure, gamma)
- OpenTopoClient: Precise elevation data (SRTM/ASTER 30m)
"""

from backend.core.eto_calculation.eto_services import (
    EToCalculationService,
    EToProcessingService,
)

__all__ = [
    "EToCalculationService",
    "EToProcessingService",
]
