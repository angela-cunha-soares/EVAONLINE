"""
Unit Tests – backend.core.data_results.__init__

Verifies that the public re-exports declared in __all__ are importable
from the top-level package.
"""

import pytest


class TestDataResultsInit:
    """Ensure every symbol listed in __all__ is importable."""

    def test_all_exports_are_importable(self):
        import backend.core.data_results as pkg

        for name in pkg.__all__:
            assert hasattr(pkg, name), f"{name} not found in data_results package"

    # -- Tables --
    def test_display_results_table_importable(self):
        from backend.core.data_results import display_results_table  # noqa: F401

    # -- Statistical --
    @pytest.mark.parametrize(
        "name",
        [
            "display_daily_data",
            "display_descriptive_stats",
            "display_normality_test",
            "display_correlation_matrix",
            "display_eto_summary",
            "display_trend_analysis",
            "display_seasonality_test",
            "display_cumulative_distribution",
        ],
    )
    def test_statistical_exports(self, name):
        import backend.core.data_results as pkg

        assert callable(getattr(pkg, name))

    # -- Graphs --
    @pytest.mark.parametrize(
        "name",
        [
            "plot_eto_vs_temperature",
            "plot_eto_vs_radiation",
            "plot_temp_rad_prec",
            "plot_heatmap",
        ],
    )
    def test_graph_exports(self, name):
        import backend.core.data_results as pkg

        assert callable(getattr(pkg, name))

    # -- Layouts --
    @pytest.mark.parametrize(
        "name",
        [
            "create_results_tabs",
            "create_results_layout_simplified",
        ],
    )
    def test_layout_exports(self, name):
        import backend.core.data_results as pkg

        assert callable(getattr(pkg, name))
