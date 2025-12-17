"""
FastAPI dependencies for Serena routes.

Usage:
    from fastapi import Depends
    from ..deps import serena

    @router.get("/find")
    async def find(pattern: str, client=Depends(serena)):
        return await client.find_symbol(pattern)
"""

from fastapi import HTTPException

from toolbus.connectors import connector_registry


def serena():
    """Get Serena client from connector registry.

    Raises HTTPException if connector not available or unhealthy.
    """
    connector = connector_registry.get_optional("serena")
    if connector is None:
        raise HTTPException(status_code=503, detail="Serena connector not registered")

    if not connector.healthy:
        raise HTTPException(
            status_code=503,
            detail=f"Serena not connected (circuit: {connector.circuit_state})"
        )

    return connector.client


def serena_connector():
    """Get SerenaConnector instance from registry.

    Raises HTTPException if connector not registered.
    """
    connector = connector_registry.get_optional("serena")
    if connector is None:
        raise HTTPException(status_code=503, detail="Serena connector not registered")
    return connector
