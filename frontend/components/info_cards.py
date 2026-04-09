"""
Information Cards for EVAonline Dashboard.

Provides educational and transparency cards:
1. FAO-56 Method
2. Data Sources
3. EVAonline Method
4. ETo Comparison & Validation
5. Real-Time Metrics

These cards enhance user understanding and build trust through transparency.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_fao_method_card():
    """
    Create FAO-56 Method information card.

    Explains the international standard for ETo calculation.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="fas fa-flask me-2"), "FAO-56 Method"]
                )
            ),
            dbc.CardBody(
                [
                    html.P(
                        "The FAO-56 Penman-Monteith method is the international "
                        "standard for calculating reference evapotranspiration (ET₀).",
                        className="card-text",
                    ),
                    html.H6("Required parameters:", className="mt-3"),
                    html.Ul(
                        [
                            html.Li("Air temperature (max, min, mean)"),
                            html.Li("Relative humidity"),
                            html.Li("Wind speed (2m height)"),
                            html.Li("Solar radiation"),
                        ]
                    ),
                    html.Hr(),
                    html.Small(
                        [
                            html.I(className="fas fa-book me-1"),
                            "Reference: Allen et al. (1998) - FAO Paper 56",
                        ],
                        className="text-muted",
                    ),
                ]
            ),
        ],
        className="mb-3 shadow-sm",
    )


def create_data_sources_card():
    """
    Create Data Sources information card.

    Lists all climate data sources with coverage and licenses.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="fas fa-database me-2"), "Data Sources"]
                )
            ),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="fas fa-globe me-1"),
                                    "Open-Meteo",
                                ]
                            ),
                            html.P(
                                "High-resolution global data (recommended)",
                                className="small mb-1",
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Archive: 1990-present (historical)",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Forecast: Today + 5 days",
                                        className="small",
                                    ),
                                    html.Li(
                                        "License: CC BY 4.0", className="small"
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="fas fa-satellite me-1"),
                                    "NASA POWER",
                                ]
                            ),
                            html.P(
                                "Global historical data since 1990",
                                className="small mb-1",
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Resolution: ~55km", className="small"
                                    ),
                                    html.Li(
                                        "License: Public Domain",
                                        className="small",
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="fas fa-snowflake me-1"),
                                    "MET Norway",
                                ]
                            ),
                            html.P(
                                "Nordic region high-quality data",
                                className="small mb-1",
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Resolution: 1km (Nordic), 9km (Global)",
                                        className="small",
                                    ),
                                    html.Li(
                                        "License: CC BY 4.0", className="small"
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="fas fa-flag-usa me-1"),
                                    "NWS (USA only)",
                                ]
                            ),
                            html.P(
                                "Real-time + forecasts",
                                className="small mb-1",
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "NOAA National Weather Service",
                                        className="small",
                                    ),
                                    html.Li(
                                        "License: Public Domain",
                                        className="small",
                                    ),
                                ],
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-3 shadow-sm",
    )


def create_evaonline_method_card():
    """
    Create EVAonline Method information card.

    Explains our multi-source Kalman fusion approach.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="fas fa-bolt me-2"), "EVAonline Method"]
                )
            ),
            dbc.CardBody(
                [
                    html.P("Our ETo calculation uses:", className="fw-bold"),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-layer-group me-1"
                                    ),
                                    "1️⃣ Multi-source Kalman Fusion",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Combines 2-3 climate sources intelligently",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Regional weights (USA/Nordic/Global)",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Reduces outliers and measurement errors",
                                        className="small",
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-map-marked-alt me-1"
                                    ),
                                    "2️⃣ Local Climate Normals",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "27 Brazilian cities with 1991-2020 normals",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Adaptive Kalman filter with regional context",
                                        className="small",
                                    ),
                                    html.Li(
                                        "High-precision mode: R²=0.69, KGE=0.81",
                                        className="small",
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-globe-americas me-1"
                                    ),
                                    "3️⃣ Global Fallback",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Physical limits validation (WMO standards)",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Simple Kalman filter for any location",
                                        className="small",
                                    ),
                                    html.Li(
                                        "Ensures worldwide coverage",
                                        className="small",
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Hr(),
                    html.Small(
                        [
                            html.I(className="fas fa-chart-line me-1"),
                            "Validation: 17 cities, 30 years | Accuracy: MAE=0.42mm, PBIAS=0.7%, NSE=0.68",
                        ],
                        className="text-muted",
                    ),
                ]
            ),
        ],
        className="mb-3 shadow-sm",
    )


def create_comparison_explanation_card():
    """
    Create ETo Comparison & Validation explanation card.

    Explains why we show two methods and what to expect.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [
                        html.I(className="fas fa-search me-2"),
                        "ETo Comparison & Validation",
                    ]
                )
            ),
            dbc.CardBody(
                [
                    html.P(
                        "Two calculation methods for transparency:",
                        className="fw-bold",
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-star me-1 text-warning"
                                    ),
                                    "ETo EVAonline (Recommended)",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "✓ Multi-source Kalman fusion",
                                        className="small text-success",
                                    ),
                                    html.Li(
                                        "✓ Local climate normals (when available)",
                                        className="small text-success",
                                    ),
                                    html.Li(
                                        "✓ Regional optimization",
                                        className="small text-success",
                                    ),
                                    html.Li(
                                        "✓ Validated against Xavier et al. (2016)",
                                        className="small text-success",
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-check-circle me-1 text-info"
                                    ),
                                    "ETo Open-Meteo (Reference)",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "• Standard FAO-56 calculation",
                                        className="small",
                                    ),
                                    html.Li(
                                        "• Single ensemble source",
                                        className="small",
                                    ),
                                    html.Li(
                                        "• No local climate adjustment",
                                        className="small",
                                    ),
                                    html.Li(
                                        "• Global coverage", className="small"
                                    ),
                                ],
                                className="mb-2",
                            ),
                        ]
                    ),
                    html.Hr(),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(className="fas fa-lightbulb me-1"),
                                    "Why two methods?",
                                ]
                            ),
                            html.P(
                                "Showing both demonstrates EVAonline's improvement over "
                                "standard methods. Typical agreement: R² > 0.90",
                                className="small",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-info-circle me-1"
                                    ),
                                    "When EVAonline may differ more:",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Locations with local climate normals (better!)",
                                        className="small text-primary",
                                    ),
                                    html.Li(
                                        "Outlier correction (more stable!)",
                                        className="small text-primary",
                                    ),
                                    html.Li(
                                        "Multi-source fusion (higher quality!)",
                                        className="small text-primary",
                                    ),
                                ],
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-3 shadow-sm",
    )


def create_metrics_card(metrics: dict = None, interpretation: dict = None):
    """
    Create Real-Time Metrics card.

    Args:
        metrics: Dict from EToComparisonService.calculate_metrics()
        interpretation: Dict from EToComparisonService.interpret_metrics()

    Returns:
        Dash Bootstrap Card component
    """
    if metrics is None:
        # Default placeholder when no data
        metrics = {
            "r2": 0.0,
            "mae": 0.0,
            "pbias": 0.0,
            "kge": 0.0,
            "n_points": 0,
        }
        interpretation = {
            "overall": "No data available",
            "r2": "No data",
            "mae": "No data",
            "kge": "No data",
            "pbias": "No data",
        }

    # Color badges based on quality
    def get_badge_color(value, thresholds):
        """Get Bootstrap color based on value and thresholds."""
        if value >= thresholds[0]:
            return "success"
        elif value >= thresholds[1]:
            return "warning"
        else:
            return "danger"

    r2_color = get_badge_color(metrics["r2"], [0.90, 0.75])
    mae_color = (
        "success"
        if metrics["mae"] < 0.5
        else "warning" if metrics["mae"] < 1.0 else "danger"
    )
    kge_color = get_badge_color(metrics["kge"], [0.85, 0.70])
    pbias_color = (
        "success"
        if abs(metrics["pbias"]) <= 5
        else "warning" if abs(metrics["pbias"]) <= 10 else "danger"
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [
                        html.I(className="fas fa-chart-bar me-2"),
                        "Validation Metrics (This Request)",
                    ]
                )
            ),
            dbc.CardBody(
                [
                    html.P(
                        "Comparing EVAonline vs Open-Meteo:",
                        className="fw-bold mb-3",
                    ),
                    # Metrics table
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Strong("R² (Correlation):"),
                                            html.Span(
                                                f" {metrics['r2']:.2f}",
                                                className="ms-2",
                                            ),
                                            dbc.Badge(
                                                interpretation["r2"],
                                                color=r2_color,
                                                className="ms-2",
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("MAE (Mean Error):"),
                                            html.Span(
                                                f" {metrics['mae']:.2f} mm",
                                                className="ms-2",
                                            ),
                                            dbc.Badge(
                                                interpretation["mae"],
                                                color=mae_color,
                                                className="ms-2",
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("PBIAS (Bias):"),
                                            html.Span(
                                                f" {metrics['pbias']:+.1f}%",
                                                className="ms-2",
                                            ),
                                            dbc.Badge(
                                                interpretation["pbias"],
                                                color=pbias_color,
                                                className="ms-2",
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("KGE (Quality):"),
                                            html.Span(
                                                f" {metrics['kge']:.2f}",
                                                className="ms-2",
                                            ),
                                            dbc.Badge(
                                                interpretation["kge"],
                                                color=kge_color,
                                                className="ms-2",
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                                md=12,
                            ),
                        ]
                    ),
                    html.Hr(),
                    html.Div(
                        [
                            html.Small(
                                [
                                    html.I(className="fas fa-calendar me-1"),
                                    f"Period: {metrics['n_points']} days",
                                ],
                                className="text-muted d-block",
                            ),
                            html.Small(
                                [
                                    html.I(className="fas fa-bullseye me-1"),
                                    f"Agreement: {interpretation['overall']}",
                                ],
                                className="text-muted d-block",
                            ),
                        ]
                    ),
                    html.Hr(),
                    html.Div(
                        [
                            html.H6(
                                [
                                    html.I(
                                        className="fas fa-info-circle me-1"
                                    ),
                                    "Interpretation:",
                                ]
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "R² > 0.90: Methods highly consistent",
                                        className="small",
                                    ),
                                    html.Li(
                                        "MAE < 0.5mm: Practical equivalence",
                                        className="small",
                                    ),
                                    html.Li(
                                        "PBIAS < ±5%: No systematic bias",
                                        className="small",
                                    ),
                                    html.Li(
                                        "KGE > 0.85: Excellent agreement",
                                        className="small",
                                    ),
                                ]
                            ),
                        ],
                        className="mt-3",
                    ),
                ]
            ),
        ],
        className="mb-3 shadow-sm",
    )


def create_info_sidebar(metrics: dict = None, interpretation: dict = None):
    """
    Create complete information sidebar with all cards.

    Args:
        metrics: Optional metrics dict for real-time card
        interpretation: Optional interpretation dict

    Returns:
        Dash html.Div with all info cards
    """
    return html.Div(
        [
            html.H4(
                [
                    html.I(className="fas fa-info-circle me-2"),
                    "About EVAonline",
                ],
                className="mb-3",
            ),
            create_fao_method_card(),
            create_data_sources_card(),
            create_evaonline_method_card(),
            create_comparison_explanation_card(),
            create_metrics_card(metrics, interpretation),
        ],
        className="info-sidebar",
    )


def create_collapsible_info_section(
    metrics: dict = None, interpretation: dict = None
):
    """
    Create collapsible accordion for mobile/compact view.

    Args:
        metrics: Optional metrics dict
        interpretation: Optional interpretation dict

    Returns:
        Dash Bootstrap Accordion component
    """
    return dbc.Accordion(
        [
            dbc.AccordionItem(
                create_fao_method_card().children[1],  # CardBody only
                title="🔬 FAO-56 Method",
            ),
            dbc.AccordionItem(
                create_data_sources_card().children[1],
                title="🌐 Data Sources",
            ),
            dbc.AccordionItem(
                create_evaonline_method_card().children[1],
                title="⚡ EVAonline Method",
            ),
            dbc.AccordionItem(
                create_comparison_explanation_card().children[1],
                title="🔍 ETo Comparison",
            ),
            dbc.AccordionItem(
                create_metrics_card(metrics, interpretation).children[1],
                title="📈 Validation Metrics",
            ),
        ],
        start_collapsed=True,
        className="mb-3",
    )
