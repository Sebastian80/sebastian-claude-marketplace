"""
Contracts (Protocols) for AI Tool Bridge.

These protocols define the interfaces that implementations must satisfy.
Using Protocol enables structural subtyping - no inheritance required.
"""

from .connector import ConnectorProtocol, ConnectorUnavailableError
from .plugin import PluginProtocol

__all__ = [
    "ConnectorProtocol",
    "ConnectorUnavailableError",
    "PluginProtocol",
]
