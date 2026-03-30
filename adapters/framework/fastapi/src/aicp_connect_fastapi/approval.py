"""Approval endpoints for FastAPI.

Provides REST endpoints for Human-in-the-Loop approval workflows.
"""

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from aicp.approval import ApprovalStatus
from aicp.approval_service import ApprovalService


class ApprovalDecisionRequest(BaseModel):
    """Request body for approval decisions."""

    decided_by: str
    reason: str | None = None


class ApprovalResponse(BaseModel):
    """Response for approval requests."""

    id: str
    status: str
    capability_name: str
    arguments: dict[str, Any]
    risk: dict[str, Any] | None
    created_at: str
    expires_at: str
    decided_by: str | None = None
    decision: str | None = None
    reason: str | None = None


def create_approval_router(
    approval_service: ApprovalService,
    executor: Any = None,
) -> APIRouter:
    """Create approval endpoints router.

    Args:
        approval_service: The approval service instance
        executor: Optional executor for executing after approval

    Returns:
        Configured APIRouter with approval endpoints
    """
    router = APIRouter(prefix="/approval-requests", tags=["approval"])

    @router.get("", response_model=list[ApprovalResponse])
    async def list_approval_requests(
        approver_role: str | None = None,
        approver_email: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalResponse]:
        """List approval requests."""
        if status == "pending" or status is None:
            requests = await approval_service.list_pending(
                approver_role=approver_role,
                approver_email=approver_email,
                limit=limit,
            )
        else:
            requests = []
            if approver_role:
                requests = await approval_service.list_pending(
                    approver_role=approver_role, limit=limit
                )

        return [
            ApprovalResponse(
                id=r.id,
                status=r.status.value,
                capability_name=r.capability_name,
                arguments=r.arguments,
                risk={"level": r.risk.level, "factors": r.risk.factors}
                if r.risk
                else None,
                created_at=r.created_at.isoformat(),
                expires_at=r.expires_at.isoformat(),
                decided_by=r.decided_by,
                decision=r.decision.value if r.decision else None,
                reason=r.reason,
            )
            for r in requests
        ]

    @router.get("/{request_id}", response_model=ApprovalResponse)
    async def get_approval_request(request_id: str) -> ApprovalResponse:
        """Get a specific approval request."""
        request = await approval_service.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        return ApprovalResponse(
            id=request.id,
            status=request.status.value,
            capability_name=request.capability_name,
            arguments=request.arguments,
            risk={"level": request.risk.level, "factors": request.risk.factors}
            if request.risk
            else None,
            created_at=request.created_at.isoformat(),
            expires_at=request.expires_at.isoformat(),
            decided_by=request.decided_by,
            decision=request.decision.value if request.decision else None,
            reason=request.reason,
        )

    @router.post("/{request_id}/approve", response_model=ApprovalResponse)
    async def approve_request(
        request_id: str,
        decision: ApprovalDecisionRequest,
    ) -> ApprovalResponse:
        """Approve an approval request."""
        try:
            request = await approval_service.approve(
                request_id, decision.decided_by, decision.reason
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if executor and request.execution_id:
            await executor.execute_after_approval(request_id)

        return ApprovalResponse(
            id=request.id,
            status=request.status.value,
            capability_name=request.capability_name,
            arguments=request.arguments,
            risk={"level": request.risk.level, "factors": request.risk.factors}
            if request.risk
            else None,
            created_at=request.created_at.isoformat(),
            expires_at=request.expires_at.isoformat(),
            decided_by=request.decided_by,
            decision=request.decision.value if request.decision else None,
            reason=request.reason,
        )

    @router.post("/{request_id}/reject", response_model=ApprovalResponse)
    async def reject_request(
        request_id: str,
        decision: ApprovalDecisionRequest,
    ) -> ApprovalResponse:
        """Reject an approval request."""
        try:
            request = await approval_service.reject(
                request_id, decision.decided_by, decision.reason
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return ApprovalResponse(
            id=request.id,
            status=request.status.value,
            capability_name=request.capability_name,
            arguments=request.arguments,
            risk={"level": request.risk.level, "factors": request.risk.factors}
            if request.risk
            else None,
            created_at=request.created_at.isoformat(),
            expires_at=request.expires_at.isoformat(),
            decided_by=request.decided_by,
            decision=request.decision.value if request.decision else None,
            reason=request.reason,
        )

    @router.post("/{request_id}/revoke", response_model=ApprovalResponse)
    async def revoke_request(
        request_id: str,
        decision: ApprovalDecisionRequest,
    ) -> ApprovalResponse:
        """Revoke a previously approved request."""
        try:
            request = await approval_service.revoke(
                request_id, decision.decided_by, decision.reason
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return ApprovalResponse(
            id=request.id,
            status=request.status.value,
            capability_name=request.capability_name,
            arguments=request.arguments,
            risk={"level": request.risk.level, "factors": request.risk.factors}
            if request.risk
            else None,
            created_at=request.created_at.isoformat(),
            expires_at=request.expires_at.isoformat(),
            decided_by=request.decided_by,
            decision=request.decision.value if request.decision else None,
            reason=request.reason,
        )

    @router.post("/{request_id}/execute", response_model=dict)
    async def execute_approved_request(
        request_id: str,
        request_body: dict | None = None,
    ) -> dict:
        """Execute a capability after approval is granted."""
        if not executor:
            raise HTTPException(
                status_code=400, detail="Executor not configured"
            )

        approval_request = await approval_service.get_request(request_id)
        if not approval_request:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if approval_request.status != ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail=f"Request not approved: {approval_request.status.value}",
            )

        context = request_body.get("context", {}) if request_body else {}
        result = await executor.execute_after_approval(request_id, context)

        return {
            "approval_request_id": request_id,
            "execution_result": result.model_dump(),
        }

    return router


def mount_approval(
    app: FastAPI,
    approval_service: ApprovalService,
    executor: Any = None,
    path: str = "/approval-requests",
) -> None:
    """Mount approval endpoints on a FastAPI app.

    Args:
        app: FastAPI application
        approval_service: The approval service instance
        executor: Optional executor for executing after approval
        path: Base path for approval endpoints
    """
    router = create_approval_router(approval_service, executor)
    router.prefix = path
    app.include_router(router)
