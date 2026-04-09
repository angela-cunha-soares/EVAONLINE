"""
===========================================
DATA PROCESSING MODULE - EVAonline
===========================================
Módulo de processamento de dados climáticos.

NOVA ARQUITETURA MODULAR:
- climate_ensemble.py: Orquestrador (ClimateKalmanEnsemble)
- climate_fusion.py: Fusão multi-fonte (ClimateFusion)
- kalman_filters.py: Filtros Kalman
- historical_loader.py: Referências climáticas
- data_preprocessing.py: Pré-processamento e validação
"""

import importlib
from typing import Any


def __getattr__(name: str) -> Any:
    """
    Lazy loading de módulos para evitar imports circulares.

    Args:
        name: Nome do módulo/função a ser importado

    Returns:
        Módulo ou função importada dinamicamente
    """
    lazy_imports = {
        # Data download
        "download_weather_data": (
            "backend.api.services.data_download",
            "download_weather_data",
        ),
        # Data preprocessing
        "data_initial_validate": (
            "backend.core.data_processing.data_preprocessing",
            "data_initial_validate",
        ),
        "detect_outliers_iqr": (
            "backend.core.data_processing.data_preprocessing",
            "detect_outliers_iqr",
        ),
        "data_impute": (
            "backend.core.data_processing.data_preprocessing",
            "data_impute",
        ),
        "preprocessing": (
            "backend.core.data_processing.data_preprocessing",
            "preprocessing",
        ),
        # Orquestrador principal
        "ClimateKalmanEnsemble": (
            "backend.core.data_processing.climate_ensemble",
            "ClimateKalmanEnsemble",
        ),
        # Fusão inteligente
        "ClimateFusion": (
            "backend.core.data_processing.climate_fusion",
            "ClimateFusion",
        ),
        # Filtros Kalman
        "AdaptiveKalmanFilter": (
            "backend.core.data_processing.kalman_filters",
            "AdaptiveKalmanFilter",
        ),
        "SimpleKalmanFilter": (
            "backend.core.data_processing.kalman_filters",
            "SimpleKalmanFilter",
        ),
        "KalmanApplier": (
            "backend.core.data_processing.kalman_filters",
            "KalmanApplier",
        ),
        # Loader de dados históricos (lê JSON diretamente)
        "HistoricalDataLoader": (
            "backend.core.data_processing.historical_loader",
            "HistoricalDataLoader",
        ),
    }

    if name in lazy_imports:
        module_name, attr_name = lazy_imports[name]
        try:
            module = importlib.import_module(module_name)
            return getattr(module, attr_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Could not import {name} from {module_name}: {e}"
            )

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# ===========================================
# VERSÃO E METADADOS
# ===========================================

__version__ = "1.0.0"
__author__ = "EVAonline Team"
__description__ = (
    "Data processing module for climate data analysis and "
    "ETo calculation. Includes optimized preprocessing pipeline "
    "with physical validation, IQR outlier detection, and linear "
    "imputation following FAO-56 guidelines. "
    "NOVA ARQUITETURA MODULAR: climate_ensemble, climate_fusion, "
    "kalman_filters, historical_loader. Enhanced Kalman ensemble "
    "filters with improved NaN handling, input validations, and "
    "timestamp support for accurate data fusion."
)

# Nota: Todos os símbolos são carregados via __getattr__ (lazy loading)
# Os avisos do Pylance sobre "not present in module" são falsos positivos
# pyright: reportUnsupportedDunderAll=false
__all__ = [
    # Download
    "download_weather_data",
    # Preprocessing
    "data_initial_validate",
    "detect_outliers_iqr",
    "data_impute",
    "preprocessing",
    # Nova arquitetura modular
    "ClimateKalmanEnsemble",  # Orquestrador principal
    "ClimateFusion",  # Fusão inteligente
    "AdaptiveKalmanFilter",  # Filtro adaptativo
    "SimpleKalmanFilter",  # Filtro simples
    "KalmanApplier",  # Aplicador de filtros
    "HistoricalDataLoader",  # Loader de dados históricos (JSON)
]
