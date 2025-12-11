"""
Connectors - External service connection management.

Provides circuit breaker-protected HTTP clients for external APIs.
Plugins register their connectors here; the bridge manages lifecycle.

Example:
    from ai_tool_bridge.connectors import (
        ConnectorConfig,
        HTTPConnector,
        connector_registry,
    )

    # In plugin startup:
    config = ConnectorConfig(
        name="jira",
        base_url="https://company.atlassian.net",
        health_endpoint="/rest/api/2/myself",
    )
    connector = HTTPConnector(config)
    connector_registry.register(connector)

    # In plugin routes:
    jira = connector_registry.get("jira")
    response = await jira.get("/rest/api/2/issue/PROJ-123")
"""

from .circuit import CircuitBreaker, CircuitState
from .health import HealthMonitor
from .http import ConnectorConfig, HTTPConnector
from .registry import ConnectorRegistry, connector_registry

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    # HTTP connector
    "ConnectorConfig",
    "HTTPConnector",
    # Registry
    "ConnectorRegistry",
    "connector_registry",
    # Health monitoring
    "HealthMonitor",
]
