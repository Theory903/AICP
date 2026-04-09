"""Approval service for managing approval requests.

This module provides:
- an abstract approval store interface
- a concurrency-safe in-memory implementation
- a robust approval service with validation, transitions, and callback dispatch

Design rules:
- persist state before side effects
- keep approval state authoritative
- never hide invalid state transitions
- avoid capability-specific hacks here
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from aicp.approval import ApprovalContext, ApprovalRequest, calculate_risk

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ApprovalServiceError(Exception):
    """Base error for approval service failures."""


class ApprovalNotFoundError(ApprovalServiceError):
    """Raised when an approval request cannot be found."""


class ApprovalValidationError(ApprovalServiceError):
    """Raised when approval input is invalid."""


class ApprovalCallbackError(ApprovalServiceError):
    """Raised when a callback fails after the approval state was persisted."""

    def __init__(self, message: str, *, request_id: str, cause: Exception) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.cause = cause


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


ApprovalCallback = Callable[[ApprovalRequest], Awaitable[ApprovalRequest | None]]
CallbackErrorHandler = Callable[[ApprovalRequest, Exception], Awaitable[None] | None]


# ---------------------------------------------------------------------------
# Store interface
# ---------------------------------------------------------------------------


class ApprovalStore(ABC):
    """Abstract store for approval requests."""

    @abstractmethod
    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        """Store a new approval request."""

    @abstractmethod
    async def get(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""

    @abstractmethod
    async def update(self, request: ApprovalRequest) -> ApprovalRequest:
        """Update an approval request."""

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

    @abstractmethod
    async def list_by_execution(self, execution_id: str) -> list[ApprovalRequest]:
        """List approval requests for an execution."""

    @abstractmethod
    async def list_by_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        """List approval requests for a workflow."""

    @abstractmethod
    async def list_all(self, *, limit: int = 100) -> list[ApprovalRequest]:
        """List all approval requests."""


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------


class InMemoryApprovalStore(ApprovalStore):
    """Concurrency-safe in-memory implementation of ApprovalStore."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._lock = asyncio.Lock()

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        async with self._lock:
            if request.id in self._requests:
                raise ApprovalValidationError(f"Approval request already exists: {request.id}")
            self._requests[request.id] = request
            return request

    async def get(self, request_id: str) -> ApprovalRequest | None:
        self._validate_request_id(request_id)
        async with self._lock:
            return self._requests.get(request_id)

    async def update(self, request: ApprovalRequest) -> ApprovalRequest:
        async with self._lock:
            if request.id not in self._requests:
                raise ApprovalNotFoundError(f"Approval request not found for update: {request.id}")
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
        self._validate_limit(limit)

        async with self._lock:
            results: list[ApprovalRequest] = []
            for request in self._requests.values():
                if not request.is_pending:
                    continue
                if approver_role and request.approver_role != approver_role:
                    continue
                if approver_email and request.approver_email != approver_email:
                    continue
                if tenant_id and request.requester and request.requester.tenant_id != tenant_id:
                    continue
                results.append(request)

            results.sort(key=lambda r: getattr(r, "created_at", None) or "")
            return results[:limit]

    async def list_by_execution(self, execution_id: str) -> list[ApprovalRequest]:
        if not execution_id.strip():
            raise ApprovalValidationError("execution_id cannot be empty")

        async with self._lock:
            results = [request for request in self._requests.values() if request.execution_id == execution_id]
            results.sort(key=lambda r: getattr(r, "created_at", None) or "")
            return results

    async def list_by_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        if not workflow_id.strip():
            raise ApprovalValidationError("workflow_id cannot be empty")

        async with self._lock:
            results = [request for request in self._requests.values() if request.workflow_id == workflow_id]
            results.sort(key=lambda r: getattr(r, "created_at", None) or "")
            return results

    async def list_all(self, *, limit: int = 100) -> list[ApprovalRequest]:
        self._validate_limit(limit)
        async with self._lock:
            results = list(self._requests.values())
            results.sort(key=lambda r: getattr(r, "created_at", None) or "")
            return results[:limit]

    @staticmethod
    def _validate_request_id(request_id: str) -> None:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ApprovalValidationError("request_id must be a non-empty string")

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if limit <= 0:
            raise ApprovalValidationError("limit must be greater than 0")


# ---------------------------------------------------------------------------
# Approval service
# ---------------------------------------------------------------------------


class ApprovalService:
    """Service for managing approval requests.

    Responsibilities:
    1. create approval requests
    2. persist state transitions
    3. dispatch callbacks after persistence
    4. expose filtered listing helpers

    Important:
    - state persistence happens before callback dispatch
    - callback failures do not roll back persisted approval state
    """

    def __init__(
        self,
        store: ApprovalStore | None = None,
        on_approved: ApprovalCallback | None = None,
        on_rejected: ApprovalCallback | None = None,
        risk_thresholds: dict[str, Any] | None = None,
        on_callback_error: CallbackErrorHandler | None = None,
        raise_on_callback_error: bool = False,
    ) -> None:
        self._store = store or InMemoryApprovalStore()
        self._on_approved = on_approved
        self._on_rejected = on_rejected
        self._risk_thresholds = dict(risk_thresholds or {})
        self._on_callback_error = on_callback_error
        self._raise_on_callback_error = raise_on_callback_error

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
        """Create and persist a new approval request."""
        self._validate_capability_name(capability_name)
        self._validate_arguments(arguments)
        self._validate_expiry(expires_in_seconds)

        thresholds = risk_thresholds or self._risk_thresholds
        risk = calculate_risk(capability_name, arguments, thresholds)

        resolved_approver_role, resolved_approver_email = self._resolve_approver(
            risk=risk,
            approver_role=approver_role,
            approver_email=approver_email,
        )

        request = ApprovalRequest.create(
            capability_name=capability_name,
            arguments=arguments,
            approver_role=resolved_approver_role,
            approver_email=resolved_approver_email,
            requester=requester or ApprovalContext(),
            risk=risk,
            expires_in_seconds=expires_in_seconds,
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

        return await self._store.create(request)

    async def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get an approval request by ID."""
        return await self._store.get(request_id)

    async def require_request(self, request_id: str) -> ApprovalRequest:
        """Get an approval request or raise."""
        request = await self._store.get(request_id)
        if request is None:
            raise ApprovalNotFoundError(f"Approval request not found: {request_id}")
        return request

    async def approve(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Approve an approval request."""
        return await self._transition(
            request_id=request_id,
            action="approve",
            decided_by=decided_by,
            reason=reason,
            callback=self._on_approved,
        )

    async def reject(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Reject an approval request."""
        return await self._transition(
            request_id=request_id,
            action="reject",
            decided_by=decided_by,
            reason=reason,
            callback=self._on_rejected,
        )

    async def revoke(
        self,
        request_id: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Revoke a previously approved request."""
        return await self._transition(
            request_id=request_id,
            action="revoke",
            decided_by=decided_by,
            reason=reason,
            callback=None,
        )

    async def decide(
        self,
        request_id: str,
        decision: str,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Apply a decision using a single entry point."""
        normalized = decision.strip().lower()
        if normalized == "approved":
            return await self.approve(request_id, decided_by, reason)
        if normalized == "rejected":
            return await self.reject(request_id, decided_by, reason)
        if normalized == "revoked":
            return await self.revoke(request_id, decided_by, reason)

        raise ApprovalValidationError("decision must be one of: approved, rejected, revoked")

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

    async def list_all(self, *, limit: int = 100) -> list[ApprovalRequest]:
        """List all approval requests."""
        return await self._store.list_all(limit=limit)

    def set_approved_callback(self, callback: ApprovalCallback | None) -> None:
        """Set or clear callback for approved requests."""
        self._on_approved = callback

    def set_rejected_callback(self, callback: ApprovalCallback | None) -> None:
        """Set or clear callback for rejected requests."""
        self._on_rejected = callback

    def set_callback_error_handler(
        self,
        handler: CallbackErrorHandler | None,
    ) -> None:
        """Set or clear callback error handler."""
        self._on_callback_error = handler

    async def _transition(
        self,
        *,
        request_id: str,
        action: str,
        decided_by: str,
        reason: str | None,
        callback: ApprovalCallback | None,
    ) -> ApprovalRequest:
        """Apply a state transition, persist it, then dispatch callback."""
        if not isinstance(decided_by, str) or not decided_by.strip():
            raise ApprovalValidationError("decided_by must be a non-empty string")

        request = await self.require_request(request_id)

        try:
            if action == "approve":
                request.approve(decided_by, reason)
            elif action == "reject":
                request.reject(decided_by, reason)
            elif action == "revoke":
                request.revoke(decided_by, reason)
            else:
                raise ApprovalValidationError(f"Unsupported action: {action}")
        except Exception as exc:
            raise ApprovalValidationError(
                f"Invalid approval transition '{action}' for request {request_id}: {exc}"
            ) from exc

        updated = await self._store.update(request)

        if callback is not None:
            await self._dispatch_callback(updated, callback)

        return updated

    async def _dispatch_callback(
        self,
        request: ApprovalRequest,
        callback: ApprovalCallback,
    ) -> None:
        """Dispatch a callback after state is already persisted."""
        try:
            await callback(request)
        except Exception as exc:
            if self._on_callback_error is not None:
                maybe_awaitable = self._on_callback_error(request, exc)
                if maybe_awaitable is not None and hasattr(maybe_awaitable, "__await__"):
                    await maybe_awaitable

            if self._raise_on_callback_error:
                raise ApprovalCallbackError(
                    f"Callback failed for approval request {request.id}",
                    request_id=request.id,
                    cause=exc,
                ) from exc

    def _resolve_approver(
        self,
        *,
        risk: Any,
        approver_role: str | None,
        approver_email: str | None,
    ) -> tuple[str | None, str | None]:
        """Resolve default approver info from risk if none is supplied."""
        if approver_role is not None or approver_email is not None:
            return approver_role, approver_email

        level = self._risk_level_value(risk)
        if level == "critical":
            return "admin", None
        if level == "high":
            return "admin", None
        if level == "medium":
            return "manager", None
        return None, None

    @staticmethod
    def _risk_level_value(risk: Any) -> str:
        """Normalize risk level whether it is string-like or enum-like."""
        level = getattr(risk, "level", None)
        if level is None:
            return "low"
        if hasattr(level, "value"):
            return str(level.value).lower()
        return str(level).lower()

    @staticmethod
    def _validate_capability_name(capability_name: str) -> None:
        if not isinstance(capability_name, str) or not capability_name.strip():
            raise ApprovalValidationError("capability_name must be a non-empty string")

    @staticmethod
    def _validate_arguments(arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ApprovalValidationError("arguments must be a dictionary")

    @staticmethod
    def _validate_expiry(expires_in_seconds: int) -> None:
        if not isinstance(expires_in_seconds, int) or expires_in_seconds <= 0:
            raise ApprovalValidationError("expires_in_seconds must be a positive integer")
