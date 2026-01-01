"""Discovery utilities for FastAPI adapter."""

from fastapi import FastAPI

from aicp.adapters.framework.fastapi.mapper import create_discovery_response
from aicp.adapters.framework.fastapi.mount import get_aicp_capabilities, get_aicp_config


def create_discovery_handler(app: FastAPI):
    """Create a discovery handler for the app.

    Args:
        app: FastAPI application

    Returns:
        Discovery handler function
    """

    async def discovery():
        config = get_aicp_config(app)
        capabilities = get_aicp_capabilities(app)

        if config is None:
            return {"error": "AICP not mounted on this application"}

        return create_discovery_response(capabilities, config)

    return discovery
