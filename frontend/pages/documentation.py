# filepath: frontend/pages/documentation.py
"""
Página de Documentação do EVAonline.
Suporta tradução dinâmica PT/EN via shared_utils.get_translations.
"""

import logging

import dash_bootstrap_components as dbc
from dash import html

from shared_utils.get_translations import t

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Tradução com fallback
# =============================================================================
def _t(lang, *keys, default=""):
    """Wrapper para tradução com prefixo 'documentation' automático."""
    return t(lang, "documentation", *keys, default=default)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _create_quick_start_section(lang):
    """How to use EVAonline - Quick and objective guide."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "quick_start_title"),
                        id="quick-start",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5(
                                        _t(lang, "quick_start_steps_title"),
                                        className="mb-4",
                                    ),
                                    # Step 1
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            dbc.Badge(
                                                                "1",
                                                                color="primary",
                                                                className="me-3 doc-step-badge",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.H6(
                                                                        _t(lang, "step1_title"),
                                                                        className="mb-1",
                                                                    ),
                                                                    html.Small(
                                                                        [
                                                                            _t(lang, "step1_desc"),
                                                                            html.Strong(
                                                                                _t(lang, "step1_elevation")
                                                                            ),
                                                                            _t(lang, "step1_elevation_detail"),
                                                                            html.Strong(
                                                                                _t(lang, "step1_timezone")
                                                                            ),
                                                                            _t(lang, "step1_and"),
                                                                            html.Strong(
                                                                                _t(lang, "step1_region")
                                                                            ),
                                                                            _t(lang, "step1_region_detail"),
                                                                        ],
                                                                        className="text-muted",
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        className="d-flex align-items-start",
                                                    )
                                                ]
                                            )
                                        ],
                                        className="mb-2 border-start border-primary border-3",
                                    ),
                                    # Step 2
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            dbc.Badge(
                                                                "2",
                                                                color="primary",
                                                                className="me-3 doc-step-badge",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.H6(
                                                                        _t(lang, "step2_title"),
                                                                        className="mb-1",
                                                                    ),
                                                                    html.Small(
                                                                        [
                                                                            _t(lang, "step2_desc_select"),
                                                                            html.Strong(
                                                                                _t(lang, "step2_historical")
                                                                            ),
                                                                            _t(lang, "step2_historical_detail"),
                                                                            html.Strong(
                                                                                _t(lang, "step2_recent")
                                                                            ),
                                                                            _t(lang, "step2_recent_detail"),
                                                                            html.Strong(
                                                                                _t(lang, "step2_forecast")
                                                                            ),
                                                                            _t(lang, "step2_forecast_detail"),
                                                                        ],
                                                                        className="text-muted",
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        className="d-flex align-items-start",
                                                    )
                                                ]
                                            )
                                        ],
                                        className="mb-2 border-start border-primary border-3",
                                    ),
                                    # Step 3
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            dbc.Badge(
                                                                "3",
                                                                color="primary",
                                                                className="me-3 doc-step-badge",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.H6(
                                                                        _t(lang, "step3_title"),
                                                                        className="mb-1",
                                                                    ),
                                                                    html.Small(
                                                                        [
                                                                            _t(lang, "step3_desc"),
                                                                            html.Strong(
                                                                                _t(lang, "step3_kalman")
                                                                            ),
                                                                            _t(lang, "step3_calculates"),
                                                                            html.Strong(
                                                                                _t(lang, "step3_fao56")
                                                                            ),
                                                                            _t(lang, "step3_displays"),
                                                                        ],
                                                                        className="text-muted",
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        className="d-flex align-items-start",
                                                    )
                                                ]
                                            )
                                        ],
                                        className="mb-3 border-start border-primary border-3",
                                    ),
                                    html.Small(
                                        _t(
                                            lang,
                                            "step3_progress_path",
                                            default="Current dashboard path: asynchronous task-status updates via Redis polling every 2s (WebSocket endpoint remains available).",
                                        ),
                                        className="text-muted d-block mb-3",
                                    ),
                                    dbc.Alert(
                                        [
                                            html.I(
                                                className="bi bi-lightning-charge-fill me-2"
                                            ),
                                            html.Strong(_t(lang, "fully_automatic_title")),
                                            _t(lang, "fully_automatic_desc"),
                                        ],
                                        color="success",
                                        className="mb-0",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_interactive_map_section(lang):
    """Describes the interactive map and its layers."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "map_title"),
                        id="interactive-map",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.P(
                                        [
                                            _t(lang, "map_intro"),
                                        ],
                                        className="mb-4",
                                    ),
                                    html.H5(_t(lang, "map_controls_title"), className="mb-3"),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        [
                                                            dbc.CardBody(
                                                                [
                                                                    html.Div(
                                                                        [
                                                                            html.Span(
                                                                                "🗺️",
                                                                                className="doc-emoji-icon",
                                                                            ),
                                                                            html.Strong(
                                                                                _t(lang, "map_layer_control"),
                                                                                className="ms-2",
                                                                            ),
                                                                        ],
                                                                        className="mb-2",
                                                                    ),
                                                                    html.P(
                                                                        _t(lang, "map_layer_control_desc"),
                                                                        className="small text-muted mb-0",
                                                                    ),
                                                                ]
                                                            )
                                                        ],
                                                        className="h-100 border-start border-primary border-3",
                                                    ),
                                                ],
                                                md=6,
                                                className="mb-3",
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Card(
                                                        [
                                                            dbc.CardBody(
                                                                [
                                                                    html.Div(
                                                                        [
                                                                            html.Span(
                                                                                "📍",
                                                                                className="doc-emoji-icon",
                                                                            ),
                                                                            html.Strong(
                                                                                _t(lang, "map_geolocation"),
                                                                                className="ms-2",
                                                                            ),
                                                                        ],
                                                                        className="mb-2",
                                                                    ),
                                                                    html.P(
                                                                        _t(lang, "map_geolocation_desc"),
                                                                        className="small text-muted mb-0",
                                                                    ),
                                                                ]
                                                            )
                                                        ],
                                                        className="h-100 border-start border-info border-3",
                                                    ),
                                                ],
                                                md=6,
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                    html.H5(
                                        _t(lang, "map_layers_title"),
                                        className="mb-3 mt-4",
                                    ),
                                    dbc.Table(
                                        [
                                            html.Thead(
                                                html.Tr(
                                                    [
                                                        html.Th(
                                                            _t(lang, "map_th_layer"),
                                                            className="doc-table-col-wide",
                                                        ),
                                                        html.Th(_t(lang, "map_th_description")),
                                                        html.Th(
                                                            _t(lang, "map_th_default"),
                                                            className="doc-table-col-narrow",
                                                        ),
                                                    ]
                                                )
                                            ),
                                            html.Tbody(
                                                [
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.Img(
                                                                        src="/assets/images/Flag_of_Brazil.svg",
                                                                        className="doc-flag-icon",
                                                                    ),
                                                                    "Brasil - Estados",
                                                                ]
                                                            ),
                                                            html.Td(
                                                                _t(lang, "map_layer_estados_desc")
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    "ON",
                                                                    color="success",
                                                                ),
                                                                className="text-center",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.Span(
                                                                        "🌾",
                                                                        className="me-1",
                                                                    ),
                                                                    "MATOPIBA - Região",
                                                                ]
                                                            ),
                                                            html.Td(
                                                                [
                                                                    _t(lang, "map_layer_matopiba_desc_start"),
                                                                    html.Strong(
                                                                        "Ma"
                                                                    ),
                                                                    "ranhão, ",
                                                                    html.Strong(
                                                                        "To"
                                                                    ),
                                                                    "cantins, ",
                                                                    html.Strong(
                                                                        "Pi"
                                                                    ),
                                                                    "auí, and " if lang == "en" else "auí e ",
                                                                    html.Strong(
                                                                        "Ba"
                                                                    ),
                                                                    _t(lang, "map_layer_matopiba_desc_end"),
                                                                ]
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    "OFF",
                                                                    color="secondary",
                                                                ),
                                                                className="text-center",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.Span(
                                                                        "🏘️",
                                                                        className="me-1",
                                                                    ),
                                                                    "337 Cidades",
                                                                ]
                                                            ),
                                                            html.Td(
                                                                _t(lang, "map_layer_cities_desc")
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    "OFF",
                                                                    color="secondary",
                                                                ),
                                                                className="text-center",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.Span(
                                                                        "🎓",
                                                                        className="me-1",
                                                                    ),
                                                                    "Piracicaba/SP",
                                                                ]
                                                            ),
                                                            html.Td(
                                                                [
                                                                    _t(lang, "map_layer_piracicaba_desc_start"),
                                                                    html.Strong(
                                                                        "ESALQ/USP"
                                                                    ),
                                                                    ' (Escola Superior de Agricultura "Luiz de Queiroz"), '
                                                                    if lang == "pt"
                                                                    else " (College of Agriculture), ",
                                                                    _t(lang, "map_layer_piracicaba_desc_end"),
                                                                ]
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    "ON",
                                                                    color="success",
                                                                ),
                                                                className="text-center",
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                        ],
                                        bordered=True,
                                        hover=True,
                                        responsive=True,
                                        className="mb-0",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_operation_modes_section(lang):
    """Describes the 3 operational modes."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "modes_title"),
                        id="modos",
                        className="mb-4 doc-section-title",
                    ),
                    html.P(
                        _t(lang, "modes_intro"),
                        className="text-muted mb-3",
                    ),
                    dbc.Row(
                        [
                            # Historical
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            [
                                                html.I(
                                                    className="bi bi-clock-history me-2"
                                                ),
                                                html.Strong(_t(lang, "mode_historical_title")),
                                            ],
                                            className="doc-card-header-historical",
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    _t(lang, "mode_historical_desc"),
                                                    className="mb-3",
                                                ),
                                                html.Ul(
                                                    [
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_period")
                                                                ),
                                                                _t(lang, "mode_historical_period"),
                                                                dbc.Badge(
                                                                    _t(lang, "mode_historical_delay"),
                                                                    color="warning",
                                                                    className="ms-1",
                                                                    pill=True,
                                                                ),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_max_request")
                                                                ),
                                                                _t(lang, "mode_historical_max"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_sources")
                                                                ),
                                                                _t(lang, "mode_historical_sources"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_delivery")
                                                                ),
                                                                _t(lang, "mode_historical_delivery"),
                                                            ]
                                                        ),
                                                    ],
                                                    className="small",
                                                ),
                                                dbc.Badge(
                                                    _t(lang, "mode_historical_badge1"),
                                                    color="info",
                                                    className="mt-2 me-1",
                                                ),
                                                dbc.Badge(
                                                    _t(lang, "mode_historical_badge2"),
                                                    color="secondary",
                                                    className="mt-2",
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="h-100 shadow-sm",
                                ),
                                md=4,
                                className="mb-3",
                            ),
                            # Recent
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            [
                                                html.I(
                                                    className="bi bi-calendar-check me-2"
                                                ),
                                                html.Strong(_t(lang, "mode_recent_title")),
                                            ],
                                            className="doc-card-header-recent",
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    _t(lang, "mode_recent_desc"),
                                                    className="mb-3",
                                                ),
                                                html.Ul(
                                                    [
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_period")
                                                                ),
                                                                _t(lang, "mode_recent_period"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_sources")
                                                                ),
                                                                _t(lang, "mode_recent_sources"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_delivery")
                                                                ),
                                                                _t(lang, "mode_recent_delivery"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_gap_filling")
                                                                ),
                                                                _t(lang, "mode_recent_gap"),
                                                            ]
                                                        ),
                                                    ],
                                                    className="small",
                                                ),
                                                dbc.Badge(
                                                    _t(lang, "mode_recent_badge"),
                                                    color="success",
                                                    className="mt-2",
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="h-100 shadow-sm",
                                ),
                                md=4,
                                className="mb-3",
                            ),
                            # Forecast
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            [
                                                html.I(
                                                    className="bi bi-cloud-sun me-2"
                                                ),
                                                html.Strong(_t(lang, "mode_forecast_title")),
                                            ],
                                            className="doc-card-header-forecast",
                                        ),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    _t(lang, "mode_forecast_desc"),
                                                    className="mb-3",
                                                ),
                                                html.Ul(
                                                    [
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_period")
                                                                ),
                                                                _t(lang, "mode_forecast_period"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_sources_global")
                                                                ),
                                                                _t(lang, "mode_forecast_sources_global"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_sources_usa")
                                                                ),
                                                                _t(lang, "mode_forecast_sources_usa"),
                                                            ]
                                                        ),
                                                        html.Li(
                                                            [
                                                                html.Strong(
                                                                    _t(lang, "label_delivery")
                                                                ),
                                                                _t(lang, "mode_forecast_delivery"),
                                                            ]
                                                        ),
                                                    ],
                                                    className="small",
                                                ),
                                                dbc.Badge(
                                                    _t(lang, "mode_forecast_badge1"),
                                                    color="warning",
                                                    text_color="dark",
                                                    className="mt-2 me-1",
                                                ),
                                                dbc.Badge(
                                                    _t(lang, "mode_forecast_badge2"),
                                                    color="info",
                                                    className="mt-2",
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="h-100 shadow-sm",
                                ),
                                md=4,
                                className="mb-3",
                            ),
                        ]
                    ),
                    # Mode auto-detection note
                    dbc.Alert(
                        [
                            html.I(className="bi bi-info-circle-fill me-2"),
                            html.Strong(_t(lang, "modes_auto_title")),
                            _t(lang, "modes_auto_desc"),
                        ],
                        color="light",
                        className="mt-2",
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4",
    )


def _create_usa_stations_section(lang):
    """USA NWS Stations automatic detection section."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        [
                            html.Img(
                                src="/assets/images/Flag_of_the_United_States.svg",
                                className="doc-flag-icon",
                            ),
                            _t(lang, "usa_title"),
                        ],
                        id="usa-stations",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.H5(
                                                        _t(lang, "usa_subtitle"),
                                                        className="mb-3",
                                                    ),
                                                    html.P(
                                                        [
                                                            _t(lang, "usa_intro_start"),
                                                            html.Strong(
                                                                _t(lang, "usa_intro_bold")
                                                            ),
                                                            _t(lang, "usa_intro_end"),
                                                        ]
                                                    ),
                                                    html.Ol(
                                                        [
                                                            html.Li(
                                                                [
                                                                    html.Strong(
                                                                        _t(lang, "usa_item1_title")
                                                                    ),
                                                                    _t(lang, "usa_item1_desc"),
                                                                ]
                                                            ),
                                                            html.Li(
                                                                [
                                                                    html.Strong(
                                                                        _t(lang, "usa_item2_title")
                                                                    ),
                                                                    _t(lang, "usa_item2_desc"),
                                                                ]
                                                            ),
                                                            html.Li(
                                                                _t(lang, "usa_item3")
                                                            ),
                                                            html.Li(
                                                                _t(lang, "usa_item4")
                                                            ),
                                                            html.Li(
                                                                _t(lang, "usa_item5")
                                                            ),
                                                        ]
                                                    ),
                                                    dbc.Alert(
                                                        [
                                                            html.I(
                                                                className="bi bi-broadcast-pin me-2"
                                                            ),
                                                            html.Strong(
                                                                _t(lang, "usa_available_in")
                                                            ),
                                                            _t(lang, "usa_available_desc"),
                                                        ],
                                                        color="info",
                                                    ),
                                                ],
                                                md=7,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H6(
                                                        _t(lang, "usa_card_title"),
                                                        className="mb-3",
                                                    ),
                                                    dbc.ListGroup(
                                                        [
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-building me-2 text-primary"
                                                                    ),
                                                                    _t(lang, "usa_card_name"),
                                                                ]
                                                            ),
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-geo-alt me-2 text-danger"
                                                                    ),
                                                                    _t(lang, "usa_card_distance"),
                                                                ]
                                                            ),
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-arrow-up me-2 text-success"
                                                                    ),
                                                                    _t(lang, "usa_card_elevation"),
                                                                ]
                                                            ),
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-thermometer-half me-2 text-warning"
                                                                    ),
                                                                    _t(lang, "usa_card_temp"),
                                                                ]
                                                            ),
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-clock me-2 text-info"
                                                                    ),
                                                                    _t(lang, "usa_card_time"),
                                                                ]
                                                            ),
                                                        ],
                                                        flush=True,
                                                    ),
                                                    html.Hr(),
                                                    html.Small(
                                                        [
                                                            html.Strong(
                                                                _t(lang, "usa_coverage_title")
                                                            ),
                                                            _t(lang, "usa_coverage_desc"),
                                                        ],
                                                        className="text-muted",
                                                    ),
                                                ],
                                                md=5,
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm border-info",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_results_section(lang):
    """Describes all result tabs, tables, charts, statistics, downloads,
    water deficit, ETo comparison, NWS card and ocean detection."""

    def _tab_card(title_key, items_keys, *, badge_indices=None):
        """Build a single tab card with a list of items.

        Parameters
        ----------
        badge_indices : set[int] | None
            0-based indices that should get an ``≥30d`` badge appended.
        """
        badge_indices = badge_indices or set()
        items = []
        for idx, k in enumerate(items_keys):
            content = _t(lang, k)
            if idx in badge_indices:
                content = html.Span(
                    [
                        content,
                        dbc.Badge(
                            "≥30d",
                            color="warning",
                            className="ms-1",
                            pill=True,
                        ),
                    ]
                )
            items.append(html.Li(content))
        return dbc.Card(
            dbc.CardBody(
                [
                    html.Strong(_t(lang, title_key)),
                    html.Ul(items, className="small mb-0"),
                ]
            ),
            className="h-100",
        )

    def _icon_card(icon_cls, color_cls, title_key, desc_key, *, badge=None):
        """Build a centred icon card for a chart entry."""
        title_children: list = [_t(lang, title_key)]
        if badge:
            title_children.append(
                dbc.Badge(badge, color="warning", className="ms-1", pill=True)
            )
        return dbc.Card(
            dbc.CardBody(
                [
                    html.I(className=f"{icon_cls} {color_cls} doc-icon-lg"),
                    html.P(
                        title_children,
                        className="mb-0 mt-2 small fw-bold",
                    ),
                    html.Small(
                        _t(lang, desc_key), className="text-muted"
                    ),
                ],
                className="text-center p-3",
            ),
            className="h-100",
        )

    def _download_card(icon_cls, color, title_key, desc_key):
        """Build a download-option card."""
        return dbc.Card(
            dbc.CardBody(
                [
                    html.I(className=f"{icon_cls} doc-icon-lg text-{color}"),
                    html.P(
                        _t(lang, title_key),
                        className="mb-1 mt-2 small fw-bold",
                    ),
                    html.Small(
                        _t(lang, desc_key), className="text-muted"
                    ),
                ],
                className="text-center p-3",
            ),
            className="h-100",
        )

    def _stats_rule_card(icon_cls, color, title_key, desc_key):
        """Build a stats-rule card."""
        return dbc.Card(
            dbc.CardBody(
                [
                    html.I(className=f"{icon_cls} doc-icon-lg text-{color}"),
                    html.P(
                        _t(lang, title_key),
                        className="mb-1 mt-2 small fw-bold",
                    ),
                    html.Small(
                        _t(lang, desc_key), className="text-muted"
                    ),
                ],
                className="text-center p-3",
            ),
            className="h-100",
        )

    # ── Main layout ──────────────────────────────────────────────
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "results_title"),
                        id="resultados",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5(
                                        _t(lang, "results_subtitle"),
                                        className="mb-4",
                                    ),
                                    # ── 1. Result Tabs ───────────────
                                    html.H6(
                                        _t(lang, "results_tabs_title"),
                                        className="mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "results_tabs_desc"),
                                        className="text-muted mb-2",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                _tab_card(
                                                    "tab_summary",
                                                    [f"tab_summary_{i}" for i in range(1, 7)],
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _tab_card(
                                                    "tab_tables",
                                                    [f"tab_tables_{i}" for i in range(1, 7)],
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _tab_card(
                                                    "tab_charts",
                                                    [f"tab_charts_{i}" for i in range(1, 7)],
                                                    badge_indices={3},  # heatmap ≥30d
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _tab_card(
                                                    "tab_stats",
                                                    [f"tab_stats_{i}" for i in range(1, 7)],
                                                    badge_indices={2, 4, 5},  # Shapiro, CV%, skew/kurt
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                        ]
                                    ),
                                    html.Hr(),
                                    # ── 2. Statistical Analysis Rules ─
                                    html.H6(
                                        _t(lang, "stats_rules_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "stats_rules_intro"),
                                        className="text-muted small mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                _stats_rule_card(
                                                    "bi bi-calendar-check",
                                                    "warning",
                                                    "stats_rule_30days_title",
                                                    "stats_rule_30days_desc",
                                                ),
                                                md=4,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _stats_rule_card(
                                                    "bi bi-cloud-sun",
                                                    "info",
                                                    "stats_rule_forecast_title",
                                                    "stats_rule_forecast_desc",
                                                ),
                                                md=4,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _stats_rule_card(
                                                    "bi bi-grid-3x3",
                                                    "danger",
                                                    "stats_rule_heatmap_title",
                                                    "stats_rule_heatmap_desc",
                                                ),
                                                md=4,
                                                className="mb-2",
                                            ),
                                        ]
                                    ),
                                    html.Hr(),
                                    # ── 3. Water Deficit Analysis ─────
                                    html.H6(
                                        _t(lang, "water_deficit_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "water_deficit_intro"),
                                        className="text-muted small mb-2",
                                    ),
                                    dbc.Alert(
                                        [
                                            html.I(className="bi bi-calculator me-2"),
                                            html.Code(
                                                _t(lang, "water_deficit_formula"),
                                                className="fs-6",
                                            ),
                                        ],
                                        color="light",
                                        className="border mb-2",
                                    ),
                                    html.Ul(
                                        [
                                            html.Li(
                                                [
                                                    html.I(
                                                        className="bi bi-arrow-down-circle text-danger me-1"
                                                    ),
                                                    _t(lang, "water_deficit_negative"),
                                                ]
                                            ),
                                            html.Li(
                                                [
                                                    html.I(
                                                        className="bi bi-arrow-up-circle text-success me-1"
                                                    ),
                                                    _t(lang, "water_deficit_positive"),
                                                ]
                                            ),
                                        ],
                                        className="small mb-2",
                                    ),
                                    html.P(
                                        _t(lang, "water_deficit_metrics_title"),
                                        className="small fw-bold mb-1",
                                    ),
                                    html.Ul(
                                        [
                                            html.Li(_t(lang, f"water_deficit_metric{i}"))
                                            for i in range(1, 6)
                                        ],
                                        className="small mb-0",
                                    ),
                                    html.Hr(),
                                    # ── 4. ETo Comparison ────────────
                                    html.H6(
                                        _t(lang, "eto_comparison_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    dbc.Alert(
                                        [
                                            html.I(className="bi bi-arrow-left-right me-2"),
                                            _t(lang, "eto_comparison_desc"),
                                        ],
                                        color="info",
                                        className="small",
                                    ),
                                    html.Hr(),
                                    # ── 5. Interactive Charts ─────────
                                    html.H6(
                                        _t(lang, "charts_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "charts_desc"),
                                        className="text-muted small mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                _icon_card(
                                                    "bi bi-graph-up",
                                                    "text-primary",
                                                    "chart_eto_temp",
                                                    "chart_eto_temp_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _icon_card(
                                                    "bi bi-sun",
                                                    "text-warning",
                                                    "chart_eto_rad",
                                                    "chart_eto_rad_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _icon_card(
                                                    "bi bi-droplet",
                                                    "text-info",
                                                    "chart_multi",
                                                    "chart_multi_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _icon_card(
                                                    "bi bi-grid-3x3",
                                                    "text-danger",
                                                    "chart_heatmap",
                                                    "chart_heatmap_desc",
                                                    badge="≥30d",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                        ]
                                    ),
                                    html.Hr(),
                                    # ── 6. Download Options ──────────
                                    html.H6(
                                        _t(lang, "downloads_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "downloads_intro"),
                                        className="text-muted small mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                _download_card(
                                                    "bi bi-table",
                                                    "success",
                                                    "downloads_per_table_title",
                                                    "downloads_per_table_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _download_card(
                                                    "bi bi-image",
                                                    "primary",
                                                    "downloads_per_chart_title",
                                                    "downloads_per_chart_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _download_card(
                                                    "bi bi-download",
                                                    "success",
                                                    "downloads_global_title",
                                                    "downloads_global_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                            dbc.Col(
                                                _download_card(
                                                    "bi bi-envelope",
                                                    "info",
                                                    "downloads_email_title",
                                                    "downloads_email_desc",
                                                ),
                                                md=3,
                                                className="mb-2",
                                            ),
                                        ]
                                    ),
                                    html.Hr(),
                                    # ── 7. USA NWS Station Card ──────
                                    html.H6(
                                        _t(lang, "usa_results_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    html.P(
                                        _t(lang, "usa_results_desc"),
                                        className="text-muted small mb-2",
                                    ),
                                    html.Ul(
                                        [
                                            html.Li(_t(lang, f"usa_results_item{i}"))
                                            for i in range(1, 6)
                                        ],
                                        className="small mb-0",
                                    ),
                                    html.Hr(),
                                    # ── 8. Ocean Detection ───────────
                                    html.H6(
                                        _t(lang, "ocean_detection_title"),
                                        className="mt-3 mb-2 text-primary",
                                    ),
                                    dbc.Alert(
                                        [
                                            html.I(className="bi bi-exclamation-triangle me-2"),
                                            _t(lang, "ocean_detection_desc"),
                                        ],
                                        color="warning",
                                        className="small",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_variables_section(lang):
    """Explains each climate variable used in ETo calculation."""
    _var_keys = [
        ("T2M", "var_t2m_name", "°C", "var_t2m_desc"),
        ("T2M_MAX", "var_tmax_name", "°C", "var_tmax_desc"),
        ("T2M_MIN", "var_tmin_name", "°C", "var_tmin_desc"),
        ("RH2M", "var_rh_name", "%", "var_rh_desc"),
        ("WS2M", "var_ws_name", "m/s", "var_ws_desc"),
        ("ALLSKY_SFC_SW_DWN", "var_rad_name", "MJ/m²/day", "var_rad_desc"),
        ("PRECTOTCORR", "var_precip_name", "mm/day", "var_precip_desc"),
        ("ETo", "var_eto_name", "mm/day", "var_eto_desc"),
    ]

    rows = []
    for symbol, name_key, unit, desc_key in _var_keys:
        rows.append(
            html.Tr(
                [
                    html.Td(
                        html.Code(symbol),
                        className="fw-bold",
                    ),
                    html.Td(_t(lang, name_key)),
                    html.Td(
                        dbc.Badge(
                            unit,
                            color="light",
                            text_color="dark",
                        )
                    ),
                    html.Td(
                        html.Small(
                            _t(lang, desc_key),
                            className="text-muted",
                        )
                    ),
                ]
            )
        )

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "variables_title"),
                        id="variables",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.P(
                                        _t(lang, "variables_intro"),
                                        className="text-muted mb-3",
                                    ),
                                    dbc.Table(
                                        [
                                            html.Thead(
                                                html.Tr(
                                                    [
                                                        html.Th(_t(lang, "var_th_symbol")),
                                                        html.Th(_t(lang, "var_th_name")),
                                                        html.Th(_t(lang, "var_th_unit")),
                                                        html.Th(_t(lang, "var_th_desc")),
                                                    ]
                                                )
                                            ),
                                            html.Tbody(rows),
                                        ],
                                        bordered=True,
                                        hover=True,
                                        responsive=True,
                                        size="sm",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_data_sources_section(lang):
    """Data sources — updated with all 6 real sources."""
    sources = [
        {
            "icon": "bi-cloud-sun",
            "name": "Open-Meteo Archive",
            "coverage_key": "src_openmeteo_archive_coverage",
            "resolution_key": "src_openmeteo_archive_resolution",
            "period_key": "src_openmeteo_archive_period",
            "variables_key": "src_openmeteo_archive_vars",
            "license": "CC-BY 4.0",
            "color": "primary",
            "modes": ["Historical", "Recent"],
            "url": "https://open-meteo.com/",
        },
        {
            "icon": "bi-cloud-arrow-down",
            "name": "Open-Meteo Forecast",
            "coverage_key": "src_openmeteo_forecast_coverage",
            "resolution_key": "src_openmeteo_forecast_resolution",
            "period_key": "src_openmeteo_forecast_period",
            "variables_key": "src_openmeteo_forecast_vars",
            "license": "CC-BY 4.0",
            "color": "success",
            "modes": ["Recent (gap fill)", "Forecast"],
            "url": "https://open-meteo.com/",
        },
        {
            "icon": "bi-rocket-takeoff",
            "name": "NASA POWER",
            "coverage_key": "src_nasa_coverage",
            "resolution_key": "src_nasa_resolution",
            "period_key": "src_nasa_period",
            "variables_key": "src_nasa_vars",
            "license": "Public Domain",
            "color": "danger",
            "modes": ["Historical", "Recent"],
            "url": "https://power.larc.nasa.gov/",
        },
        {
            "icon": "bi-snow2",
            "name": "MET Norway (YR.no)",
            "coverage_key": "src_met_coverage",
            "resolution_key": "src_met_resolution",
            "period_key": "src_met_period",
            "variables_key": "src_met_vars",
            "license": "CC-BY 4.0",
            "color": "info",
            "modes": ["Forecast"],
            "url": "https://api.met.no/",
        },
        {
            "icon": "bi-flag",
            "name": "NWS Forecast (NOAA)",
            "coverage": [
                html.Img(
                    src="/assets/images/Flag_of_the_United_States.svg",
                    className="doc-flag-icon-sm",
                ),
            ],
            "coverage_key": "src_nws_forecast_coverage",
            "resolution_key": "src_nws_forecast_resolution",
            "period_key": "src_nws_forecast_period",
            "variables_key": "src_nws_forecast_vars",
            "license": "Public Domain",
            "color": "warning",
            "modes": ["Forecast (USA)"],
            "url": "https://www.weather.gov/",
        },
        {
            "icon": "bi-broadcast-pin",
            "name": "NWS Stations (NOAA)",
            "coverage": [
                html.Img(
                    src="/assets/images/Flag_of_the_United_States.svg",
                    className="doc-flag-icon-sm",
                ),
            ],
            "coverage_key": "src_nws_stations_coverage",
            "resolution_key": "src_nws_stations_resolution",
            "period_key": "src_nws_stations_period",
            "variables_key": "src_nws_stations_vars",
            "license": "Public Domain",
            "color": "dark",
            "modes": ["Forecast (USA)"],
            "url": "https://www.weather.gov/",
        },
    ]

    source_cards = []
    for src in sources:
        modes_badges = [
            dbc.Badge(
                m,
                color="light",
                text_color="dark",
                className="me-1",
            )
            for m in src["modes"]
        ]

        # Build coverage content
        if "coverage" in src:
            coverage_content = src["coverage"] + [_t(lang, src["coverage_key"])]
        else:
            coverage_content = _t(lang, src["coverage_key"])

        source_cards.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className=f"bi {src['icon']} me-2 doc-icon-md",
                                        ),
                                        html.Strong(src["name"]),
                                    ],
                                    className="mb-2",
                                ),
                                html.P(
                                    html.Small(
                                        coverage_content,
                                        className="text-muted",
                                    ),
                                    className="mb-1",
                                ),
                                html.P(
                                    [
                                        html.I(className="bi bi-grid me-1"),
                                        html.Small(_t(lang, src["resolution_key"])),
                                    ],
                                    className="mb-1",
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-calendar me-1"
                                        ),
                                        html.Small(_t(lang, src["period_key"])),
                                    ],
                                    className="mb-1",
                                ),
                                html.P(
                                    [
                                        html.I(
                                            className="bi bi-thermometer-half me-1"
                                        ),
                                        html.Small(_t(lang, src["variables_key"])),
                                    ],
                                    className="mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Small(
                                            _t(lang, "sources_label_modes"),
                                            className="text-muted me-1",
                                        ),
                                        *modes_badges,
                                    ],
                                    className="mb-2",
                                ),
                                html.A(
                                    [
                                        html.I(
                                            className="bi bi-box-arrow-up-right me-1"
                                        ),
                                        _t(lang, "sources_official_website"),
                                    ],
                                    href=src["url"],
                                    target="_blank",
                                    className="btn btn-outline-secondary btn-sm",
                                    rel="noopener noreferrer",
                                ),
                            ],
                            className="p-3",
                        )
                    ],
                    className=f"h-100 border-start border-{src['color']} border-3",
                ),
                md=4,
                className="mb-3",
            )
        )

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "sources_title"),
                        id="fontes-dados",
                        className="mb-4 doc-section-title",
                    ),
                    html.P(
                        _t(lang, "sources_intro"),
                        className="text-muted mb-3",
                    ),
                    dbc.Row(source_cards),
                    # Elevation source
                    dbc.Alert(
                        [
                            html.I(className="bi bi-mountains me-2"),
                            html.Strong(_t(lang, "sources_elevation_title")),
                            _t(lang, "sources_elevation_desc_start"),
                            html.A(
                                "OpenTopoData",
                                href="https://www.opentopodata.org/",
                                target="_blank",
                                className="alert-link",
                            ),
                            _t(lang, "sources_elevation_desc_end"),
                        ],
                        color="light",
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4",
    )


def _create_features_section(lang):
    """Automatic features of the system."""
    features = [
        ("bi-geo-alt-fill", "feat_elevation_title", "feat_elevation_desc", "danger"),
        ("bi-clock", "feat_timezone_title", "feat_timezone_desc", "primary"),
        ("bi-shuffle", "feat_fusion_title", "feat_fusion_desc", "success"),
        ("bi-activity", "feat_progress_title", "feat_progress_desc", "info"),
        ("bi-water", "feat_ocean_title", "feat_ocean_desc", "warning"),
        ("bi-wind", "feat_wind_title", "feat_wind_desc", "secondary"),
        ("bi-shield-check", "feat_preprocess_title", "feat_preprocess_desc", "dark"),
        ("bi-lightning-charge", "feat_cache_title", "feat_cache_desc", "primary"),
        ("bi-flag", "feat_usa_title", "feat_usa_desc", "danger"),
    ]

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "features_title"),
                        id="funcionalidades",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Row(
                        [
                            _feature_card(
                                icon,
                                _t(lang, title_key),
                                _t(lang, desc_key),
                                color,
                            )
                            for icon, title_key, desc_key, color in features
                        ]
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4",
    )


def _feature_card(icon, title, description, color):
    """Individual feature card."""
    return dbc.Col(
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.I(
                            className=f"bi {icon} text-{color} doc-emoji-icon-lg",
                        ),
                        html.H6(title, className="mt-2 mb-1"),
                        html.Small(description, className="text-muted"),
                    ],
                    className="text-center p-3",
                )
            ],
            className="h-100 shadow-sm",
        ),
        md=4,
        className="mb-3",
    )


def _create_usage_limits_section(lang):
    """Usage limits information section."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "limits_title"),
                        id="usage-limits",
                        className="mb-4 doc-section-title",
                    ),
                    html.P(
                        _t(lang, "limits_intro"),
                        className="text-muted mb-4",
                    ),
                    # Per-user limits card
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(
                                        className="bi bi-person-badge me-2"
                                    ),
                                    html.Strong(
                                        _t(lang, "limits_per_user_title")
                                    ),
                                ],
                                className="bg-primary text-white",
                            ),
                            dbc.CardBody(
                                [
                                    html.P(
                                        _t(lang, "limits_per_user_desc"),
                                        className="text-muted small mb-3",
                                    ),
                                    dbc.Table(
                                        [
                                            html.Thead(
                                                html.Tr(
                                                    [
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_mode",
                                                            )
                                                        ),
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_limit",
                                                            ),
                                                            className="text-center",
                                                        ),
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_details",
                                                            )
                                                        ),
                                                    ]
                                                )
                                            ),
                                            html.Tbody(
                                                [
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-calendar-check me-2 text-success"
                                                                    ),
                                                                    _t(
                                                                        lang,
                                                                        "limits_dashboard_mode",
                                                                    ),
                                                                ]
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    _t(
                                                                        lang,
                                                                        "limits_dashboard_limit",
                                                                    ),
                                                                    color="success",
                                                                    pill=True,
                                                                ),
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_dashboard_detail",
                                                                ),
                                                                className="small text-muted",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-clock-history me-2 text-info"
                                                                    ),
                                                                    _t(
                                                                        lang,
                                                                        "limits_historical_mode",
                                                                    ),
                                                                ]
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    _t(
                                                                        lang,
                                                                        "limits_historical_limit",
                                                                    ),
                                                                    color="info",
                                                                    pill=True,
                                                                ),
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_historical_detail",
                                                                ),
                                                                className="small text-muted",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-globe me-2 text-warning"
                                                                    ),
                                                                    html.Strong(
                                                                        _t(
                                                                            lang,
                                                                            "limits_global_mode",
                                                                        )
                                                                    ),
                                                                ]
                                                            ),
                                                            html.Td(
                                                                dbc.Badge(
                                                                    _t(
                                                                        lang,
                                                                        "limits_global_limit",
                                                                    ),
                                                                    color="warning",
                                                                    text_color="dark",
                                                                    pill=True,
                                                                ),
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_global_detail",
                                                                ),
                                                                className="small text-muted",
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                        ],
                                        bordered=True,
                                        hover=True,
                                        responsive=True,
                                        className="mb-0",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4 shadow-sm",
                    ),
                    # External API quotas card
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.I(
                                        className="bi bi-cloud-download me-2"
                                    ),
                                    html.Strong(
                                        _t(lang, "limits_api_title")
                                    ),
                                ],
                                className="bg-secondary text-white",
                            ),
                            dbc.CardBody(
                                [
                                    html.P(
                                        _t(lang, "limits_api_desc"),
                                        className="text-muted small mb-3",
                                    ),
                                    dbc.Table(
                                        [
                                            html.Thead(
                                                html.Tr(
                                                    [
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_api_name",
                                                            )
                                                        ),
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_api_daily",
                                                            ),
                                                            className="text-center",
                                                        ),
                                                        html.Th(
                                                            _t(
                                                                lang,
                                                                "limits_api_usage",
                                                            )
                                                        ),
                                                    ]
                                                )
                                            ),
                                            html.Tbody(
                                                [
                                                    html.Tr(
                                                        [
                                                            html.Td("NASA POWER"),
                                                            html.Td(
                                                                "1,000",
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_nasa_usage",
                                                                ),
                                                                className="small",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                "Open-Meteo Archive"
                                                            ),
                                                            html.Td(
                                                                "10,000",
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_openmeteo_archive_usage",
                                                                ),
                                                                className="small",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                "Open-Meteo Forecast"
                                                            ),
                                                            html.Td(
                                                                "10,000",
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_openmeteo_forecast_usage",
                                                                ),
                                                                className="small",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td(
                                                                "OpenTopoData"
                                                            ),
                                                            html.Td(
                                                                "1,000",
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_opentopo_usage",
                                                                ),
                                                                className="small",
                                                            ),
                                                        ]
                                                    ),
                                                    html.Tr(
                                                        [
                                                            html.Td("Resend"),
                                                            html.Td(
                                                                "100",
                                                                className="text-center",
                                                            ),
                                                            html.Td(
                                                                _t(
                                                                    lang,
                                                                    "limits_resend_usage",
                                                                ),
                                                                className="small",
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                        ],
                                        bordered=True,
                                        hover=True,
                                        responsive=True,
                                        size="sm",
                                        className="mb-0",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4 shadow-sm",
                    ),
                    # What happens when limit reached
                    dbc.Alert(
                        [
                            html.I(
                                className="bi bi-info-circle-fill me-2"
                            ),
                            html.Strong(
                                _t(lang, "limits_exceeded_title")
                            ),
                            " ",
                            _t(lang, "limits_exceeded_desc"),
                        ],
                        color="warning",
                        className="mb-3",
                    ),
                    # Tip about cache
                    dbc.Alert(
                        [
                            html.I(
                                className="bi bi-lightbulb-fill me-2"
                            ),
                            html.Strong(
                                _t(lang, "limits_tip_title")
                            ),
                            _t(lang, "limits_tip_desc"),
                        ],
                        color="success",
                        className="mb-0",
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4",
    )


def _create_faq_section(lang):
    """FAQ / Troubleshooting section."""
    faq_keys = [
        ("faq_q1", "faq_a1"),
        ("faq_q2", "faq_a2"),
        ("faq_q3", "faq_a3"),
        ("faq_q4", "faq_a4"),
        ("faq_q5", "faq_a5"),
        ("faq_q6", "faq_a6"),
        ("faq_q7", "faq_a7"),
    ]

    accordion_items = []
    for i, (q_key, a_key) in enumerate(faq_keys):
        accordion_items.append(
            dbc.AccordionItem(
                html.P(_t(lang, a_key), className="mb-0"),
                title=_t(lang, q_key),
                item_id=f"faq-{i}",
            )
        )

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "faq_title"),
                        id="faq",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Accordion(
                        accordion_items,
                        start_collapsed=True,
                        className="mb-4",
                    ),
                ],
                width=12,
            )
        ]
    )


def _create_license_section(lang):
    """Software license."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H2(
                        _t(lang, "license_title"),
                        id="licenca",
                        className="mb-4 doc-section-title",
                    ),
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5(
                                        _t(lang, "license_name"),
                                        className="mb-4",
                                    ),
                                    # 3 columns: Permissions, Limitations, Conditions
                                    dbc.Row(
                                        [
                                            # Permissions
                                            dbc.Col(
                                                [
                                                    html.H6(
                                                        _t(lang, "license_permissions"),
                                                        className="mb-3 text-success",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-check-circle-fill text-success me-2"
                                                                    ),
                                                                    _t(lang, "license_perm_commercial"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-check-circle-fill text-success me-2"
                                                                    ),
                                                                    _t(lang, "license_perm_modification"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-check-circle-fill text-success me-2"
                                                                    ),
                                                                    _t(lang, "license_perm_distribution"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-check-circle-fill text-success me-2"
                                                                    ),
                                                                    _t(lang, "license_perm_patent"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-check-circle-fill text-success me-2"
                                                                    ),
                                                                    _t(lang, "license_perm_private"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                md=4,
                                                className="mb-3",
                                            ),
                                            # Limitations
                                            dbc.Col(
                                                [
                                                    html.H6(
                                                        _t(lang, "license_limitations"),
                                                        className="mb-3 text-danger",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-x-circle-fill text-danger me-2"
                                                                    ),
                                                                    _t(lang, "license_lim_liability"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-x-circle-fill text-danger me-2"
                                                                    ),
                                                                    _t(lang, "license_lim_warranty"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                md=4,
                                                className="mb-3",
                                            ),
                                            # Conditions
                                            dbc.Col(
                                                [
                                                    html.H6(
                                                        _t(lang, "license_conditions"),
                                                        className="mb-3 text-primary",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-info-circle-fill text-primary me-2"
                                                                    ),
                                                                    _t(lang, "license_cond_notice"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-info-circle-fill text-primary me-2"
                                                                    ),
                                                                    _t(lang, "license_cond_changes"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-info-circle-fill text-primary me-2"
                                                                    ),
                                                                    _t(lang, "license_cond_disclose"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-info-circle-fill text-primary me-2"
                                                                    ),
                                                                    _t(lang, "license_cond_network"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-info-circle-fill text-primary me-2"
                                                                    ),
                                                                    _t(lang, "license_cond_same"),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                md=4,
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                    html.Hr(className="my-3"),
                                    html.P(
                                        [
                                            _t(lang, "license_full_text"),
                                            html.A(
                                                _t(lang, "license_repo"),
                                                href="https://github.com/evaonlineplatform/EVAONLINE/blob/main/LICENSE",
                                                target="_blank",
                                                className="text-primary",
                                            ),
                                            ".",
                                        ],
                                        className="text-muted small mb-0",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4 shadow-sm",
                    ),
                ],
                width=12,
            )
        ]
    )


# =============================================================================
# MAIN LAYOUT
# =============================================================================


def create_documentation_layout(lang="en"):
    """Cria o layout da página de documentação com suporte a idioma."""
    return html.Div(
        [
            dbc.Container(
                [
                    # Quick Nav
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.A(
                                                [
                                                    html.Span(
                                                        "1",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-rocket-takeoff me-1"
                                                    ),
                                                    _t(lang, "nav_quick_start"),
                                                ],
                                                href="#quick-start",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "2",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-map me-1"
                                                    ),
                                                    _t(lang, "nav_map"),
                                                ],
                                                href="#interactive-map",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "3",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-sliders me-1"
                                                    ),
                                                    _t(lang, "nav_modes"),
                                                ],
                                                href="#modos",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "4",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-geo-alt me-1"
                                                    ),
                                                    _t(lang, "nav_usa"),
                                                ],
                                                href="#usa-stations",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "5",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-graph-up me-1"
                                                    ),
                                                    _t(lang, "nav_results"),
                                                ],
                                                href="#resultados",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "6",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-thermometer-half me-1"
                                                    ),
                                                    _t(lang, "nav_variables"),
                                                ],
                                                href="#variables",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "7",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-cloud-download me-1"
                                                    ),
                                                    _t(lang, "nav_sources"),
                                                ],
                                                href="#fontes-dados",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "8",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-lightning me-1"
                                                    ),
                                                    _t(lang, "nav_features"),
                                                ],
                                                href="#funcionalidades",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "9",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-shield-exclamation me-1"
                                                    ),
                                                    _t(lang, "nav_limits"),
                                                ],
                                                href="#usage-limits",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "10",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-question-circle me-1"
                                                    ),
                                                    _t(lang, "nav_faq"),
                                                ],
                                                href="#faq",
                                                className="doc-nav-link",
                                            ),
                                            html.A(
                                                [
                                                    html.Span(
                                                        "11",
                                                        className="doc-nav-number",
                                                    ),
                                                    html.I(
                                                        className="bi bi-file-earmark-text me-1"
                                                    ),
                                                    _t(lang, "nav_license"),
                                                ],
                                                href="#licenca",
                                                className="doc-nav-link",
                                            ),
                                        ],
                                        className="doc-nav-container",
                                    )
                                ],
                                className="py-2 px-3",
                            )
                        ],
                        className="mb-4 shadow-sm doc-nav-card",
                    ),
                    # All sections
                    _create_quick_start_section(lang),
                    _create_interactive_map_section(lang),
                    _create_operation_modes_section(lang),
                    _create_usa_stations_section(lang),
                    _create_results_section(lang),
                    _create_variables_section(lang),
                    _create_data_sources_section(lang),
                    _create_features_section(lang),
                    _create_usage_limits_section(lang),
                    _create_faq_section(lang),
                    _create_license_section(lang),
                ],
                fluid=False,
                className="py-4",
            )
        ],
        className="doc-page-container",
    )
