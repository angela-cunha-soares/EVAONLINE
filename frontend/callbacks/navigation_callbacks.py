"""
Callbacks para navegação entre páginas e controle de roteamento.

Features:
- Roteamento entre Home, Documentação e Sobre
- Toggle da navbar em dispositivos móveis
- Atualização dinâmica do título da página

NOTA: Navegação via NavLink usa href (browser nativo).
      Destaque de links ativos é feito em navbar_callbacks.py (via style).
"""

import logging

from dash.dependencies import ClientsideFunction, Input, Output, State

# Layouts das páginas
from ..pages.home import home_layout
from ..pages.about import create_about_layout
from ..pages.documentation import create_documentation_layout
from ..pages.architecture import create_architecture_layout

logger = logging.getLogger(__name__)


def register_navigation_callbacks(app):
    """
    Registra callbacks de navegação.

    Callbacks registrados:
    1. display_page: Roteamento baseado na URL (com suporte a idioma)
    2. toggle_navbar: Toggle da navbar em mobile
    3. clientside_callback: Atualização do título da página
    """

    # ================================================================
    # 1. ROTEAMENTO - Exibe página baseado na URL e idioma
    # ================================================================
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        Input("language-store", "data"),
    )
    def display_page(pathname, lang):
        """
        Controla a exibição das páginas baseado na URL.
        Para a página Architecture, regenera o layout com o idioma atual.

        Rotas:
        - /documentation → Página de documentação
        - /about → Página sobre
        - /architecture → Página de arquitetura (traduzível)
        - / (e qualquer outra) → Home (mapa + cálculo ETo)
        """
        if not lang:
            lang = "en"

        logger.info(f"🧭 Navegando para: {pathname} (lang={lang})")

        # Páginas dinâmicas (traduzíveis)
        if pathname == "/architecture":
            return create_architecture_layout(lang)
        if pathname == "/about":
            return create_about_layout(lang)
        if pathname == "/documentation":
            return create_documentation_layout(lang)

        # Qualquer rota não mapeada vai para home (incluindo "/" e "/eto-calculator")
        return home_layout

    # ================================================================
    # 2. TOGGLE NAVBAR - Dispositivos móveis
    # ================================================================
    @app.callback(
        Output("navbar-collapse", "is_open"),
        Input("navbar-toggler", "n_clicks"),
        State("navbar-collapse", "is_open"),
    )
    def toggle_navbar(n_clicks, is_open):
        """Alterna a navbar em dispositivos móveis."""
        if n_clicks:
            logger.debug("📱 Alternando estado da navbar")
            return not is_open
        return is_open

    # ================================================================
    # 3. TÍTULO DA PÁGINA - Clientside (sem round-trip ao servidor)
    # Usa Output dummy "url.hash" que não causa side effects
    # (hash é ignorado pelo Dash routing)
    # ================================================================
    app.clientside_callback(
        """
        function(pathname) {
            const titles = {
                '/': 'EVAonline: Home',
                '/eto-calculator': 'EVAonline: Calcular ETo',
                '/documentation': 'EVAonline: Documentation',
                '/architecture': 'EVAonline: Architecture',
                '/about': 'EVAonline: About'
            };
            document.title = titles[pathname] || 'EVAonline';
            return window.dash_clientside.no_update;
        }
        """,
        Output("url", "hash"),
        Input("url", "pathname"),
    )

    # ================================================================
    # 4. DATEPICKER LOCALE - Translates calendar month/day names
    # via DOM manipulation (MutationObserver in datepicker_locale.js)
    # ================================================================
    app.clientside_callback(
        ClientsideFunction("datepicker_locale", "set_locale"),
        Output("datepicker-locale-output", "children"),
        Input("language-store", "data"),
    )

    # ================================================================
    # 5. GEOLOCATE + LAYER TOGGLE BUTTON TITLES - Clientside
    # Updates the LocateControl button title (DOM-level) and
    # layer toggle button title when language changes
    # ================================================================
    app.clientside_callback(
        """
        function(lang) {
            setTimeout(function() {
                var btn = document.querySelector('.leaflet-control-locate a');
                if (btn) {
                    btn.title = (lang === 'pt') ? 'Minha Localização' : 'My Location';
                }
            }, 500);
            return (lang === 'pt') ? 'Alternar Camadas' : 'Toggle Layers';
        }
        """,
        Output("layer-control-toggle", "title"),
        Input("language-store", "data"),
    )

    logger.info("✅ Callbacks de navegação registrados com sucesso")
