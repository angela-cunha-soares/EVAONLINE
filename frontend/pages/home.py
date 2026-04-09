"""
Pagina HOME unificada do EVAonline.

Layout simples com sidebar + mapa (estilo Iris k-means example).
Estrutura: HOME | DOCUMENTATION | ABOUT | GITHUB

Features:
- Sidebar com configuracoes de calculo (nao usa Offcanvas)
- Mapa mundial interativo ocupando area principal
- Resultados exibidos abaixo do mapa
"""

import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

from ..components.world_map_leaflet import create_world_map

logger = logging.getLogger(__name__)


def create_sidebar_card():
    """
    Cria sidebar profissional com design moderno.
    Estilo clean com gradientes, icones e espacamento otimizado.
    """
    return html.Div(
        [
            # Header com gradiente azul acadêmico
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="bi bi-cloud-sun-fill card-header-icon",
                            ),
                        ],
                        className="me-3",
                    ),
                    html.Div(
                        [
                            html.H5(
                                "ETo Calculator",
                                id="sidebar-title",
                                className="mb-0 fw-bold",
                            ),
                            html.Small(
                                "FAO-56 Penman-Monteith",
                                id="sidebar-subtitle",
                                className="opacity-75",
                            ),
                        ],
                    ),
                ],
                className="d-flex align-items-center p-3 text-white card-header-academic",
            ),
            # Corpo da sidebar
            html.Div(
                [
                    # Seção 0: Localização Selecionada
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-geo-alt-fill me-2 text-danger"
                                    ),
                                    html.Span(
                                        "Selected Location",
                                        id="sidebar-selected-location",
                                        className="fw-semibold text-dark",
                                    ),
                                ],
                                className="mb-2",
                            ),
                            # Card com coordenadas (atualizado dinamicamente)
                            html.Div(
                                id="sidebar-location-display",
                                children=dbc.Alert(
                                    [
                                        html.I(
                                            className="bi bi-hand-index-thumb me-2"
                                        ),
                                        "Click on the map to select a point",
                                    ],
                                    color="secondary",
                                    className="mb-0 small py-2",
                                ),
                            ),
                            # Campos de entrada manual (lat, lon, altitude)
                            html.Div(
                                [
                                    # Toggle para mostrar/ocultar campos
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-pencil-square me-1"
                                            ),
                                            html.Span(
                                                "Manual Input",
                                                id="sidebar-manual-input-text",
                                            ),
                                        ],
                                        id="toggle-manual-coords",
                                        color="link",
                                        size="sm",
                                        className="p-0 mt-2 text-decoration-none",
                                    ),
                                    dbc.Collapse(
                                        html.Div(
                                            [
                                                # Latitude
                                                dbc.InputGroup(
                                                    [
                                                        dbc.InputGroupText(
                                                            "Lat",
                                                            className="bg-white input-group-label input-group-fixed",
                                                        ),
                                                        dbc.Input(
                                                            id="manual-lat",
                                                            type="number",
                                                            placeholder="-22.7235",
                                                            min=-90,
                                                            max=90,
                                                            step=0.0001,
                                                            className="input-text",
                                                        ),
                                                    ],
                                                    size="sm",
                                                    className="mb-1",
                                                ),
                                                # Longitude
                                                dbc.InputGroup(
                                                    [
                                                        dbc.InputGroupText(
                                                            "Lon",
                                                            className="bg-white input-group-label input-group-fixed",
                                                        ),
                                                        dbc.Input(
                                                            id="manual-lon",
                                                            type="number",
                                                            placeholder="-47.6492",
                                                            min=-180,
                                                            max=180,
                                                            step=0.0001,
                                                            className="input-text",
                                                        ),
                                                    ],
                                                    size="sm",
                                                    className="mb-1",
                                                ),
                                                # Altitude
                                                dbc.InputGroup(
                                                    [
                                                        dbc.InputGroupText(
                                                            "Alt",
                                                            className="bg-white input-group-label input-group-fixed",
                                                        ),
                                                        dbc.Input(
                                                            id="manual-alt",
                                                            type="number",
                                                            placeholder="546 (m)",
                                                            min=-500,
                                                            max=9000,
                                                            step=1,
                                                            className="input-text",
                                                        ),
                                                    ],
                                                    size="sm",
                                                    className="mb-1",
                                                ),
                                                # Botão aplicar
                                                dbc.Button(
                                                    [
                                                        html.I(
                                                            className="bi bi-check2-circle me-1"
                                                        ),
                                                        html.Span(
                                                            "Apply",
                                                            id="sidebar-apply-text",
                                                        ),
                                                    ],
                                                    id="apply-manual-coords",
                                                    color="success",
                                                    size="sm",
                                                    className="w-100 mt-1",
                                                    outline=True,
                                                ),
                                                html.Small(
                                                    "Altitude is optional (auto-detected via SRTM)",
                                                    id="sidebar-altitude-help",
                                                    className="text-muted d-block mt-1 help-text",
                                                ),
                                            ],
                                            className="mt-2",
                                        ),
                                        id="collapse-manual-coords",
                                        is_open=False,
                                    ),
                                ],
                            ),
                        ],
                        className="mb-4 pb-3 section-separator",
                    ),
                    # Secao 1: Tipo de Dados
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        className="bi bi-sliders2 me-2 text-primary"
                                    ),
                                    html.Span(
                                        "Data Type",
                                        id="sidebar-data-type",
                                        className="fw-semibold text-dark",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.RadioItems(
                                id="data-type-radio",
                                options=[
                                    {
                                        "label": html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-hourglass-split me-2 text-primary"
                                                ),
                                                html.Span("Historical"),
                                                html.Small(
                                                    " (1990 \u2192 yesterday)",
                                                    className="text-muted ms-1",
                                                ),
                                            ],
                                            className="d-flex align-items-center",
                                        ),
                                        "value": "historical",
                                    },
                                    {
                                        "label": html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-clock-history me-2 text-success"
                                                ),
                                                html.Span("Recent"),
                                                html.Small(
                                                    " (Last 7-30 days)",
                                                    className="text-muted ms-1",
                                                ),
                                            ],
                                            className="d-flex align-items-center",
                                        ),
                                        "value": "recent",
                                    },
                                    {
                                        "label": html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-cloud-sun-fill me-2 forecast-icon",
                                                ),
                                                html.Span("Forecast"),
                                                html.Small(
                                                    " (5 days)",
                                                    className="text-muted ms-1",
                                                ),
                                            ],
                                            className="d-flex align-items-center",
                                        ),
                                        "value": "forecast",
                                    },
                                ],
                                value=None,
                                className="custom-radio-group",
                                inputClassName="me-2",
                                labelClassName="py-2 px-3 rounded-3 mb-2 d-block border",
                                labelCheckedClassName="bg-light border-primary",
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Componentes ocultos para manter compatibilidade
                    html.Div(
                        [
                            dcc.Store(
                                id="climate-source-dropdown", data="auto"
                            ),
                            html.Div(
                                id="source-selection-info",
                                style={"display": "none"},
                            ),
                            html.Div(
                                id="source-description",
                                style={"display": "none"},
                            ),
                        ],
                        style={"display": "none"},
                    ),
                    # Secao 3: Formulario Condicional
                    html.Div(
                        id="conditional-form",
                        className="mb-3",
                    ),
                    # Botao de Calcular - Estilo moderno
                    dbc.Button(
                        [
                            html.I(className="bi bi-calculator-fill me-2"),
                            "CALCULATE ETo",
                        ],
                        id="calculate-eto-btn",
                        color="success",
                        className="w-100 py-2 fw-semibold btn-calculate-eto",
                        n_clicks=0,
                        disabled=True,
                    ),
                    # Feedback areas
                    html.Div(id="validation-alert", className="mt-3"),
                    html.Div(id="operation-mode-indicator", className="mt-2"),
                    html.Div(
                        id="calculation-success-status", className="mt-2"
                    ),
                    html.Div(id="eto-progress-container", className="mt-2"),
                ],
                className="p-3 sidebar-body",
            ),
        ],
        className="card-wrapper",
    )


def create_map_card():
    """Cria card com o mapa mundial - estilo moderno."""
    return html.Div(
        [
            # Header com gradiente azul acadêmico (variação)
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="bi bi-geo-alt-fill card-header-icon",
                            ),
                        ],
                        className="me-3",
                    ),
                    html.Div(
                        [
                            html.H5(
                                "Select Location",
                                id="map-select-title",
                                className="mb-0 fw-bold",
                            ),
                            html.Small(
                                "Click on the map or use geolocation",
                                id="map-select-subtitle",
                                className="opacity-75",
                            ),
                        ],
                    ),
                ],
                className="d-flex align-items-center p-3 text-white card-header-academic-alt",
            ),
            # Corpo do card
            html.Div(
                [
                    # Mapa
                    create_world_map(),
                ],
                className="map-card-body",
            ),
            # Info abaixo do mapa
            html.Div(
                [
                    # Info de Selecao
                    html.Div(
                        id="current-selection-info",
                        className="mt-2",
                    ),
                    # ========================================
                    # INFO CARDS - Abaixo do mapa
                    # ========================================
                    html.Div(
                        id="fusion-info-card",
                        children=None,
                        className="mt-3",
                    ),
                    # ========================================
                    # MATOPIBA REFERENCE
                    # ========================================
                    html.Div(
                        [
                            html.Small(
                                [
                                    html.Strong("MATOPIBA"),
                                    ": Acronym from the initials of the states of ",
                                    html.Strong("Ma"),
                                    "ranhão, ",
                                    html.Strong("To"),
                                    "cantins, ",
                                    html.Strong("Pi"),
                                    "auí and ",
                                    html.Strong("Ba"),
                                    "hia. ",
                                    html.A(
                                        "Learn more (Embrapa)",
                                        id="matopiba-learn-more",
                                        href="https://www.embrapa.br/territorial/busca-de-publicacoes/-/publicacao/1037313/proposta-de-delimitacao-territorial-do-matopiba",
                                        target="_blank",
                                        className="text-primary",
                                    ),
                                ],
                                id="matopiba-reference-text",
                                className="text-muted matopiba-reference",
                            ),
                        ],
                        className="mt-1 px-2",
                    ),
                ],
                className="p-2",
            ),
        ],
        className="card-wrapper",
    )


# =============================================================================
# LAYOUT PRINCIPAL - DESIGN MODERNO
# =============================================================================
home_layout = dbc.Container(
    [
        # Espacamento superior
        html.Div(className="py-0"),
        # Layout Principal: Sidebar (4 cols) + Mapa (8 cols)
        dbc.Row(
            [
                # SIDEBAR (4 colunas)
                dbc.Col(
                    create_sidebar_card(),
                    lg=4,
                    md=5,
                    className="mb-3",
                ),
                # MAPA (8 colunas)
                dbc.Col(
                    create_map_card(),
                    lg=8,
                    md=7,
                    className="mb-3",
                ),
            ],
            align="start",
            className="g-3",  # Gap entre colunas
        ),
        # Linha de Resultados (abaixo do mapa)
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="eto-results-container"),
                    width=12,
                ),
            ],
        ),
        # =================================================================
        # STORES E COMPONENTES OCULTOS
        # =================================================================
        dcc.Store(id="sidebar-state", storage_type="memory", data=True),
        dcc.Store(
            id="selected-location-data", storage_type="memory", data=None
        ),
        dcc.Store(id="current-location", storage_type="memory", data=None),
        dcc.Store(id="map-click-data", storage_type="memory", data=None),
        dcc.Store(id="parsed-coordinates", storage_type="memory", data=None),
        dcc.Store(id="current-task-id", storage_type="memory", data=None),
        dcc.Store(
            id="current-operation-mode", storage_type="memory", data=None
        ),
        dcc.Store(id="eto-results-data", storage_type="memory", data=None),
        dcc.Store(id="manual-elevation", storage_type="memory", data=None),
        dcc.Download(id="download-csv"),
        dcc.Download(id="download-excel"),
        # Per-table download components
        dcc.Download(id="download-table-climate"),
        dcc.Download(id="download-table-stats"),
        dcc.Download(id="download-table-eto-summary"),
        dcc.Download(id="download-table-normality"),
        # Hidden button placeholders for callback registration
        html.Button(id="btn-new-query", style={"display": "none"}),
        html.Button(id="btn-new-query-sidebar", style={"display": "none"}),
        dcc.Interval(
            id="progress-interval",
            interval=2000,
            n_intervals=0,
            disabled=True,
        ),
        # Hidden elements for callback compatibility
        html.Div(
            [
                html.Div(id="location-display"),
                html.Div(id="location-input-container"),
                html.Div(id="coord-validation-feedback"),
                html.Div(id="selected-coords-display"),
                dbc.RadioItems(
                    id="location-mode-radio",
                    value="map",
                ),
                dbc.RadioItems(id="file-format-historical", value="csv"),
                # Botões de download (renderizados dinamicamente nos resultados)
                dbc.Button(id="btn-download-csv", n_clicks=0),
                dbc.Button(id="btn-download-excel", n_clicks=0),
            ],
            style={"display": "none"},
        ),
        # Toast Container
        html.Div(
            id="toast-container",
            className="toast-container-fixed",
        ),
    ],
    fluid=False,
    className="py-1",
)

logger.info("Home page (unified) loaded successfully")
