"""Persistence interfaces for the runtime package."""

from abc import ABC, abstractmethod
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState


class RuntimeStore(ABC):
    """Storage contract for runtime state."""

    @abstractmethod
    async def save_workflow(self, workflow: WorkflowState) -> None:
        """Persist workflow state."""

    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Load workflow state by ID."""

    @abstractmethod
    async def list_workflows(self) -> list[WorkflowState]:
        """List all workflow states."""

    @abstractmethod
    async def save_execution_record(self, execution_id: str, record: dict[str, Any]) -> None:
        """Persist execution record."""

    @abstractmethod
    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        """Load execution record by ID."""

    @abstractmethod
    async def save_approval_request(self, request: dict[str, Any]) -> None:
        """Persist approval request."""

    @abstractmethod
    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        """Load approval request by ID."""

    @abstractmethod
    async def list_approval_requests(self) -> list[dict[str, Any]]:
        """List approval requests."""

    @abstractmethod
    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        """Persist approval decision."""

    @abstractmethod
    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        """Load approval decision by ID."""

    @abstractmethod
    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        """Append immutable audit entry."""

    @abstractmethod
    async def list_audit_entries(self) -> list[dict[str, Any]]:
        """List audit entries."""
