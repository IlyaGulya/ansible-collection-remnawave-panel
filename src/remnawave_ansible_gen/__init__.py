"""Remnawave Ansible Module Generator."""

from .cli import main
from .models import DiscoveredEndpoint, DiscoveredResource

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "main",
    "DiscoveredEndpoint",
    "DiscoveredResource",
]
