"""ApprovalService for managing approval requests.

Provides a service interface for creating, listing, and deciding on approval requests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from aicp.approval import (
    ApprovalContext,
    ApprovalRequest,
    calculate_risk,
)


class ApprovalStore(ABC):
    """Abstract store for approval requests."""

    @abstractmethod
    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        """Store a new approval request."""
        pass

    @abstractmethod
    async def get(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        pass

    @abstractmethod
    async def update(self, request: ApprovalRequest) -> ApprovalRequest:
        """Update an approval request."""
        pass

    @abstractmethod
    async def list_pending(
        self,
        *,
        approver_role: str | None = None,
        approver_email: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List pending approval requests."""
        pass

    @abstractmethod
    async def list_by_execution(self, execution_id: str) -> list[ApprovalRequest]:
        """List approval requests for an execution."""
        pass

    @abstractmethod
    async def list_by_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        """List approval requests for a workflow."""
        pass


class InMemoryApprovalStore(ApprovalStore):
    """In-memory implementation of ApprovalStore."""

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        self._requests[request.id] = request
        return request

    async def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    async def update(self, request: ApprovalRequest) -> ApprovalRequest:
        self._requests[request.id] = request
        return request

    async def list_pending(
        self,
        *,
        approver_role: str | None = None,
        approver_email: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        results = []
        for request in self._requests.values():
            if not request.is_pending:
                continue
            if approver_role and request.approver_role != approver_role:
                continue
            if approver_email and request.approver_email != approver_email:
                continue
            if tenant_id and request.requester.tenant_id != tenant_id:
                continue
            results.append(request)
        return results[:limit]

    async def list_by_execution(self, execution_id: str) -> list[ApprovalRequest]:
        return [
            r for r in self._requests.values() if r.execution_id == execution_id
        ]

    async def list_by_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        return [
            r for r in self._requests.values() if r.workflow_id == workflow_id
        ]


ApprovalCallback = Callable[
    [ApprovalRequest], Coroutine[Any, Any, ApprovalRequest]
]


class ApprovalService:
    """Service for managing approval requests.

    This is the core HITL implementation. It:
    1. Creates approval requests when policy requires approval
    2. Stores them for later decision
    3. Calls callbacks when decisions are made to resume execution
    """

    def __init__(
        self,
        store: ApprovalStore | None = None,
        on_approved: ApprovalCallback | None = None,
        on_rejected: ApprovalCallback | None = None,
        risk_thresholds: dict[str, Any] | None = None,
    ):
        self._store = store or InMemoryApprovalStore()
        self._on_approved = on_approved
        self._on_rejected = on_rejected
        self._risk_thresholds = risk_thresholds or {}

    async def create_approval_request(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        *,
        approver_role: str | None = None,
        approver_email: str | None = None,
        requester: ApprovalContext | None = None,
        risk_thresholds: dict[str, Any] | None = None,
        expires_in_seconds: int = 86400,
        execution_id: str | None = None,
        workflow_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request.

        Args:
            capability_name: Name of the capability
            arguments: Arguments for execution
            approver_role: Role required to approve
            approver_email: Specific approver email
            requester: Context about requester
            risk_thresholds: Custom risk thresholds
            expires_in_seconds: When request expires
            execution_id: Associated execution ID
            workflow_id: Associated workflow ID

        Returns:
            Created ApprovalRequest
        """
        thresholds = risk_thresholds or self._risk_thresholds
        risk = calculate_risk(capability_name, arguments, thresholds)

        if approver_role is None and approver_email is None:
            if risk.level == "high":
                approver_role = "admin"
            elif risk.level == "medium":
                approver_role = "manager"

        request = ApprovalRequest.create(
            capability_name=capability_name,
            arguments=arguments,
            approver_role=approver_role,
            approver_email=approver_email,
            requester=requester,
            risk=risk,
            expires_in_seconds=expires_in_seconds,
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

        return await self._store.create(request)

    async def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        return await self._store.get(request_id)

    async def approve(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Approve an approval request.

        Args:
            request_id: ID of the request
            decided_by: Who is making the decision
            reason: Optional reason

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or not pending
        """
        request = await self._store.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        request.approve(decided_by, reason)
        await self._store.update(request)

        if self._on_approved:
            await self._on_approved(request)

        return request

    async def reject(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Reject an approval request.

        Args:
            request_id: ID of the request
            decided_by: Who is making the decision
            reason: Optional reason

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or not pending
        """
        request = await self._store.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        request.reject(decided_by, reason)
        await self._store.update(request)

        if self._on_rejected:
            await self._on_rejected(request)

        return request

    async def revoke(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Revoke a previously approved request.

        Args:
            request_id: ID of the request
            decided_by: Who is making the decision
            reason: Optional reason

        Returns:
            Updated ApprovalRequest
        """
        request = await self._store.get(request_id)
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")

        request.revoke(decided_by, reason)
        await self._store.update(request)

        return request

    async def list_pending(
        self,
        *,
        approver_role: str | None = None,
        approver_email: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """List pending approval requests."""
        return await self._store.list_pending(
            approver_role=approver_role,
            approver_email=approver_email,
            tenant_id=tenant_id,
            limit=limit,
        )

    async def list_by_execution(self, execution_id: str) -> list[ApprovalRequest]:
        """List approval requests for an execution."""
        return await self._store.list_by_execution(execution_id)

    async def list_by_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        """List approval requests for a workflow."""
        return await self._store.list_by_workflow(workflow_id)

    def set_approved_callback(self, callback: ApprovalCallback) -> None:
        """Set callback for approved requests."""
        self._on_approved = callback

    def set_rejected_callback(self, callback: ApprovalCallback) -> None:
        """Set callback for rejected requests."""
        self._on_rejected = callback
