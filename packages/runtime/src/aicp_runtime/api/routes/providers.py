"""Provider runtime routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from aicp_runtime.services.provider_health import ProviderHealthService


class ProviderHealthView(BaseModel):
    """Coarse provider health summary derived from runtime activity."""

    provider_name: str
    provider_type: str
    recent_total: int
    success_count: int
    failure_count: int
    auth_failure_count: int
    rate_limit_count: int
    success_rate: float
    auth_failure_rate: float
    failure_rate: float
    recent_latency_ms: float | None = None
    recent_error_code_mix: dict[str, int]
    last_error_code: str | None = None
    health_status: str
    last_activity_at: str | None = None


def build_provider_health_router(
    provider_health_service: ProviderHealthService,
) -> APIRouter:
    """Build the provider health API router."""
    router = APIRouter(tags=["providers"])

    @router.get("/providers/health", response_model=list[ProviderHealthView])
    async def list_provider_health(
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[ProviderHealthView]:
        summaries = await provider_health_service.list_provider_health(limit=limit)
        return [ProviderHealthView.model_validate(summary) for summary in summaries]

    return router
