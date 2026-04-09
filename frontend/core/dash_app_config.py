import flask
import dash_bootstrap_components as dbc
from dash import Dash
from pathlib import Path


def create_dash_app(standalone=False):
    """
    Cria o app Dash sem servidor Flask para integração ASGI.
    Args:
        standalone: Se True, configura arquivos estáticos para execução independente
    Returns:
        tuple: (app, None) - app Dash e None para servidor
    """
    # Determinar caminho correto para assets ANTES de criar o app
    assets_path = Path(__file__).parent.parent / "assets"

    # Criar servidor Flask primeiro
    server = flask.Flask(__name__)

    app = Dash(
        __name__,
        server=server,
        title="EVAonline",
        update_title=None,
        assets_folder=str(assets_path),
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/materia/bootstrap.min.css",
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css",
            "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css",
        ],
        external_scripts=[
            "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js",
        ],
        suppress_callback_exceptions=True,
        meta_tags=[
            {
                "name": "viewport",
                "content": "width=device-width, initial-scale=1",
            },
        ],
    )

    # Desabilitar o favicon padrão do Dash e usar emoji via SVG
    app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌦️</text></svg>">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

    # Configurar servidor Flask para servir assets quando standalone
    if standalone:
        from flask import send_from_directory

        @server.route("/assets/<path:filename>")
        def serve_assets(filename):
            """Serve arquivos estáticos de assets/"""
            return send_from_directory(assets_path, filename)

    return app, server
