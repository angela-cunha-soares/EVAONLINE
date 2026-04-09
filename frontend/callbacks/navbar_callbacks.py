"""
Callbacks para funcionalidades da navbar.

Callbacks:
1. toggle_language: Alterna entre PT/EN
2. translate_navbar_links: Traduz links da navbar
3. highlight_active_link: Destaca link ativo

Dependências:
- language-store (base_layout.py): Armazena idioma atual
- language-toggle (navbar.py): Botão de tradução
- language-label (navbar.py): Label do botão
- nav-home, nav-documentation, nav-about (navbar.py): Links
"""

import logging

from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate

from shared_utils.get_translations import t

logger = logging.getLogger(__name__)


# ============================================================================
# CALLBACK 1: Toggle de idioma (botão PT/EN)
# ============================================================================
@callback(
    Output("language-store", "data"),
    Input("language-toggle", "n_clicks"),
    State("language-store", "data"),
    prevent_initial_call=True,
)
def toggle_language(n_clicks, current_language):
    """
    Alterna entre Português e Inglês ao clicar no botão.

    O label é atualizado por translate_navbar_links (que reage ao language-store).

    Args:
        n_clicks: Número de cliques no botão
        current_language: Idioma atual ("en" ou "pt")

    Returns:
        str: Novo código de idioma
    """
    if not n_clicks:
        raise PreventUpdate

    # Alterna o idioma
    new_language = "pt" if current_language == "en" else "en"

    logger.info(f"🌐 Idioma alterado: {current_language} → {new_language}")

    return new_language


# ============================================================================
# CALLBACK 2: Tradução dos links da navbar
# ============================================================================
@callback(
    Output("language-label", "children"),
    Output("nav-home", "children"),
    Output("nav-documentation", "children"),
    Output("nav-architecture", "children"),
    Output("nav-about", "children"),
    Input("language-store", "data"),
)
def translate_navbar_links(lang):
    """
    Traduz os links da navbar e atualiza o label do botão de idioma.

    Dispara automaticamente quando language-store é atualizado.
    Também dispara na carga inicial (language-store default = "en").

    O label do botão mostra o OUTRO idioma (convite para trocar):
    - Se está em EN → botão mostra "PORTUGUÊS"
    - Se está em PT → botão mostra "ENGLISH"
    """
    if not lang:
        lang = "en"

    return (
        t(lang, "navbar", "language_button", default="PORTUGUÊS"),
        t(lang, "navbar", "home", default="HOME"),
        t(lang, "navbar", "documentation", default="DOCUMENTATION"),
        t(lang, "navbar", "architecture", default="ARCHITECTURE"),
        t(lang, "navbar", "about", default="ABOUT"),
    )


# ============================================================================
# CALLBACK 3: Destaque do link ativo
# ============================================================================
@callback(
    [
        Output("nav-home", "style"),
        Output("nav-documentation", "style"),
        Output("nav-architecture", "style"),
        Output("nav-about", "style"),
    ],
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def highlight_active_link(pathname):
    """
    Destaca o link ativo na navbar baseado na URL atual.

    Rotas que ativam "Home": /, /eto-calculator
    Link GitHub (externo) não é tratado aqui.
    """
    base_style = {
        "fontWeight": "400",
        "color": "#495057",
        "borderBottom": "2px solid transparent",
        "transition": "all 0.3s ease",
    }

    active_style = {
        "fontWeight": "600",
        "color": "#00695c",
        "borderBottom": "2px solid #00695c",
        "transition": "all 0.3s ease",
    }

    is_home = pathname in ("/", "/eto-calculator", None)
    is_docs = pathname == "/documentation"
    is_arch = pathname == "/architecture"
    is_about = pathname == "/about"

    return (
        active_style if is_home else base_style,
        active_style if is_docs else base_style,
        active_style if is_arch else base_style,
        active_style if is_about else base_style,
    )


logger.info("✅ Callbacks da navbar registrados com sucesso")
