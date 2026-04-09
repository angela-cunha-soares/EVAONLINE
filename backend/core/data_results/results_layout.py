"""
Results Layout with Tabs - Table/Statistics and Graphics.

Two-tab structure:
- Tab 1: Complete table with climate variables + ETos + statistics
- Tab 2: Statistical and comparison graphics
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from backend.core.data_results.results_graphs import (
    plot_eto_vs_radiation,
    plot_eto_vs_temperature,
    plot_heatmap,
    plot_temp_rad_prec,
)
from backend.core.data_results.results_statistical import (
    create_deficit_chart_section,
    display_descriptive_stats,
    display_eto_summary,
    display_normality_test,
)
from backend.core.data_results.results_tables import (
    display_results_table,
)
from shared_utils.get_translations import t


def _table_download_buttons(table_id: str, lang: str = "pt"):
    """Create compact CSV + Excel download buttons for a table section."""
    return html.Div(
        dbc.ButtonGroup(
            [
                dbc.Button(
                    [html.I(className="bi bi-filetype-csv me-1"), "CSV"],
                    id=f"btn-dl-{table_id}-csv",
                    size="sm",
                    color="success",
                    outline=True,
                ),
                dbc.Button(
                    [html.I(className="bi bi-file-earmark-spreadsheet me-1"), "Excel"],
                    id=f"btn-dl-{table_id}-excel",
                    size="sm",
                    color="primary",
                    outline=True,
                ),
            ],
            size="sm",
        ),
        className="d-flex justify-content-end mt-2 mb-1",
    )


def _chart_download_buttons(chart_id: str, lang: str = "pt"):
    """Create compact PNG + JPG download buttons for a chart section."""
    return html.Div(
        dbc.ButtonGroup(
            [
                dbc.Button(
                    [html.I(className="bi bi-file-earmark-image me-1"), "PNG"],
                    id=f"btn-dl-chart-{chart_id}-png",
                    size="sm",
                    color="info",
                    outline=True,
                ),
                dbc.Button(
                    [html.I(className="bi bi-file-earmark-image me-1"), "JPG"],
                    id=f"btn-dl-chart-{chart_id}-jpg",
                    size="sm",
                    color="warning",
                    outline=True,
                ),
            ],
            size="sm",
        ),
        className="d-flex justify-content-end mt-2 mb-1",
    )


def create_results_tabs(df, sources=None, lang: str = "pt", mode: str = ""):
    """
    Create results layout with two tabs.

    Args:
        df: DataFrame with results
        sources: List of data sources used
        lang: Language for translations
        mode: Operation mode (e.g. 'DASHBOARD_FORECAST')

    Returns:
        dbc.Tabs component with two tabs
    """
    if sources is None:
        sources = []

    # Tab 1: Table & Statistics
    tab1_content = dbc.Card(
        dbc.CardBody(
            [
                # Title
                html.H4(
                    [
                        html.I(className="bi bi-table me-2"),
                        t(lang, "results", "data_table_title", default="Results - Data Table"),
                    ],
                    className="results-section-title",
                ),
                # Climate data table
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(className="bi bi-table me-2"),
                                t(lang, "results", "daily_climate_data", default="Daily Climate Data"),
                            ],
                            className="results-table-title",
                        ),
                        display_results_table(df, lang),
                        _table_download_buttons("climate", lang),
                    ],
                    className="mb-5",
                ),
                # Descriptive statistics
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(className="bi bi-calculator me-2"),
                                t(lang, "statistics", "descriptive", default="Descriptive Statistics"),
                            ],
                            className="results-table-title",
                        ),
                        display_descriptive_stats(df, lang, mode=mode),
                        _table_download_buttons("stats", lang),
                    ],
                    className="mb-5",
                ),
                # ETo summary
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(className="bi bi-droplet me-2"),
                                t(lang, "results", "eto_summary_title", default="ETo Summary and Water Balance"),
                            ],
                            className="results-table-title",
                        ),
                        display_eto_summary(df, lang),
                        _table_download_buttons("eto-summary", lang),
                    ],
                    className="mb-5",
                ),
                # Normality test
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(className="bi bi-graph-up me-2"),
                                t(lang, "results", "normality_test_shapiro", default="Normality Test (Shapiro-Wilk)"),
                            ],
                            className="results-table-title",
                        ),
                        display_normality_test(df, lang, mode=mode),
                    ]
                    + (
                        [_table_download_buttons("normality", lang)]
                        if mode != "DASHBOARD_FORECAST" and len(df) >= 30
                        else []
                    ),
                    className="mb-4",
                ),
            ]
        ),
        className="mt-3 shadow-sm",
    )

    # Tab 2: Graphics
    tab2_content = dbc.Card(
        dbc.CardBody(
            [
                # Title
                html.H4(
                    [
                        html.I(className="bi bi-graph-up me-2"),
                        t(lang, "results", "graphical_analysis", default="Results - Graphical Analysis"),
                    ],
                    className="results-section-title",
                ),
                # Déficit Hídrico Section
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(className="bi bi-droplet-half me-2"),
                                t(lang, "results", "water_deficit_title", default="Water Deficit"),
                            ],
                            className="results-table-title",
                        ),
                        create_deficit_chart_section(df, lang),
                        _chart_download_buttons("deficit", lang),
                    ],
                    className="mb-5",
                ),
                # Climate graphics
                html.Div(
                    [
                        html.H5(
                            [
                                html.I(
                                    className="bi bi-thermometer-half me-2"
                                ),
                                t(lang, "results", "climate_analysis", default="Climate Analysis"),
                            ],
                            className="results-table-title",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H6(
                                            t(lang, "charts", "eto_vs_temp", default="ETo vs Temperature"),
                                            className="text-center mb-2",
                                        ),
                                        dcc.Graph(
                                            id="chart-eto-temp",
                                            figure=plot_eto_vs_temperature(
                                                df, lang
                                            ),
                                            config={"displayModeBar": False},
                                            style={"height": "550px"},
                                        ),
                                        _chart_download_buttons("eto-temp", lang),
                                    ],
                                    md=12,
                                    className="mb-5",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H6(
                                            t(lang, "charts", "eto_vs_rad", default="ETo vs Solar Radiation"),
                                            className="text-center mb-2",
                                        ),
                                        dcc.Graph(
                                            id="chart-eto-rad",
                                            figure=plot_eto_vs_radiation(
                                                df, lang
                                            ),
                                            config={"displayModeBar": False},
                                            style={"height": "550px"},
                                        ),
                                        _chart_download_buttons("eto-rad", lang),
                                    ],
                                    md=12,
                                    className="mb-5",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H6(
                                            t(lang, "charts", "temp_rad_prec", default="Temperature & Precipitation"),
                                            className="text-center mb-2",
                                        ),
                                        dcc.Graph(
                                            id="chart-temp-rad-prec",
                                            figure=plot_temp_rad_prec(
                                                df, lang
                                            ),
                                            config={"displayModeBar": False},
                                            style={"height": "550px"},
                                        ),
                                        _chart_download_buttons("temp-rad-prec", lang),
                                    ],
                                    md=12,
                                    className="mb-5",
                                ),
                            ]
                        ),
                    ],
                    className="mb-5",
                ),
                # Correlation heatmap (hidden when < 30 days or forecast)
                (
                    dbc.Alert(
                        [
                            html.I(className="bi bi-info-circle me-2"),
                            (
                                t(lang, "statistics", "forecast_heatmap_insufficient",
                                  default="Heatmap not shown: insufficient sample for reliable correlations in forecast mode (6 days).")
                                if mode == "DASHBOARD_FORECAST"
                                else t(lang, "statistics", "heatmap_insufficient",
                                       default="Heatmap not shown: at least 30 days required. Currently: {days} days.").format(days=len(df))
                            ),
                        ],
                        color="info",
                        className="mb-4",
                    )
                    if mode == "DASHBOARD_FORECAST" or len(df) < 30
                    else html.Div(
                        [
                            html.H5(
                                [
                                    html.I(className="bi bi-grid-3x3 me-2"),
                                    t(lang, "results", "correlation_heatmap", default="Heatmap - Correlations"),
                                ],
                                className="results-table-title",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Graph(
                                                id="chart-heatmap",
                                                figure=plot_heatmap(df, lang),
                                                config={"displayModeBar": False},
                                                style={"height": "600px"},
                                            ),
                                            _chart_download_buttons("heatmap", lang),
                                        ],
                                        md=12,
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",
                    )
                ),
            ]
        ),
        className="mt-3 shadow-sm",
    )

    # Create tabs
    tabs = dbc.Tabs(
        [
            dbc.Tab(
                tab1_content,
                label=f"\U0001f4ca {t(lang, 'results', 'tab_table_stats', default='Table & Statistics')}",
                tab_id="tab-table",
            ),
            dbc.Tab(
                tab2_content,
                label=f"\U0001f4c8 {t(lang, 'results', 'tab_charts', default='Charts')}",
                tab_id="tab-graphics",
            ),
        ],
        id="results-tabs",
        active_tab="tab-table",
        className="mb-3 nav-tabs results-tabs",
    )

    return tabs


def create_results_layout_simplified(df, sources=None, lang: str = "pt"):
    """
    Create simplified results layout with tabs (no comparison metrics).

    Focus on climate statistics and analysis, not validation metrics.
    Validation metrics (R², MAE, KGE, etc.) are for historical validation
    (EVAonline vs Xavier vs Open-Meteo), not for dashboard display.

    Args:
        df: DataFrame with results
        sources: List of data sources
        lang: Language

    Returns:
        dbc.Container with tabs layout
    """
    layout = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [create_results_tabs(df, sources, lang)],
                        xs=12,
                        className="mb-3",
                    ),
                ]
            )
        ],
        fluid=True,
        className="results-layout",
    )

    return layout
