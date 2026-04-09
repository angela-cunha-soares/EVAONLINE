"""
Layout base global do app - usa páginas modulares.
"""

from dash import html, dcc

# Import layouts das páginas (usando página unificada)
from ..pages.home import home_layout
from ..components.navbar import create_navbar
from ..components.footer import create_footer


def create_base_layout():
    """
    Layout base com roteamento para páginas.

    Returns:
        html.Div: Layout completo da aplicação
    """
    return html.Div(
        [
            # URL para roteamento
            dcc.Location(id="url", refresh=False),
            # Store para idioma selecionado (padrão: inglês)
            dcc.Store(id="language-store", storage_type="local", data="en"),
            # Dummy div for datepicker locale clientside callback
            html.Div(id="datepicker-locale-output", style={"display": "none"}),
            # Store GLOBAL para passar coordenadas entre páginas (sessionStorage)
            dcc.Store(
                id="navigation-coordinates", storage_type="session", data=None
            ),
            # Store para identificação única da sessão do usuário (sessionStorage)
            # Cada aba/janela do navegador terá um ID único
            dcc.Store(id="app-session-id", storage_type="session", data=None),
            # Flag: visitante já foi contabilizado nesta sessão?
            dcc.Store(
                id="visitor-incremented",
                storage_type="session",
                data=False,
            ),
            # Interval para atualizar contador de visitantes (a cada 10 segundos)
            dcc.Interval(
                id="visitor-counter-interval",
                interval=10 * 1000,  # 10 segundos em milissegundos
                n_intervals=0,
            ),
            # Navbar
            create_navbar(),
            # Conteúdo principal (será atualizado por callback)
            html.Div(
                id="page-content",
                children=home_layout,  # Default: home page
            ),
            # Footer
            create_footer(),
        ],
        className="app-root",
    )
