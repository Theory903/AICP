"""Discovery routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from aicp_runtime.services.discovery import DiscoveryService


def build_discovery_router(discovery_service: DiscoveryService) -> APIRouter:
    """Build the discovery API router."""
    router = APIRouter(tags=["discovery"])

    async def _discovery_document() -> dict[str, Any]:
        return await discovery_service.discover()

    @router.get("/discover")
    async def discover_capabilities() -> dict[str, Any]:
        """Return the runtime discovery document."""
        return await _discovery_document()

    @router.get("/.well-known/aicp")
    async def discover_well_known() -> dict[str, Any]:
        """Return the AICP discovery document from the well-known path."""
        return await _discovery_document()

    return router
