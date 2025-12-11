"""
AI Tool Bridge - Plugin-based daemon providing tools for AI agents.

Bridges AI agents (like Claude) to external services via a unified HTTP API.
"""

__version__ = "1.0.0"

from .config import BridgeConfig, config

__all__ = [
    "__version__",
    "BridgeConfig",
    "config",
]
