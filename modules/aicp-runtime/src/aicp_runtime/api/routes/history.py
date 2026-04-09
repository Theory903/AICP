"""History routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from aicp_runtime.services.audit import AuditService


def _normalize_filter(value: str | None) -> str | None:
    """Normalize optional query filter values."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def build_history_router(audit_service: AuditService) -> APIRouter:
    """Build the audit/history API router."""
    router = APIRouter(tags=["history"])

    @router.get("/history")
    async def list_history_entries(
        workflow_id: str | None = Query(default=None),
        capability_name: str | None = Query(default=None),
        approval_request_id: str | None = Query(default=None),
    ) -> list[dict[str, Any]]:
        """List audit history entries, optionally filtered by workflow, capability, or approval request."""
        return await audit_service.list_entries(
            workflow_id=_normalize_filter(workflow_id),
            capability_name=_normalize_filter(capability_name),
            approval_request_id=_normalize_filter(approval_request_id),
        )

    return router
