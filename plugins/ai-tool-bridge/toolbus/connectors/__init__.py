"""
Connectors - External service connection management.

Plugins register their connectors here; the bridge manages lifecycle.
"""

from .registry import ConnectorRegistry, connector_registry

__all__ = [
    "ConnectorRegistry",
    "connector_registry",
]
