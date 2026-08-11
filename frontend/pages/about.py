# filepath: frontend/pages/about.py
"""
Página About do EVAonline — Informações institucionais e científicas.
Inclui: descrição do projeto, equipe/autores do artigo e parceiros.
Metodologia, validação, fontes de dados e licença vivem nas páginas
Documentação/Arquitetura e no rodapé — não são replicadas aqui.

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
        "email": "angelasilviane@alumni.usp.br",
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
        "email": "angelasilviane@alumni.usp.br",
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
            # Seções — a página Sobre foca no essencial e não replica
            # conteúdo já presente em Documentação/Arquitetura/rodapé:
            #   • Definição do EVAonline (hero)
            #   • Equipe e autores do artigo
            #   • Parceiros / financiadores
            # Metodologia, Resultados de Validação, Fontes de Dados e Licença
            # foram removidos daqui por já existirem nas páginas próprias.
            _create_hero_section(lang),
            _create_team_section(lang),
            _create_partners_section(lang),
        ],
        fluid=False,
        className="py-4 about-page",
    )


# Layout estático padrão (fallback para import direto)
about_layout = create_about_layout("en")
