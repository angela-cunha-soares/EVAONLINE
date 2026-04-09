"""
End-to-End Tests - Spatial Analysis Flow
"""

import pytest


@pytest.mark.e2e
@pytest.mark.requires_docker
@pytest.mark.slow
class TestSpatialAnalysisFlow:
    """Tests the complete spatial analysis workflow."""

    def test_regional_coverage_analysis(self):
        """Testa análise de cobertura regional."""
        from backend.core.utils.geo_utils import detect_geographic_region

        # Tests regional coverage analysis
        assert detect_geographic_region(-22.9, -43.2) == "brasil"
        assert detect_geographic_region(40.71, -74.0) == "usa"
        assert detect_geographic_region(60.17, 24.94) == "nordic"
        assert detect_geographic_region(48.85, 2.35) == "global"
