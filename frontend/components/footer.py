"""
Componente de footer (rodapé) para o ETO Calculator - Versão com 4 Colunas.
Colunas: Logo | Desenvolvedores | Parceiros | Links Importantes.
"""

import logging
from datetime import datetime
from functools import lru_cache
from typing import Dict, List

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


class FooterManager:
    """Gerencia dados do footer com cache."""

    def __init__(self):
        self._current_year = datetime.now().year

    @property
    def current_year(self) -> int:
        return self._current_year

    @lru_cache(maxsize=1)
    def get_developer_data(self) -> List[Dict]:
        """Desenvolvedores com emails e ORCID."""
        return [
            {
                "name": "Ângela S. M. C. Soares",
                "email": "angelasilviane@alumni.usp.br",
                "orcid": "0000-0002-1253-7193",
            },
            {
                "name": "Patricia A. A. Marques",
                "email": "paamarques@usp.br",
                "orcid": "0000-0002-6818-4833",
            },
            {
                "name": "Carlos D. Maciel",
                "email": "carlos.maciel@unesp.br",
                "orcid": "0000-0003-0137-6678",
            },
        ]

    @lru_cache(maxsize=1)
    def get_partner_data(self) -> Dict[str, str]:
        """Parceiros com URLs para logos."""
        return {
            "esalq": "https://www.esalq.usp.br/",
            "usp": "https://www.usp.br/",
            "fapesp": "https://fapesp.br/",
            "ibm": "https://www.ibm.com/br-pt",
            "c4ai": "https://c4ai.inova.usp.br/",
            "leb": "http://www.leb.esalq.usp.br/",
        }

    @lru_cache(maxsize=1)
    def get_logo_extensions(self) -> Dict[str, str]:
        """Extensões dos arquivos de logo (padrão: .svg)."""
        return {
            # Todos os logos agora são SVG
            "esalq": ".svg",
            "usp": ".svg",
            "fapesp": ".svg",
            "ibm": ".svg",
            "leb": ".svg",
        }

    def get_logo_path(self, partner: str) -> str:
        """Retorna o caminho completo do logo com a extensão correta."""
        extension = self.get_logo_extensions().get(partner, ".svg")
        return f"/assets/images/logo_{partner}{extension}"

    def get_email_link(self, email: str) -> str:
        """Link direto para Gmail Compose."""
        # Gmail compose URL - abre diretamente no Gmail web
        return f"https://mail.google.com/mail/?view=cm&to={email}"

    @lru_cache(maxsize=1)
    def get_citation_data(self) -> Dict[str, str]:
        """Metadados do artigo, dataset e código para a seção 'Como citar'."""
        return {
            # Referência formatada (autores + ano + título + revista)
            "authors": (
                "Soares, A.S.M.C., Ribeiro, V.P., Duarte, S.N., "
                "Balestieri, J.A.P., Padovani, C.R., Bordignon, Á.J.Z., "
                "Maciel, C.D., & Marques, P.A.A."
            ),
            "year": "2026",
            "title": (
                "EVAonline: An open-source web platform for global "
                "reference evapotranspiration estimation via multi-source "
                "data fusion"
            ),
            "journal": "Environmental Modelling & Software",
            "volume": "204",
            "article_number": "107113",
            # Links
            "doi": "10.1016/j.envsoft.2026.107113",
            "doi_url": "https://doi.org/10.1016/j.envsoft.2026.107113",
            "zenodo_url": "https://zenodo.org/records/21781466",
            "zenodo_doi": "10.5281/zenodo.21781466",
            "github_url": (
                "https://github.com/angela-cunha-soares/EVAONLINE"
            ),
        }

    def get_citation_text(self) -> str:
        """Citação completa em texto puro (para o botão de copiar)."""
        c = self.get_citation_data()
        return (
            f"{c['authors']} ({c['year']}). {c['title']}. "
            f"{c['journal']}, {c['volume']}, {c['article_number']}. "
            f"https://doi.org/{c['doi']}"
        )


# Instância global
footer_manager = FooterManager()


def create_footer(lang: str = "en") -> html.Footer:
    """
    Cria footer profissional com 4 colunas responsivas.
    Args:
        lang: 'pt' ou 'en'.
    Returns:
        html.Footer: Footer columnar profissional.
    """
    logger.debug("🔄 Criando footer profissional com 3 colunas")
    try:
        texts = _get_footer_texts(lang)

        return html.Footer(
            [
                # Linha divisória sutil acima do footer
                html.Hr(className="m-0 footer-divider-top"),
                dbc.Container(
                    [
                        # ===== Linha Única: 3 Colunas =====
                        dbc.Row(
                            [
                                # Coluna 1: Desenvolvedores
                                dbc.Col(
                                    [
                                        html.H6(
                                            texts["developers"],
                                            id="footer-developers-title",
                                            className="mb-3 text-center footer-column-title",
                                        ),
                                        html.Ul(
                                            [
                                                html.Li(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.Strong(
                                                                    dev[
                                                                        "name"
                                                                    ],
                                                                    className="me-2",
                                                                ),
                                                                html.A(
                                                                    html.Img(
                                                                        src="/assets/images/ORCID_iD.svg",
                                                                        alt="ORCID",
                                                                        className="footer-orcid-icon",
                                                                    ),
                                                                    href=f"https://orcid.org/{dev['orcid']}",
                                                                    target="_blank",
                                                                    rel="noopener noreferrer",
                                                                    title=f"ORCID: {dev['orcid']}",
                                                                ),
                                                            ],
                                                            className="d-flex align-items-center justify-content-center",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    [
                                                                        html.I(
                                                                            className="bi bi-envelope me-1"
                                                                        ),
                                                                        dev[
                                                                            "email"
                                                                        ],
                                                                    ],
                                                                    className="footer-email-link small",
                                                                ),
                                                                dcc.Clipboard(
                                                                    content=dev[
                                                                        "email"
                                                                    ],
                                                                    title="Copiar email",
                                                                    className="ms-2 footer-copy-btn",
                                                                ),
                                                            ],
                                                            className="d-flex align-items-center justify-content-center",
                                                        ),
                                                    ],
                                                    className="footer-dev-item list-unstyled",
                                                )
                                                for dev in footer_manager.get_developer_data()
                                            ],
                                            className="list-unstyled",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-4 text-center",
                                ),
                                # Coluna 2: Parceiros (logos maiores)
                                dbc.Col(
                                    [
                                        html.H6(
                                            texts["partners"],
                                            id="footer-partners-title",
                                            className="mb-3 text-center footer-column-title",
                                        ),
                                        html.Div(
                                            [
                                                html.A(
                                                    html.Img(
                                                        src=footer_manager.get_logo_path(
                                                            partner
                                                        ),
                                                        alt=f"Logo {partner.upper()}",
                                                        className="footer-partner-logo logo-partner",
                                                    ),
                                                    href=url,
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    title=f"Visitar {partner.upper()}",
                                                    className="footer-partner-link",
                                                )
                                                for partner, url in footer_manager.get_partner_data().items()
                                            ],
                                            className="footer-partners-grid",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-4 text-center",
                                ),
                                # Coluna 3: Links Importantes (horizontal em uma linha)
                                dbc.Col(
                                    [
                                        html.H6(
                                            texts["links"],
                                            id="footer-links-title",
                                            className="mb-3 text-center footer-column-title",
                                        ),
                                        html.Div(
                                            [
                                                html.A(
                                                    [
                                                        html.Img(
                                                            src="/assets/images/github.svg",
                                                            alt="GitHub",
                                                            className="footer-github-icon",
                                                        ),
                                                        html.Span(
                                                            "GitHub",
                                                            className="d-block small mt-1 footer-icon-label",
                                                        ),
                                                    ],
                                                    href=(
                                                        "https://github.com/"
                                                        "angela-cunha-soares/"
                                                        "EVAONLINE"
                                                    ),
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    title="Repositório GitHub",
                                                    className="footer-icon-link",
                                                ),
                                                html.A(
                                                    [
                                                        html.I(
                                                            className="bi bi-file-earmark-text footer-icon",
                                                        ),
                                                        html.Span(
                                                            "License",
                                                            id="footer-license-label",
                                                            className="d-block small mt-1 footer-icon-label",
                                                        ),
                                                    ],
                                                    href=(
                                                        "https://github.com/"
                                                        "angela-cunha-soares/"
                                                        "EVAONLINE/blob/main/"
                                                        "LICENSE"
                                                    ),
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    title="Licença AGPL-3.0",
                                                    className="footer-icon-link license-link",
                                                ),
                                                html.A(
                                                    [
                                                        html.I(
                                                            className="bi bi-book footer-icon",
                                                        ),
                                                        html.Span(
                                                            "Documentation",
                                                            id="footer-docs-label",
                                                            className="d-block small mt-1 footer-icon-label",
                                                        ),
                                                    ],
                                                    href="/documentation",
                                                    title="Documentação",
                                                    className="footer-icon-link docs-link",
                                                ),
                                                html.A(
                                                    [
                                                        html.I(
                                                            className="bi bi-journal-text footer-icon",
                                                        ),
                                                        html.Span(
                                                            "FAO-56",
                                                            className="d-block small mt-1 footer-icon-label",
                                                        ),
                                                    ],
                                                    href="https://www.fao.org/3/x0490e/x0490e00.htm",
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    title="FAO Irrigation and Drainage Paper 56",
                                                    className="footer-icon-link",
                                                ),
                                                html.A(
                                                    [
                                                        html.Img(
                                                            src="/assets/images/zenodo.svg",
                                                            alt="Zenodo",
                                                            className="footer-zenodo-icon",
                                                        ),
                                                        html.Span(
                                                            "Zenodo",
                                                            className="d-block small mt-1 footer-icon-label",
                                                        ),
                                                    ],
                                                    href=footer_manager.get_citation_data()[
                                                        "zenodo_url"
                                                    ],
                                                    target="_blank",
                                                    rel="noopener noreferrer",
                                                    title="Dataset no Zenodo",
                                                    className="footer-icon-link",
                                                ),
                                            ],
                                            className="footer-links-grid",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-4 text-center",
                                ),
                            ],
                            className="py-4 justify-content-center",
                        ),
                        # ===== Seção "Como citar" =====
                        html.Hr(className="my-2 footer-divider-copyright"),
                        _create_citation_section(texts),
                        # Contador de Visitantes (tempo real)
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.I(
                                                className="bi bi-people-fill me-2 footer-visitors",
                                            ),
                                            html.Span(
                                                "Visitors: ",
                                                id="visitor-label",
                                                className="text-muted small",
                                            ),
                                            html.Strong(
                                                id="visitor-count",
                                                children="...",
                                                className="text-primary small",
                                            ),
                                            html.Span(
                                                " | Last hour: ",
                                                id="visitor-hourly-label",
                                                className="text-muted small ms-2",
                                            ),
                                            html.Strong(
                                                id="visitor-count-hourly",
                                                children="...",
                                                className="text-info small",
                                            ),
                                        ],
                                        className="text-center mt-3 mb-2",
                                    ),
                                    width=12,
                                ),
                            ],
                        ),
                        # Linha de Copyright
                        html.Hr(className="my-2 footer-divider-copyright"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.P(
                                        [
                                            f"Copyright ©{footer_manager.current_year} ",
                                            html.Strong("EVAonline"),
                                            html.Span(
                                                ". Open-source under license ",
                                                id="footer-copyright",
                                            ),
                                            html.A(
                                                "AGPLv3",
                                                href="https://github.com/angela-cunha-soares/EVAONLINE/blob/main/LICENSE",
                                                target="_blank",
                                                rel="noopener noreferrer",
                                                className="footer-license-link",
                                            ),
                                            ".",
                                        ],
                                        className="text-center mb-0 small text-muted",
                                    ),
                                    width=12,
                                ),
                            ],
                            className="mt-2",
                        ),
                    ],
                    fluid=False,
                    className="footer-container",
                ),
            ],
            className="bg-white footer-professional",
        )
    except Exception as e:
        logger.error(f"❌ Erro ao criar footer: {e}")
        return _create_fallback_footer()


def _get_footer_texts(lang: str) -> Dict:
    """Textos i18n usando sistema centralizado de traduções."""
    from shared_utils.get_translations import t

    return {
        "developers": t(lang, "footer", "developers", default="Developers"),
        "partners": t(lang, "footer", "partners", default="Partners"),
        "links": t(lang, "footer", "links", default="Important Links"),
        "cite_title": t(
            lang, "footer", "cite_title", default="How to Cite"
        ),
        "cite_intro": t(
            lang,
            "footer",
            "cite_intro",
            default="If you use EVAonline in your research, please cite:",
        ),
        "cite_paper": t(lang, "footer", "cite_paper", default="Article"),
        "cite_dataset": t(
            lang, "footer", "cite_dataset", default="Dataset (Zenodo)"
        ),
        "cite_code": t(
            lang, "footer", "cite_code", default="Code (GitHub)"
        ),
        "cite_copy": t(
            lang, "footer", "cite_copy", default="Copy citation"
        ),
    }


def _create_citation_section(texts: Dict) -> dbc.Row:
    """Faixa 'Como citar' com referência completa, botão de copiar e badges."""
    c = footer_manager.get_citation_data()
    return dbc.Row(
        dbc.Col(
            html.Div(
                [
                    # Título
                    html.H6(
                        [
                            html.I(className="bi bi-quote me-2"),
                            html.Span(
                                texts["cite_title"],
                                id="footer-cite-title",
                            ),
                        ],
                        className="footer-cite-title text-center mb-2",
                    ),
                    # Intro
                    html.P(
                        texts["cite_intro"],
                        id="footer-cite-intro",
                        className="footer-cite-intro text-center mb-2",
                    ),
                    # Referência formatada + botão copiar
                    html.Div(
                        [
                            html.P(
                                [
                                    f"{c['authors']} ({c['year']}). ",
                                    html.Em(f"{c['title']}. "),
                                    html.Span(
                                        f"{c['journal']}, {c['volume']}, "
                                        f"{c['article_number']}. ",
                                        className="footer-cite-journal",
                                    ),
                                    html.A(
                                        f"https://doi.org/{c['doi']}",
                                        href=c["doi_url"],
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        className="footer-cite-doi-link",
                                    ),
                                ],
                                className="footer-cite-text mb-0",
                            ),
                            dcc.Clipboard(
                                content=footer_manager.get_citation_text(),
                                title=texts["cite_copy"],
                                className="footer-cite-copy-btn ms-2",
                            ),
                        ],
                        className=(
                            "footer-cite-box d-flex align-items-start "
                            "justify-content-center"
                        ),
                    ),
                ],
                className="footer-cite-section",
            ),
            width=12,
        ),
        className="mt-1",
    )


def _create_fallback_footer():
    """Fallback simples."""
    return html.Footer(
        html.Div(
            html.P(
                "© 2025 ETO Calculator",
                className="text-center text-muted py-3 mb-0 small",
            ),
            className="bg-white border-top",
        )
    )


# Versão minimalista mantida para compatibilidade
def create_simple_footer(lang: str = "pt") -> html.Footer:
    """Versão minimalista."""
    texts = _get_footer_texts(lang)
    return html.Footer(
        dbc.Container(
            html.Div(
                [
                    html.P(
                        [
                            f"© {footer_manager.current_year} ETO Calculator | ",
                            html.A(
                                "Documentação",
                                href="/documentation",
                                className="text-muted",
                            ),
                            " | ",
                            html.A(
                                "Sobre", href="/about", className="text-muted"
                            ),
                            " | ",
                            html.A(
                                "ESALQ/USP",
                                href="https://www.esalq.usp.br/",
                                target="_blank",
                                className="text-muted",
                            ),
                        ],
                        className="text-center mb-0 small",
                    ),
                ],
                className="py-3",
            ),
            fluid=True,
            className="footer-simple-container",
        ),
        className="bg-white border-top",
    )
