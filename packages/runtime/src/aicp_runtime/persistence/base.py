"""Persistence interfaces for the runtime package."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState


class RuntimeStore(ABC):
    """Storage contract for runtime state.

    Implementations may be in-memory, file-backed, or database-backed.
    Mutable records should overwrite by ID where appropriate.
    Audit entries are append-only.
    """

    @abstractmethod
    async def save_workflow(self, workflow: WorkflowState) -> None:
        """Persist workflow state."""

    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Load workflow state by ID."""

    @abstractmethod
    async def list_workflows(self) -> list[WorkflowState]:
        """List all workflow states.

        Returns:
            A list of workflows. Ordering should be stable and documented
            by the implementation.
        """

    @abstractmethod
    async def save_execution_record(self, execution_id: str, record: dict[str, Any]) -> None:
        """Persist an execution record."""

    @abstractmethod
    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        """Load execution record by ID."""

    @abstractmethod
    async def list_execution_records(self) -> list[dict[str, Any]]:
        """List persisted execution records."""

    @abstractmethod
    async def save_approval_request(self, request: dict[str, Any]) -> None:
        """Persist an approval request."""

    @abstractmethod
    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        """Load approval request by ID."""

    @abstractmethod
    async def list_approval_requests(self) -> list[dict[str, Any]]:
        """List approval requests."""

    @abstractmethod
    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        """Persist an approval decision."""

    @abstractmethod
    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        """Load approval decision by ID."""

    @abstractmethod
    async def save_session_state(self, session: dict[str, Any]) -> None:
        """Persist a session state."""

    @abstractmethod
    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """Load session state by ID."""

    @abstractmethod
    async def list_session_states(self) -> list[dict[str, Any]]:
        """List all persisted session states."""

    @abstractmethod
    async def delete_session_state(self, session_id: str) -> None:
        """Delete a session state by ID."""

    @abstractmethod
    async def save_interaction_state(self, interaction: dict[str, Any]) -> None:
        """Persist an interaction state."""

    @abstractmethod
    async def get_interaction_state(self, interaction_id: str) -> dict[str, Any] | None:
        """Load interaction state by ID."""

    @abstractmethod
    async def list_interaction_states(self) -> list[dict[str, Any]]:
        """List all interaction states."""

    @abstractmethod
    async def delete_interaction_state(self, interaction_id: str) -> None:
        """Delete an interaction state by ID."""

    @abstractmethod
    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        """Append an immutable audit entry."""

    @abstractmethod
    async def list_audit_entries(self) -> list[dict[str, Any]]:
        """List audit entries."""

    async def close(self) -> None:
        """Release store resources if needed.

        Default implementation is a no-op for stores that do not hold
        external resources.
        """
        return None
