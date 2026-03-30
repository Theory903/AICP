"""Approval routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aicp_runtime.services.approvals import ApprovalService


class ApprovalDecisionRequest(BaseModel):
    """Approval decision payload."""

    decision: str
    approver: str
    reason: str | None = None
    modified_arguments: dict[str, Any] | None = None


def build_approvals_router(approval_service: ApprovalService) -> APIRouter:
    router = APIRouter()

    @router.get("/approvals")
    async def list_approvals():
        return await approval_service.list_approvals()

    @router.get("/approvals/{approval_id}")
    async def get_approval(approval_id: str):
        approval = await approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        return approval

    @router.post("/approvals/{approval_id}/decide")
    async def decide_approval(approval_id: str, request: ApprovalDecisionRequest):
        try:
            return await approval_service.decide(
                approval_id,
                decision=request.decision,
                approver=request.approver,
                reason=request.reason,
                modified_arguments=request.modified_arguments,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
