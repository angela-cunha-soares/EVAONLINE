"""
Data Results Module - ETo Results Presentation.

This module provides components for displaying ETo calculation results,
including tables, statistics, graphics, and layouts.

Components:
- results_tables: Formatted tables for displaying climate data and results
- results_statistical: Statistical analysis and tests (descriptive stats,
  normality, correlation, water balance)
- results_graphs: Plotly graphics for ETo visualization (temperature,
  radiation, precipitation, heatmaps)
- results_layout: Tab-based layout orchestrating tables, stats, and graphics
"""

from backend.core.data_results.results_graphs import (
    plot_eto_vs_radiation,
    plot_eto_vs_temperature,
    plot_heatmap,
    plot_temp_rad_prec,
)
from backend.core.data_results.results_layout import (
    create_results_layout_simplified,
    create_results_tabs,
)
from backend.core.data_results.results_statistical import (
    display_correlation_matrix,
    display_cumulative_distribution,
    display_daily_data,
    display_descriptive_stats,
    display_eto_summary,
    display_normality_test,
    display_seasonality_test,
    display_trend_analysis,
)
from backend.core.data_results.results_tables import display_results_table

__all__ = [
    # Tables
    "display_results_table",
    # Statistical displays
    "display_daily_data",
    "display_descriptive_stats",
    "display_normality_test",
    "display_correlation_matrix",
    "display_eto_summary",
    "display_trend_analysis",
    "display_seasonality_test",
    "display_cumulative_distribution",
    # Graphics
    "plot_eto_vs_temperature",
    "plot_eto_vs_radiation",
    "plot_temp_rad_prec",
    "plot_heatmap",
    # Layouts
    "create_results_tabs",
    "create_results_layout_simplified",
]
