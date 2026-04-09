"""Approval routes."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from aicp_runtime.services.approvals import ApprovalService


class ApprovalDecision(str, Enum):
    """Allowed approval decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecisionRequest(BaseModel):
    """Approval decision payload."""

    decision: ApprovalDecision
    approver: str = Field(min_length=1)
    reason: str | None = None
    modified_arguments: dict[str, Any] | None = None

    @field_validator("approver", mode="before")
    @classmethod
    def _normalize_approver(cls, value: Any) -> str:
        approver = str(value or "").strip()
        if not approver:
            raise ValueError("approver cannot be empty")
        return approver

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, value: Any) -> str | None:
        if value is None:
            return None
        reason = str(value).strip()
        return reason or None


class IntentQueryRequest(BaseModel):
    """Request to find approved approval for matching intent."""

    capability_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class ApprovalPacketSummaryView(BaseModel):
    """Top-level approval summary for review packets."""

    id: str
    status: str
    requested_at: str | None = None
    decided_at: str | None = None
    message: str | None = None


class RequestedCapabilityView(BaseModel):
    """Requested capability details."""

    name: str
    description: str | None = None
    kind: str | None = None
    provider_name: str | None = None
    provider_type: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)


class RequesterContextView(BaseModel):
    """Requester-side context for human review."""

    requester: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    interaction_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ApproverContextView(BaseModel):
    """Approver decision details."""

    approver: str | None = None
    decision: str | None = None
    reason: str | None = None
    decided_at: str | None = None


class WorkflowLinkView(BaseModel):
    """Workflow linkage summary."""

    id: str | None = None
    name: str | None = None
    status: str | None = None
    step_id: str | None = None
    current_step_id: str | None = None
    current_step_capability: str | None = None


class ExecutionLinkView(BaseModel):
    """Execution linkage summary."""

    id: str | None = None
    status: str | None = None
    created_at: str | None = None


class ApprovalLinkageView(BaseModel):
    """Runtime linkage for approvals."""

    workflow: WorkflowLinkView
    execution: ExecutionLinkView


class ApprovalPolicyView(BaseModel):
    """Policy-trigger summary."""

    effect: str
    policy_name: str | None = None
    reason: str | None = None
    required_role: str | None = None


class ApprovalImplicationsView(BaseModel):
    """Likely next steps if the approval changes state."""

    next_action: str
    resume_available: bool = False
    next_capabilities: list[str] = Field(default_factory=list)
    next_hint: str | None = None


class ApprovalAuthSessionImplicationsView(BaseModel):
    """Session/auth coupling relevant to approval review."""

    auth_mode: str | None = None
    requires_session: bool = False
    required_session_provider: str | None = None
    refreshable: bool = False
    session_present: bool = False


class ApprovalImpactSummaryView(BaseModel):
    """Deterministic impact-analysis style summary for operators."""

    risk_level: str
    destructive: bool = False
    affected_resource_hints: list[str] = Field(default_factory=list)
    rollback_capability: str | None = None
    reversible: bool = False
    blast_radius_estimate: str
    auth_session_implications: ApprovalAuthSessionImplicationsView | None = None


class ApprovalReviewPacketView(BaseModel):
    """Structured review bundle for operators."""

    approval: ApprovalPacketSummaryView
    requested_capability: RequestedCapabilityView
    requester_context: RequesterContextView
    approver_context: ApproverContextView
    linkage: ApprovalLinkageView
    policy: ApprovalPolicyView
    impact_summary: ApprovalImpactSummaryView
    implications: ApprovalImplicationsView
    history: list[dict[str, Any]] = Field(default_factory=list)


def build_approvals_router(approval_service: ApprovalService) -> APIRouter:
    """Build the approvals API router."""
    router = APIRouter(prefix="", tags=["approvals"])

    @router.get("/approvals")
    async def list_approvals() -> list[dict[str, Any]]:
        """List all approval requests."""
        return await approval_service.list_approvals()

    @router.get("/approvals/{approval_id}")
    async def get_approval(approval_id: str) -> dict[str, Any]:
        """Get a single approval request by ID."""
        approval = await approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found",
            )
        return approval

    @router.get(
        "/approvals/{approval_id}/review-packet",
        response_model=ApprovalReviewPacketView,
    )
    async def get_approval_review_packet(approval_id: str) -> ApprovalReviewPacketView:
        """Get a structured review packet for an approval request."""
        packet = await approval_service.get_review_packet(approval_id)
        if packet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval not found",
            )
        return ApprovalReviewPacketView.model_validate(packet)

    @router.post("/approvals/{approval_id}/decide")
    async def decide_approval(
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> dict[str, Any]:
        """Apply an approval decision."""
        try:
            return await approval_service.decide(
                approval_id=approval_id,
                decision=request.decision.value,
                approver=request.approver,
                reason=request.reason,
                modified_arguments=request.modified_arguments,
            )
        except ValueError as exc:
            message = str(exc)
            lowered = message.lower()

            if "not found" in lowered:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            ) from exc

    @router.post("/approvals/find-by-intent")
    async def find_approved_for_intent(
        request: IntentQueryRequest,
    ) -> dict[str, Any] | None:
        """Find an approved approval for matching intent (capability + args + context)."""
        try:
            return await approval_service.find_approved_for_intent(
                capability_name=request.capability_name,
                arguments=request.arguments,
                context=request.context,
            )
        except Exception:
            return None

    return router
