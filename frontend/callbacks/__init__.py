"""
Callbacks - Lógica de interação do Dash.
"""

from .cache_callbacks import register_cache_callbacks
from .home_callbacks import register_home_callbacks
from .navigation_callbacks import register_navigation_callbacks

__all__ = [
    "register_home_callbacks",
    "register_cache_callbacks",
    "register_navigation_callbacks",
]
