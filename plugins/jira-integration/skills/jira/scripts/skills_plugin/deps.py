"""
FastAPI dependencies for Jira routes.

Usage:
    from fastapi import Depends
    from ..deps import jira

    @router.get("/issue/{key}")
    async def get_issue(key: str, client = Depends(jira)):
        return client.issue(key)
"""

from fastapi import HTTPException

from ai_tool_bridge.connectors import connector_registry


def jira():
    """Get Jira client from connector registry.

    Raises HTTPException if connector not available or unhealthy.
    """
    connector = connector_registry.get_optional("jira")
    if connector is None:
        raise HTTPException(status_code=503, detail="Jira connector not registered")

    if not connector.healthy:
        raise HTTPException(
            status_code=503,
            detail=f"Jira not connected (circuit: {connector.circuit_state})"
        )

    return connector.client


def jira_connector():
    """Get JiraConnector instance from registry.

    Raises HTTPException if connector not registered.
    """
    connector = connector_registry.get_optional("jira")
    if connector is None:
        raise HTTPException(status_code=503, detail="Jira connector not registered")
    return connector
