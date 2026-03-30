"""Discovery utilities for FastAPI adapter."""

from fastapi import FastAPI

from aicp_connect_fastapi.mapper import create_discovery_response
from aicp_connect_fastapi.mount import get_aicp_capabilities, get_aicp_config


def create_discovery_handler(app: FastAPI):
    async def discovery():
        config = get_aicp_config(app)
        capabilities = get_aicp_capabilities(app)

        if config is None:
            return {"error": "AICP not mounted on this application"}

        return create_discovery_response(capabilities, config)

    return discovery
