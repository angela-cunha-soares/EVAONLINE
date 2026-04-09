"""
Navbar EVAonline - inclui logo, links internos + botão de tradução PT/EN.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    """
    Cria navbar responsiva.
    Returns:
        dbc.Navbar: Navbar completa.
    """
    navbar = dbc.Navbar(
        [
            dbc.Container(
                [
                    # Brand com texto destacado (estilo acadêmico)
                    html.Div(
                        [
                            html.A(
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-droplet-fill me-2 navbar-brand-icon",
                                                ),
                                                html.Span(
                                                    "EVAonline",
                                                    className="navbar-brand-title",
                                                ),
                                            ],
                                            className="navbar-brand-header",
                                        ),
                                        html.Div(
                                            "An open-source web platform for global reference evapotranspiration estimation via multi-source data fusion",
                                            className="navbar-brand-subtitle",
                                        ),
                                    ],
                                    className="navbar-brand-container",
                                ),
                                href="/",
                                className="navbar-brand-link",
                            ),
                        ],
                        className="navbar-brand",
                    ),
                    # Toggle para mobile - botão visível com ícone
                    dbc.Button(
                        html.I(className="bi bi-list"),
                        id="navbar-toggler",
                        className="d-lg-none",
                        color="secondary",
                        outline=True,
                    ),
                    # Links principais + Botão de tradução (direita)
                    dbc.Collapse(
                        dbc.Nav(
                            [
                                # Links internos com estilo acadêmico
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "HOME",
                                        href="/",
                                        id="nav-home",
                                        className="nav-link-academic",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "DOCUMENTATION",
                                        href="/documentation",
                                        id="nav-documentation",
                                        className="nav-link-academic",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "ARCHITECTURE",
                                        href="/architecture",
                                        id="nav-architecture",
                                        className="nav-link-academic",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        "ABOUT",
                                        href="/about",
                                        id="nav-about",
                                        className="nav-link-academic",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(
                                                className="bi bi-github me-2"
                                            ),
                                            "GITHUB",
                                        ],
                                        href="https://github.com/evaonlineplatform/EVAONLINE",
                                        target="_blank",
                                        id="nav-github",
                                        className="nav-link-academic nav-link-github",
                                    )
                                ),
                                # Botão de Tradução (verde acadêmico)
                                dbc.NavItem(
                                    dbc.Button(
                                        html.Span(
                                            id="language-label",
                                            children="PORTUGUÊS",
                                        ),
                                        id="language-toggle",
                                        className="ms-2",
                                    ),
                                    className="d-flex align-items-center",
                                ),
                            ],
                            className="ms-auto align-items-center",
                            navbar=True,
                        ),
                        id="navbar-collapse",
                        navbar=True,
                    ),
                ],
                fluid=False,
            ),
        ],
        color="light",
        className="navbar-expand-lg navbar-academic",
    )

    # Retorna navbar com accent bar no topo
    return html.Div(
        [
            html.Div(className="navbar-accent-bar"),
            navbar,
        ]
    )
