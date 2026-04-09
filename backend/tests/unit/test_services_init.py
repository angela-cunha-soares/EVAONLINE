"""Tests for backend/api/services/__init__.py lazy imports."""

import pytest


class TestServicesLazyImport:
    """Test the __getattr__ lazy loading in services __init__."""

    def test_all_exports_defined(self):
        from backend.api.services import __all__
        assert "ClimateClientFactory" in __all__
        assert "NASAPowerClient" in __all__
        assert "METNorwayClient" in __all__
        assert "WeatherConversionUtils" in __all__

    def test_lazy_import_climate_validation(self):
        from backend.api.services import ClimateValidationService
        assert ClimateValidationService is not None

    def test_lazy_import_climate_source_manager(self):
        from backend.api.services import ClimateSourceManager
        assert ClimateSourceManager is not None

    def test_lazy_import_climate_source_selector(self):
        from backend.api.services import ClimateSourceSelector
        assert ClimateSourceSelector is not None

    def test_lazy_import_weather_utils(self):
        from backend.api.services import WeatherConversionUtils
        assert WeatherConversionUtils is not None

    def test_lazy_import_elevation_utils(self):
        from backend.api.services import ElevationUtils
        assert ElevationUtils is not None

    def test_lazy_import_invalid_raises(self):
        with pytest.raises(AttributeError):
            from backend.api import services
            services.__getattr__("NonexistentClass")


class TestDataProcessingLazyImport:
    """Test backend/core/data_processing/__init__.py lazy loading."""

    def test_lazy_import_data_initial_validate(self):
        from backend.core.data_processing import data_initial_validate
        assert callable(data_initial_validate)

    def test_lazy_import_preprocessing(self):
        from backend.core.data_processing import preprocessing
        assert callable(preprocessing)

    def test_lazy_import_invalid_raises(self):
        with pytest.raises(AttributeError):
            from backend.core import data_processing
            data_processing.__getattr__("nonexistent_function")
