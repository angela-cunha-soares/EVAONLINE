# filepath: frontend/pages/about.py
"""
Página About do EVAonline — Informações institucionais e científicas.
Inclui: descrição, metodologia, validação, fontes de dados, equipe, parceiros e licença.

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
    """Wrapper para tradução com prefixo 'about' automático."""
    return t(lang, "about", *keys, default=default)


# =============================================================================
# DADOS ESTÁTICOS (autores, parceiros)
# =============================================================================
_DEVELOPERS = [
    {
        "name": "Ângela Silviane Moura Cunha Soares",
        "short": "Ângela S. M. C. Soares",
        "orcid": "0000-0002-1253-7193",
        "institution": "ESALQ/USP",
        "email": "angelassilviane@gmail.com",
        "role_key": "author_role_angela",
    },
    {
        "name": "Carlos Dias Maciel",
        "short": "Carlos D. Maciel",
        "orcid": "0000-0003-0137-6678",
        "institution": "UNESP",
        "email": "carlos.maciel@unesp.br",
        "role_key": "author_role_carlos",
    },
    {
        "name": "Patricia Angélica Alves Marques",
        "short": "Patricia A. A. Marques",
        "orcid": "0000-0002-6818-4833",
        "institution": "ESALQ/USP",
        "email": "paamarques@usp.br",
        "role_key": "author_role_patricia",
    },
]

_ARTICLE_AUTHORS = [
    {
        "name": "Ângela Silviane Moura Cunha Soares",
        "email": "angelassilviane@gmail.com",
        "affiliation_key": "affiliation_usp",
        "corresponding": True,
    },
    {
        "name": "Vitor Pinto Ribeiro",
        "email": "vitor.p.ribeiro@unesp.br",
        "affiliation_key": "affiliation_unesp",
        "corresponding": False,
    },
    {
        "name": "Sérgio Nascimento Duarte",
        "email": "snduarte@usp.br",
        "affiliation_key": "affiliation_usp",
        "corresponding": False,
    },
    {
        "name": "Álex Júnior Zanchet Bordignon",
        "email": "alex.bordignon@usp.br",
        "affiliation_key": "affiliation_usp",
        "corresponding": False,
    },
    {
        "name": "Carlos Roberto Padovani",
        "email": "carlos.padovani@embrapa.br",
        "affiliation_key": "affiliation_embrapa",
        "corresponding": False,
    },
    {
        "name": "José Antônio Perrella Balestieri",
        "email": "jose.perrella@unesp.br",
        "affiliation_key": "affiliation_unesp",
        "corresponding": False,
    },
    {
        "name": "Carlos Dias Maciel",
        "email": "carlos.maciel@unesp.br",
        "affiliation_key": "affiliation_unesp",
        "corresponding": False,
    },
    {
        "name": "Patricia Angélica Alves Marques",
        "email": "paamarques@usp.br",
        "affiliation_key": "affiliation_usp",
        "corresponding": False,
    },
]

_PARTNERS = [
    {"key": "esalq", "name": "ESALQ/USP", "url": "https://www.esalq.usp.br/"},
    {"key": "usp", "name": "USP", "url": "https://www.usp.br/"},
    {"key": "leb", "name": "LEB", "url": "http://www.leb.esalq.usp.br/"},
    {"key": "fapesp", "name": "FAPESP", "url": "https://fapesp.br/"},
    {"key": "c4ai", "name": "C4AI", "url": "https://c4ai.inova.usp.br/"},
    {"key": "ibm", "name": "IBM", "url": "https://www.ibm.com/br-pt"},
]

_DATA_SOURCES = [
    {
        "name": "NASA POWER",
        "resolution": "0.5° × 0.625° (~55 km)",
        "period_key": "ds_period_nasa",
        "type_key": "ds_type_reanalysis",
    },
    {
        "name": "Open-Meteo Archive",
        "resolution": "0.1° (~10 km)",
        "period_key": "ds_period_openmeteo",
        "type_key": "ds_type_reanalysis",
    },
    {
        "name": "Open-Meteo Forecast",
        "resolution": "0.1° (~10 km)",
        "period_key": "ds_period_forecast",
        "type_key": "ds_type_forecast",
    },
    {
        "name": "Met Norway",
        "resolution": "~1 km",
        "period_key": "ds_period_met",
        "type_key": "ds_type_forecast",
    },
    {
        "name": "NWS USA Forecast",
        "resolution": "Grid/Station",
        "period_key": "ds_period_nws_fc",
        "type_key": "ds_type_forecast_usa",
    },
    {
        "name": "NWS USA Stations",
        "resolution": "Station",
        "period_key": "ds_period_nws_st",
        "type_key": "ds_type_observations",
    },
    {
        "name": "OpenTopoData",
        "resolution": "SRTM 30 m",
        "period_key": "ds_period_topo",
        "type_key": "ds_type_elevation",
    },
]

_VALIDATION_RESULTS = [
    {
        "method": "EVAonline (Kalman)",
        "r2": "0.694",
        "kge": "0.814",
        "nse": "0.676",
        "mae": "0.423",
        "rmse": "0.566",
        "pbias": "+0.71",
        "highlight": True,
    },
    {
        "method": "Open-Meteo (ERA5-Land)",
        "r2": "0.649",
        "kge": "0.584",
        "nse": "0.216",
        "mae": "0.690",
        "rmse": "0.860",
        "pbias": "+8.27",
        "highlight": False,
    },
    {
        "method": "NASA POWER (FAO-56)",
        "r2": "0.740",
        "kge": "0.411",
        "nse": "-0.363",
        "mae": "0.845",
        "rmse": "1.117",
        "pbias": "+15.78",
        "highlight": False,
    },
    {
        "method": "Open-Meteo (FAO-56)",
        "r2": "0.636",
        "kge": "0.432",
        "nse": "-0.547",
        "mae": "0.859",
        "rmse": "1.097",
        "pbias": "+13.02",
        "highlight": False,
    },
]


# =============================================================================
# SEÇÃO 1: HERO — O que é o EVAonline
# =============================================================================
def _create_hero_section(lang="en"):
    """Seção hero com descrição do projeto."""
    return dbc.Row(
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H2(
                                            "EVAonline",
                                            className="mb-1 fw-bold text-primary",
                                        ),
                                        html.P(
                                            _t(
                                                lang,
                                                "hero_tagline",
                                                default="Web-based global reference EVApotranspiration estimate",
                                            ),
                                            className="text-muted mb-0 fst-italic",
                                        ),
                                    ]
                                ),
                            ],
                            className="d-flex align-items-center mb-4",
                        ),
                        html.P(
                            _t(
                                lang,
                                "hero_description",
                                default=(
                                    "EVAonline is an open-source, no-installation web platform for daily "
                                    "reference evapotranspiration (ET\u2080) estimation worldwide. It integrates "
                                    "six public reanalysis and forecast APIs (NASA POWER, Open-Meteo, NWS, "
                                    "MET Norway, and others) through a hexagonal architecture and a two-stage "
                                    "fusion strategy: physically informed weighted averaging followed by an "
                                    "adaptive Kalman filter constrained by 30-year regional climatology. "
                                    "Validated over 30 years (1991\u20132020) against the BR-DWGD benchmark at "
                                    "17 Brazilian cities (16 in the MATOPIBA region + Piracicaba/SP), it achieved "
                                    "KGE = 0.814 and MAE = 0.423 mm day\u207b\u00b9 \u2014 reducing error by "
                                    "\u224850% and bias by 95.5% compared to any individual source."
                                ),
                            ),
                            className="lead mb-3",
                        ),
                        # Article title
                        html.Div(
                            [
                                html.I(className="bi bi-journal-text me-2"),
                                html.Strong(
                                    _t(
                                        lang,
                                        "article_label",
                                        default="Article:",
                                    )
                                ),
                                html.Span(
                                    " EVAonline: Open-source web platform for global reference "
                                    "evapotranspiration via adaptive reanalysis data fusion",
                                    className="fst-italic",
                                ),
                            ],
                            className="text-muted small mb-3",
                        ),
                        html.Div(
                            [
                                dbc.Badge(
                                    "FAO-56 Penman-Monteith",
                                    color="primary",
                                    className="me-2 mb-1",
                                    pill=True,
                                ),
                                dbc.Badge(
                                    _t(lang, "badge_kalman", default="Adaptive Kalman Filter"),
                                    color="success",
                                    className="me-2 mb-1",
                                    pill=True,
                                ),
                                dbc.Badge(
                                    _t(lang, "badge_sources", default="7 Climate Sources"),
                                    color="info",
                                    className="me-2 mb-1",
                                    pill=True,
                                ),
                                dbc.Badge(
                                    _t(lang, "badge_global", default="Global Coverage"),
                                    color="warning",
                                    className="me-2 mb-1",
                                    pill=True,
                                ),
                                dbc.Badge(
                                    "Open Source (AGPL-3.0)",
                                    color="secondary",
                                    className="me-2 mb-1",
                                    pill=True,
                                ),
                            ]
                        ),
                    ]
                ),
                className="shadow-sm border-start border-primary border-4",
            ),
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 2: METODOLOGIA CIENTÍFICA
# =============================================================================
def _create_methodology_section(lang="en"):
    """Metodologia FAO-56 PM + Kalman fusion."""
    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-journal-bookmark-fill me-2 text-primary"),
                        _t(lang, "methodology_title", default="Scientific Methodology"),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        # FAO-56 PM
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="bi bi-calculator me-2"),
                                                "FAO-56 Penman-Monteith",
                                            ],
                                            className="card-title text-primary",
                                        ),
                                        html.P(
                                            _t(
                                                lang,
                                                "method_fao56_desc",
                                                default=(
                                                    "The internationally recognized standard method "
                                                    "for estimating reference evapotranspiration (ET₀), "
                                                    "recommended by the Food and Agriculture Organization "
                                                    "of the United Nations (FAO). Uses temperature, humidity, "
                                                    "wind speed, and solar radiation as inputs."
                                                ),
                                            ),
                                            className="card-text",
                                        ),
                                        html.Div(
                                            [
                                                html.Small(
                                                    [
                                                        html.I(className="bi bi-book me-1"),
                                                        "Allen et al. (1998) — FAO Irrigation and Drainage Paper 56",
                                                    ],
                                                    className="text-muted",
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                                className="h-100 shadow-sm",
                            ),
                            md=6,
                            className="mb-3",
                        ),
                        # Kalman Fusion
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="bi bi-diagram-3 me-2"),
                                                _t(
                                                    lang,
                                                    "method_kalman_title",
                                                    default="Adaptive Kalman Fusion",
                                                ),
                                            ],
                                            className="card-title text-success",
                                        ),
                                        html.P(
                                            _t(
                                                lang,
                                                "method_kalman_desc",
                                                default=(
                                                    "An ensemble approach that combines multiple climate "
                                                    "data sources using adaptive Kalman filtering. The system "
                                                    "learns from 1991–2020 climatological normals to dynamically "
                                                    "adjust weights, minimizing bias and improving accuracy "
                                                    "compared to any individual source."
                                                ),
                                            ),
                                            className="card-text",
                                        ),
                                        html.Div(
                                            [
                                                html.Small(
                                                    [
                                                        html.I(className="bi bi-check-circle me-1 text-success"),
                                                        _t(
                                                            lang,
                                                            "method_kalman_highlight",
                                                            default=(
                                                                "38–51% MAE reduction and 91–95% bias reduction "
                                                                "vs individual sources"
                                                            ),
                                                        ),
                                                    ],
                                                    className="text-muted",
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                                className="h-100 shadow-sm",
                            ),
                            md=6,
                            className="mb-3",
                        ),
                    ]
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 3: RESULTADOS DE VALIDAÇÃO
# =============================================================================
def _create_validation_section(lang="en"):
    """Tabela comparativa de métricas de validação."""
    header = html.Thead(
        html.Tr(
            [
                html.Th(_t(lang, "val_method", default="Method")),
                html.Th("R²"),
                html.Th("KGE"),
                html.Th("NSE"),
                html.Th("MAE (mm/d)"),
                html.Th("RMSE (mm/d)"),
                html.Th("PBIAS (%)"),
            ]
        )
    )

    rows = []
    for r in _VALIDATION_RESULTS:
        cls = "table-success fw-bold" if r["highlight"] else ""
        rows.append(
            html.Tr(
                [
                    html.Td(r["method"]),
                    html.Td(r["r2"]),
                    html.Td(r["kge"]),
                    html.Td(r["nse"]),
                    html.Td(r["mae"]),
                    html.Td(r["rmse"]),
                    html.Td(r["pbias"]),
                ],
                className=cls,
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-graph-up me-2 text-success"),
                        _t(lang, "validation_title", default="Validation Results"),
                    ],
                    className="mb-3",
                ),
                html.P(
                    _t(
                        lang,
                        "validation_desc",
                        default=(
                            "Validated against Xavier et al. BR-DWGD reference dataset "
                            "(3,625+ weather stations, 0.1° resolution). Study: 17 Brazilian cities "
                            "(16 in MATOPIBA + Piracicaba/SP), 30 years (1991–2020), 186,287 daily observations."
                        ),
                    ),
                    className="text-muted mb-3",
                ),
                dbc.Table(
                    [header, html.Tbody(rows)],
                    bordered=True,
                    hover=True,
                    responsive=True,
                    striped=True,
                    size="sm",
                    className="mb-3",
                ),
                # Destaques
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            "0.814",
                                            className="text-success fw-bold mb-1",
                                        ),
                                        html.Small(
                                            "KGE",
                                            className="text-muted",
                                        ),
                                    ],
                                    className="text-center py-2",
                                ),
                                className="shadow-sm",
                            ),
                            xs=6,
                            md=3,
                            className="mb-2",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            "0.42 mm/d",
                                            className="text-primary fw-bold mb-1",
                                        ),
                                        html.Small(
                                            "MAE",
                                            className="text-muted",
                                        ),
                                    ],
                                    className="text-center py-2",
                                ),
                                className="shadow-sm",
                            ),
                            xs=6,
                            md=3,
                            className="mb-2",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            "0.71%",
                                            className="text-info fw-bold mb-1",
                                        ),
                                        html.Small(
                                            "PBIAS",
                                            className="text-muted",
                                        ),
                                    ],
                                    className="text-center py-2",
                                ),
                                className="shadow-sm",
                            ),
                            xs=6,
                            md=3,
                            className="mb-2",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            "186,287",
                                            className="text-warning fw-bold mb-1",
                                        ),
                                        html.Small(
                                            _t(lang, "val_observations", default="observations"),
                                            className="text-muted",
                                        ),
                                    ],
                                    className="text-center py-2",
                                ),
                                className="shadow-sm",
                            ),
                            xs=6,
                            md=3,
                            className="mb-2",
                        ),
                    ],
                ),
                html.Div(
                    [
        html.Small(
                            [
                                html.I(className="bi bi-info-circle me-1"),
                                _t(
                                    lang,
                                    "val_reference",
                                    default=(
                                        "Xavier, A. C., Scanlon, B. R., King, C. W., & Alves, A. I. (2022). "
                                        "New improved Brazilian daily weather gridded data (1961\u20132020). "
                                        "International Journal of Climatology, 42(16), 8390\u20138404. "
                                        "https://doi.org/10.1002/joc.7731"
                                    ),
                                ),
                                html.Span(" | "),
                                html.A(
                                    [
                                        html.I(className="bi bi-box-arrow-up-right me-1"),
                                        _t(lang, "val_dataset_link", default="Access BR-DWGD Dataset"),
                                    ],
                                    href="https://sites.google.com/site/alexandrecandidoxavierufes/brazilian-daily-weather-gridded-data",
                                    target="_blank",
                                    rel="noopener noreferrer",
                                    className="text-decoration-none",
                                ),
                            ],
                            className="text-muted",
                        ),
                    ],
                    className="mt-2",
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 4: FONTES DE DADOS
# =============================================================================
def _create_data_sources_section(lang="en"):
    """Tabela das 7 fontes de dados (6 climáticas + 1 elevação)."""
    header = html.Thead(
        html.Tr(
            [
                html.Th(_t(lang, "ds_source", default="Source")),
                html.Th(_t(lang, "ds_resolution", default="Resolution")),
                html.Th(_t(lang, "ds_period", default="Period")),
                html.Th(_t(lang, "ds_type", default="Type")),
            ]
        )
    )

    rows = []
    for ds in _DATA_SOURCES:
        rows.append(
            html.Tr(
                [
                    html.Td(html.Strong(ds["name"])),
                    html.Td(ds["resolution"]),
                    html.Td(_t(lang, ds["period_key"], default="—")),
                    html.Td(
                        dbc.Badge(
                            _t(lang, ds["type_key"], default=ds["type_key"]),
                            color=(
                                "primary"
                                if "reanalysis" in ds["type_key"]
                                else "info"
                                if "forecast" in ds["type_key"]
                                else "secondary"
                            ),
                            pill=True,
                        )
                    ),
                ]
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-cloud-download me-2 text-info"),
                        _t(lang, "data_sources_title", default="Climate Data Sources"),
                    ],
                    className="mb-3",
                ),
                html.P(
                    _t(
                        lang,
                        "data_sources_desc",
                        default=(
                            "EVAonline integrates 7 data sources (6 climate + 1 elevation), automatically "
                            "selecting the best combination based on geographic location and data availability."
                        ),
                    ),
                    className="text-muted mb-3",
                ),
                dbc.Table(
                    [header, html.Tbody(rows)],
                    bordered=True,
                    hover=True,
                    responsive=True,
                    striped=True,
                    size="sm",
                ),
                html.Div(
                    [
                        html.Small(
                            [
                                html.I(className="bi bi-info-circle me-1"),
                                _t(
                                    lang,
                                    "ds_ref_openmeteo",
                                    default=(
                                        "Zippenfenig, P. (2023). Open-Meteo.com Weather API "
                                        "[Computer software]. Zenodo. "
                                        "https://doi.org/10.5281/ZENODO.7970649"
                                    ),
                                ),
                            ],
                            className="text-muted",
                        ),
                        html.Br(),
                        html.Small(
                            [
                                html.I(className="bi bi-info-circle me-1"),
                                _t(
                                    lang,
                                    "ds_ref_nasapower",
                                    default=(
                                        "The data was obtained from NASA Langley Research Center\u2019s "
                                        "Prediction Of Worldwide Energy Resources (POWER) project, "
                                        "funded through the NASA Earth Science Division."
                                    ),
                                ),
                            ],
                            className="text-muted",
                        ),
                    ],
                    className="mt-2",
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 5: EQUIPE & AUTORES
# =============================================================================
def _create_team_section(lang="en"):
    """Cards dos desenvolvedores e lista de autores do artigo."""
    author_cards = []
    for author in _DEVELOPERS:
        author_cards.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                html.I(
                                    className="bi bi-person-circle",
                                    style={"fontSize": "3rem", "color": "#6c757d"},
                                ),
                                className="text-center mb-3",
                            ),
                            html.H5(
                                author["name"],
                                className="card-title text-center mb-1",
                            ),
                            html.P(
                                author["institution"],
                                className="text-muted text-center mb-2",
                            ),
                            html.P(
                                _t(lang, author["role_key"], default="Researcher"),
                                className="text-center small mb-3",
                            ),
                            html.Div(
                                [
                                    # ORCID
                                    html.A(
                                        [
                                            html.Img(
                                                src="/assets/images/ORCID_iD.svg",
                                                alt="ORCID",
                                                style={"height": "16px"},
                                                className="me-1",
                                            ),
                                            html.Small(author["orcid"]),
                                        ],
                                        href=f"https://orcid.org/{author['orcid']}",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        className="d-block text-center text-decoration-none mb-1",
                                    ),
                                    # Email
                                    html.Div(
                                        [
                                            html.I(className="bi bi-envelope me-1"),
                                            html.Small(author["email"]),
                                        ],
                                        className="text-center text-muted",
                                    ),
                                ],
                            ),
                        ]
                    ),
                    className="h-100 shadow-sm",
                ),
                md=4,
                className="mb-3",
            )
        )

    # Article authors list
    article_author_rows = []
    for aa in _ARTICLE_AUTHORS:
        name_el = html.Span(
            [
                html.Strong(aa["name"]),
                *([
                    html.Span(" *", className="text-danger", title=_t(lang, "corresponding_author", default="Corresponding author")),
                ] if aa["corresponding"] else []),
            ]
        )
        article_author_rows.append(
            html.Tr(
                [
                    html.Td(name_el),
                    html.Td(
                        html.A(
                            aa["email"],
                            href=f"mailto:{aa['email']}",
                            className="text-decoration-none",
                        ),
                        className="text-muted",
                    ),
                    html.Td(_t(lang, aa["affiliation_key"], default="")),
                ]
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-people-fill me-2 text-primary"),
                        _t(lang, "team_title", default="Team"),
                    ],
                    className="mb-3",
                ),
                # Developers subsection
                html.H5(
                    [
                        html.I(className="bi bi-code-slash me-2"),
                        _t(lang, "developers_title", default="Developers"),
                    ],
                    className="mb-3 text-secondary",
                ),
                dbc.Row(author_cards),
                # Article authors subsection
                html.H5(
                    [
                        html.I(className="bi bi-journal-text me-2"),
                        _t(lang, "article_authors_title", default="Article Authors"),
                    ],
                    className="mb-3 mt-4 text-secondary",
                ),
                dbc.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th(_t(lang, "author_name", default="Name")),
                                    html.Th(_t(lang, "author_email", default="Email")),
                                    html.Th(_t(lang, "author_affiliation", default="Affiliation")),
                                ]
                            )
                        ),
                        html.Tbody(article_author_rows),
                    ],
                    bordered=True,
                    hover=True,
                    responsive=True,
                    striped=True,
                    size="sm",
                    className="mb-2",
                ),
                html.Small(
                    [
                        html.Span("* ", className="text-danger"),
                        _t(lang, "corresponding_author", default="Corresponding author"),
                    ],
                    className="text-muted",
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 6: PARCEIROS & FINANCIAMENTO
# =============================================================================
def _create_partners_section(lang="en"):
    """Grid de logos de parceiros institucionais."""
    logos = []
    for partner in _PARTNERS:
        logos.append(
            html.A(
                html.Img(
                    src=f"/assets/images/logo_{partner['key']}.svg",
                    alt=f"Logo {partner['name']}",
                    style={"height": "70px", "maxWidth": "170px"},
                    className="mx-3 my-2 partner-logo-about",
                ),
                href=partner["url"],
                target="_blank",
                rel="noopener noreferrer",
                title=partner["name"],
            )
        )

    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-building me-2 text-warning"),
                        _t(lang, "partners_title", default="Partners"),
                    ],
                    className="mb-3",
                ),
                dbc.Card(
                    dbc.CardBody(
                        html.Div(
                            logos,
                            className="d-flex justify-content-center flex-wrap align-items-center",
                        ),
                    ),
                    className="shadow-sm",
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# SEÇÃO 7: LICENÇA & REPOSITÓRIO
# =============================================================================
def _create_license_section(lang="en"):
    """Informações de licença e links do repositório."""
    return dbc.Row(
        dbc.Col(
            [
                html.H3(
                    [
                        html.I(className="bi bi-shield-check me-2 text-secondary"),
                        _t(lang, "license_title", default="License & Repository"),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            [
                                                html.I(className="bi bi-file-earmark-text me-2"),
                                                "AGPL-3.0",
                                            ],
                                            className="card-title",
                                        ),
                                        html.P(
                                            _t(
                                                lang,
                                                "license_desc",
                                                default=(
                                                    "GNU Affero General Public License v3.0 — "
                                                    "Free to use, modify and distribute. "
                                                    "Modifications must be shared under the same license."
                                                ),
                                            ),
                                            className="card-text small",
                                        ),
                                        html.A(
                                            [
                                                html.I(className="bi bi-box-arrow-up-right me-1"),
                                                _t(lang, "license_view", default="View License"),
                                            ],
                                            href="https://github.com/angelacunhasoares/EVAONLINE/blob/main/LICENSE",
                                            target="_blank",
                                            rel="noopener noreferrer",
                                            className="btn btn-outline-secondary btn-sm",
                                        ),
                                    ]
                                ),
                                className="h-100 shadow-sm",
                            ),
                            md=6,
                            className="mb-3",
                        ),
                        dbc.Col(
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            [
                                                html.Img(
                                                    src="/assets/images/github.svg",
                                                    alt="GitHub",
                                                    style={"height": "20px"},
                                                    className="me-2",
                                                ),
                                                _t(lang, "repo_title", default="Source Code"),
                                            ],
                                            className="card-title",
                                        ),
                                        html.P(
                                            _t(
                                                lang,
                                                "repo_desc",
                                                default=(
                                                    "Full source code, documentation, and issue tracker. "
                                                    "Contributions are welcome via pull requests."
                                                ),
                                            ),
                                            className="card-text small",
                                        ),
                                        html.A(
                                            [
                                                html.I(className="bi bi-github me-1"),
                                                _t(lang, "repo_view", default="View on GitHub"),
                                            ],
                                            href="https://github.com/angelacunhasoares/EVAONLINE",
                                            target="_blank",
                                            rel="noopener noreferrer",
                                            className="btn btn-outline-dark btn-sm",
                                        ),
                                    ]
                                ),
                                className="h-100 shadow-sm",
                            ),
                            md=6,
                            className="mb-3",
                        ),
                    ]
                ),
            ],
            lg=12,
        ),
        className="mb-4",
    )


# =============================================================================
# LAYOUT PRINCIPAL — Factory function (i18n)
# =============================================================================
def create_about_layout(lang="en"):
    """
    Constrói o layout da página About com tradução dinâmica.

    Args:
        lang: Código do idioma ('en' ou 'pt').

    Returns:
        dbc.Container: Layout completo da página About.
    """
    logger.debug(f"📄 Criando layout About (lang={lang})")

    return dbc.Container(
        [
            # Título da página
            html.H1(
                _t(lang, "page_title", default="About EVAonline"),
                className="text-center my-4 fw-bold",
            ),
            html.P(
                _t(
                    lang,
                    "page_subtitle",
                    default="Open-source tool for reference evapotranspiration estimation",
                ),
                className="text-center text-muted mb-4 lead",
            ),
            html.Hr(className="mb-4"),
            # Seções
            _create_hero_section(lang),
            _create_methodology_section(lang),
            _create_validation_section(lang),
            _create_data_sources_section(lang),
            _create_team_section(lang),
            _create_partners_section(lang),
            _create_license_section(lang),
        ],
        fluid=False,
        className="py-4 about-page",
    )


# Layout estático padrão (fallback para import direto)
about_layout = create_about_layout("en")
