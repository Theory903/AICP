"""ApprovalRequest protocol for Human-in-the-Loop.

This module implements HITL as a first-class protocol primitive.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApprovalDecision(str, Enum):
    """Decision on an approval request."""

    APPROVE = "approve"
    REJECT = "reject"
    REVOKE = "revoke"


@dataclass
class ApprovalRisk:
    """Risk assessment for an approval request."""

    level: str
    factors: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class ApprovalContext:
    """Context about the entity requesting approval."""

    requester_id: str | None = None
    requester_email: str | None = None
    requester_role: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass
class ApprovalChange:
    """Proposed change for approval."""

    capability_name: str
    arguments: dict[str, Any]
    resource_type: str | None = None
    resource_id: str | None = None
    description: str | None = None


@dataclass
class ApprovalRequest:
    """Protocol object for Human-in-the-Loop approval.

    This is a first-class protocol primitive, not a UI popup.
    The runtime pauses execution when approval is required,
    emits this structured object, and resumes when a decision comes back.

    Attributes:
        id: Unique identifier (format: apr_xxxxx)
        capability_name: The capability being requested
        arguments: Arguments for the capability execution
        status: Current status of the request
        approver_role: Role required to approve (e.g., finance_manager)
        approver_email: Specific approver email (optional)
        requester: Context about who/what requested this
        risk: Risk assessment
        expires_at: When this request expires
        created_at: When the request was created
        decided_at: When the decision was made
        decided_by: Who made the decision
        decision: The decision (approve/reject/revoke)
        reason: Human-readable reason for decision
        execution_id: ID of the execution this approval is for
        workflow_id: ID of the workflow this approval is for (if any)
    """

    id: str
    capability_name: str
    arguments: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_role: str | None = None
    approver_email: str | None = None
    requester: ApprovalContext = field(default_factory=ApprovalContext)
    risk: ApprovalRisk | None = None
    expires_in_seconds: int = 86400
    created_at: datetime = field(default_factory=datetime.utcnow)
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision: ApprovalDecision | None = None
    reason: str | None = None
    execution_id: str | None = None
    workflow_id: str | None = None

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
        expires_in_seconds: int = 86400,
        execution_id: str | None = None,
        workflow_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        return cls(
            id=f"apr_{uuid.uuid4().hex[:12]}",
            capability_name=capability_name,
            arguments=arguments,
            approver_role=approver_role,
            approver_email=approver_email,
            requester=requester or ApprovalContext(),
            risk=risk,
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
        """Check if the request has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if the request is still pending."""
        return self.status == ApprovalStatus.PENDING and not self.is_expired

    def approve(
        self,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Approve this request."""
        if not self.is_pending:
            raise ValueError(f"Cannot approve request in status: {self.status}")

        self.status = ApprovalStatus.APPROVED
        self.decision = ApprovalDecision.APPROVE
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.utcnow()
        return self

    def reject(
        self,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Reject this request."""
        if not self.is_pending:
            raise ValueError(f"Cannot reject request in status: {self.status}")

        self.status = ApprovalStatus.REJECTED
        self.decision = ApprovalDecision.REJECT
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.utcnow()
        return self

    def revoke(self, decided_by: str, reason: str | None = None) -> ApprovalRequest:
        """Revoke a previously approved request."""
        if self.status != ApprovalStatus.APPROVED:
            raise ValueError(f"Cannot revoke request in status: {self.status}")

        self.status = ApprovalStatus.REVOKED
        self.decision = ApprovalDecision.REVOKE
        self.decided_by = decided_by
        self.reason = reason
        self.decided_at = datetime.utcnow()
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "capability_name": self.capability_name,
            "arguments": self.arguments,
            "status": self.status.value,
            "approver_role": self.approver_role,
            "approver_email": self.approver_email,
            "requester": {
                "requester_id": self.requester.requester_id,
                "requester_email": self.requester.requester_email,
                "requester_role": self.requester.requester_role,
                "tenant_id": self.requester.tenant_id,
                "session_id": self.requester.session_id,
            },
            "risk": {
                "level": self.risk.level,
                "factors": self.risk.factors,
                "score": self.risk.score,
            } if self.risk else None,
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

    Args:
        capability_name: Name of the capability
        arguments: Arguments being passed
        thresholds: Threshold configuration (e.g., {"amount": 10000})

    Returns:
        ApprovalRisk with level and factors
    """
    factors = []
    score = 0.0

    thresholds = thresholds or {}

    amount_keys = ["amount", "value", "price", "total", "cost"]
    for key in amount_keys:
        if key in arguments:
            try:
                amount = float(arguments[key])
                if amount > 10000:
                    factors.append(f"High transaction amount: {amount}")
                    score += 0.5
                elif amount > 1000:
                    factors.append(f"Medium transaction amount: {amount}")
                    score += 0.2
            except (ValueError, TypeError):
                pass

    delete_keys = ["delete", "remove", "destroy", "cancel"]
    for key in delete_keys:
        if key.lower() in capability_name.lower():
            factors.append("Destructive action")
            score += 0.4

    admin_keys = ["admin", "root", "superuser"]
    for key in admin_keys:
        if key.lower() in capability_name.lower():
            factors.append("Administrative action")
            score += 0.5

    data_keys = ["ssn", "password", "secret", "credit_card", "api_key"]
    for key in data_keys:
        for arg_key, arg_val in arguments.items():
            if key.lower() in arg_key.lower():
                factors.append(f"Sensitive data access: {arg_key}")
                score += 0.3

    if score >= 0.7:
        level = "high"
    elif score >= 0.3:
        level = "medium"
    else:
        level = "low"

    return ApprovalRisk(level=level, factors=factors, score=score)
