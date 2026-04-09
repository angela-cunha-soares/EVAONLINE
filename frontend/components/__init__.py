"""
Módulo de componentes reutilizáveis para o aplicativo EVAonline.

Este módulo centraliza a exportação de todos os componentes de UI:
- Navbar e Footer
- Mapa mundial interativo
- Cards informativos (FAO, fontes de dados, métricas)
"""

# Core layout components
from .footer import create_footer, create_simple_footer
from .navbar import create_navbar
from .world_map_leaflet import create_world_map

# Info cards
from .info_cards import (
    create_collapsible_info_section,
    create_comparison_explanation_card,
    create_data_sources_card,
    create_evaonline_method_card,
    create_fao_method_card,
    create_info_sidebar,
    create_metrics_card,
)

# Exportar todos os componentes
__all__ = [
    # Core layout
    "create_navbar",
    "create_footer",
    "create_simple_footer",
    "create_world_map",
    # Info cards
    "create_fao_method_card",
    "create_data_sources_card",
    "create_evaonline_method_card",
    "create_comparison_explanation_card",
    "create_metrics_card",
    "create_info_sidebar",
    "create_collapsible_info_section",
]
