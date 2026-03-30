"""History routes."""

from fastapi import APIRouter

from aicp_runtime.services.audit import AuditService


def build_history_router(audit_service: AuditService) -> APIRouter:
    router = APIRouter()

    @router.get("/history")
    async def list_history(
        workflow_id: str | None = None,
        capability_name: str | None = None,
        approval_request_id: str | None = None,
    ):
        return await audit_service.list_entries(
            workflow_id=workflow_id,
            capability_name=capability_name,
            approval_request_id=approval_request_id,
        )

    return router
