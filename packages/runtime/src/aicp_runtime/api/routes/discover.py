"""Discovery routes."""

from fastapi import APIRouter

from aicp_runtime.services.discovery import DiscoveryService


def build_discover_router(discovery_service: DiscoveryService) -> APIRouter:
    router = APIRouter()

    @router.get("/discover")
    async def discover() -> dict:
        return await discovery_service.discover()

    return router
