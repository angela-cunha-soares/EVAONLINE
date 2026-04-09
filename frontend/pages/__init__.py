"""
Pages package for ETO Calculator application.
"""

from .about import about_layout, create_about_layout
from .architecture import architecture_layout, create_architecture_layout
from .documentation import create_documentation_layout
from .home import home_layout

__all__ = [
    "home_layout",
    "about_layout",
    "architecture_layout",
    "create_about_layout",
    "create_architecture_layout",
    "create_documentation_layout",
]
