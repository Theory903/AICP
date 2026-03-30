"""ApprovalRequest protocol for Human-in-the-Loop.

This module implements HITL as a first-class protocol primitive.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    """Lifecycle state of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApprovalDecision(str, Enum):
    """Human decision applied to an approval request."""

    APPROVE = "approve"
    REJECT = "reject"
    REVOKE = "revoke"


class RiskLevel(str, Enum):
    """Normalized risk levels for approval evaluation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(slots=True)
class ApprovalRisk:
    """Risk assessment for an approval request."""

    level: RiskLevel
    factors: list[str] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "factors": list(self.factors),
            "score": self.score,
        }


@dataclass(slots=True)
class ApprovalContext:
    """Context about the entity requesting approval."""

    requester_id: str | None = None
    requester_email: str | None = None
    requester_role: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requester_id": self.requester_id,
            "requester_email": self.requester_email,
            "requester_role": self.requester_role,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


@dataclass(slots=True)
class ApprovalChange:
    """Proposed change for approval.

    Keep this even if not fully used everywhere yet.
    It is a legitimate protocol-level hook for richer approval UX, audit,
    and diff-aware governance.
    """

    capability_name: str
    arguments: dict[str, Any]
    resource_type: str | None = None
    resource_id: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "arguments": self.arguments,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
        }


@dataclass(slots=True)
class ApprovalRequest:
    """Protocol object for Human-in-the-Loop approval.

    This is a first-class protocol primitive, not a UI popup.
    The runtime pauses execution when approval is required,
    emits this structured object, and resumes when a decision comes back.
    """

    id: str
    capability_name: str
    arguments: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_role: str | None = None
    approver_email: str | None = None
    requester: ApprovalContext = field(default_factory=ApprovalContext)
    risk: ApprovalRisk | None = None
    change: ApprovalChange | None = None
    expires_in_seconds: int = 86400
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision: ApprovalDecision | None = None
    reason: str | None = None
    execution_id: str | None = None
    workflow_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id.startswith("apr_"):
            raise ValueError("ApprovalRequest id must start with 'apr_'")
        if not self.capability_name.strip():
            raise ValueError("capability_name cannot be empty")
        if self.expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be > 0")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.decided_at is not None and self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")

    @classmethod
    def create(
        cls,
        capability_name: str,
        arguments: dict[str, Any],
        *,
        approver_role: str | None = None,
        approver_email: str | None = None,
        requester: ApprovalContext | None = None,
        risk: ApprovalRisk | None = None,
        change: ApprovalChange | None = None,
        expires_in_seconds: int = 86400,
        execution_id: str | None = None,
        workflow_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        return cls(
            id=f"apr_{uuid.uuid4().hex[:12]}",
            capability_name=capability_name,
            arguments=dict(arguments),
            approver_role=approver_role,
            approver_email=approver_email,
            requester=requester or ApprovalContext(),
            risk=risk,
            change=change,
            expires_in_seconds=expires_in_seconds,
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

    @property
    def expires_at(self) -> datetime:
        """Calculate expiration time."""
        return self.created_at + timedelta(seconds=self.expires_in_seconds)

    @property
    def is_expired(self) -> bool:
        """Check whether the request has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check whether the request is still pending and not expired."""
        return self.status == ApprovalStatus.PENDING and not self.is_expired

    @property
    def is_terminal(self) -> bool:
        """Check whether the request is in a terminal state."""
        return self.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.REVOKED,
            ApprovalStatus.EXPIRED,
        }

    def mark_expired(self) -> ApprovalRequest:
        """Mark a pending request as expired."""
        if self.status == ApprovalStatus.PENDING:
            self.status = ApprovalStatus.EXPIRED
        return self

    def refresh_status(self) -> ApprovalRequest:
        """Synchronize state with wall clock.

        This keeps long-lived requests honest instead of pretending
        a pending request is still actionable after expiry.
        """
        if self.status == ApprovalStatus.PENDING and self.is_expired:
            self.status = ApprovalStatus.EXPIRED
        return self

    def approve(
        self,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Approve this request."""
        self.refresh_status()
        if not self.is_pending:
            raise ValueError(f"Cannot approve request in status: {self.status.value}")

        self.status = ApprovalStatus.APPROVED
        self.decision = ApprovalDecision.APPROVE
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.now(UTC)
        return self

    def reject(
        self,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Reject this request."""
        self.refresh_status()
        if not self.is_pending:
            raise ValueError(f"Cannot reject request in status: {self.status.value}")

        self.status = ApprovalStatus.REJECTED
        self.decision = ApprovalDecision.REJECT
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.now(UTC)
        return self

    def revoke(
        self,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Revoke a previously approved request."""
        if self.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Cannot revoke request in status: {self.status.value}")

        self.status = ApprovalStatus.REVOKED
        self.decision = ApprovalDecision.REVOKE
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.now(UTC)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert request to a serializable dictionary."""
        self.refresh_status()
        return {
            "id": self.id,
            "capability_name": self.capability_name,
            "arguments": self.arguments,
            "status": self.status.value,
            "approver_role": self.approver_role,
            "approver_email": self.approver_email,
            "requester": self.requester.to_dict(),
            "risk": self.risk.to_dict() if self.risk else None,
            "change": self.change.to_dict() if self.change else None,
            "expires_in_seconds": self.expires_in_seconds,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by,
            "decision": self.decision.value if self.decision else None,
            "reason": self.reason,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
        }


def calculate_risk(
    capability_name: str,
    arguments: dict[str, Any],
    thresholds: dict[str, Any] | None = None,
) -> ApprovalRisk:
    """Calculate risk level for a capability execution.

    thresholds supports overrides like:
        {
            "high_amount": 10000,
            "medium_amount": 1000,
            "destructive_score": 0.4,
            "admin_score": 0.5,
            "sensitive_score": 0.3,
        }
    """
    thresholds = thresholds or {}

    high_amount = float(thresholds.get("high_amount", 10000))
    medium_amount = float(thresholds.get("medium_amount", 1000))
    destructive_score = float(thresholds.get("destructive_score", 0.4))
    admin_score = float(thresholds.get("admin_score", 0.5))
    sensitive_score = float(thresholds.get("sensitive_score", 0.3))

    factors: list[str] = []
    score = 0.0
    capability_name_lc = capability_name.lower()

    amount_keys = {"amount", "value", "price", "total", "cost"}
    for key in amount_keys:
        if key not in arguments:
            continue
        try:
            amount = float(arguments[key])
        except (TypeError, ValueError):
            continue

        if amount > high_amount:
            factors.append(f"High transaction amount: {amount}")
            score += 0.5
        elif amount > medium_amount:
            factors.append(f"Medium transaction amount: {amount}")
            score += 0.2

    destructive_terms = {"delete", "remove", "destroy", "cancel", "revoke", "purge"}
    if any(term in capability_name_lc for term in destructive_terms):
        factors.append("Destructive action")
        score += destructive_score

    admin_terms = {"admin", "root", "superuser", "privileged"}
    if any(term in capability_name_lc for term in admin_terms):
        factors.append("Administrative action")
        score += admin_score

    sensitive_terms = {"ssn", "password", "secret", "credit_card", "api_key", "token"}
    for arg_key in arguments:
        arg_key_lc = arg_key.lower()
        if any(term in arg_key_lc for term in sensitive_terms):
            factors.append(f"Sensitive data access: {arg_key}")
            score += sensitive_score

    if score >= 0.7:
        level = RiskLevel.HIGH
    elif score >= 0.3:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return ApprovalRisk(level=level, factors=factors, score=round(score, 3))