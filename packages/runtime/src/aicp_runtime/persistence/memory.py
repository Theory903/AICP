"""In-memory runtime persistence implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState

from aicp_runtime.persistence.base import RuntimeStore


class InMemoryRuntimeStore(RuntimeStore):
    """Simple in-memory store for runtime state."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowState] = {}
        self._execution_records: dict[str, dict[str, Any]] = {}
        self._approval_requests: dict[str, dict[str, Any]] = {}
        self._approval_decisions: dict[str, dict[str, Any]] = {}
        self._session_states: dict[str, dict[str, Any]] = {}
        self._interaction_states: dict[str, dict[str, Any]] = {}
        self._audit_entries: list[dict[str, Any]] = []

    async def save_workflow(self, workflow: WorkflowState) -> None:
        self._workflows[workflow.id] = workflow.model_copy(deep=True)

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        workflow = self._workflows.get(workflow_id)
        return workflow.model_copy(deep=True) if workflow is not None else None

    async def list_workflows(self) -> list[WorkflowState]:
        return [
            workflow.model_copy(deep=True)
            for _, workflow in sorted(self._workflows.items(), key=lambda item: item[0])
        ]

    async def save_execution_record(
        self, execution_id: str, record: dict[str, Any]
    ) -> None:
        self._execution_records[self._require_id(execution_id, "execution_id")] = (
            deepcopy(record)
        )

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        record = self._execution_records.get(execution_id)
        return deepcopy(record) if record is not None else None

    async def list_execution_records(self) -> list[dict[str, Any]]:
        return [
            deepcopy(record)
            for _, record in sorted(
                self._execution_records.items(), key=lambda item: item[0], reverse=True
            )
        ]

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        request_id = self._require_record_id(request, record_name="approval request")
        self._approval_requests[request_id] = deepcopy(request)

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        request = self._approval_requests.get(approval_id)
        return deepcopy(request) if request is not None else None

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return [
            deepcopy(request)
            for _, request in sorted(
                self._approval_requests.items(), key=lambda item: item[0]
            )
        ]

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        decision_id = self._require_record_id(decision, record_name="approval decision")
        self._approval_decisions[decision_id] = deepcopy(decision)

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        decision = self._approval_decisions.get(decision_id)
        return deepcopy(decision) if decision is not None else None

    async def save_session_state(self, session: dict[str, Any]) -> None:
        session_id = self._require_record_id(session, record_name="session state")
        self._session_states[session_id] = deepcopy(session)

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        session = self._session_states.get(session_id)
        return deepcopy(session) if session is not None else None

    async def list_session_states(self) -> list[dict[str, Any]]:
        return [
            deepcopy(session)
            for _, session in sorted(
                self._session_states.items(), key=lambda item: item[0]
            )
        ]

    async def delete_session_state(self, session_id: str) -> None:
        self._session_states.pop(self._require_id(session_id, "session_id"), None)

    async def save_interaction_state(self, interaction: dict[str, Any]) -> None:
        interaction_id = self._require_record_id(
            interaction,
            record_name="interaction state",
        )
        self._interaction_states[interaction_id] = deepcopy(interaction)

    async def get_interaction_state(self, interaction_id: str) -> dict[str, Any] | None:
        interaction = self._interaction_states.get(interaction_id)
        return deepcopy(interaction) if interaction is not None else None

    async def list_interaction_states(self) -> list[dict[str, Any]]:
        return [
            deepcopy(interaction)
            for _, interaction in sorted(
                self._interaction_states.items(), key=lambda item: item[0]
            )
        ]

    async def delete_interaction_state(self, interaction_id: str) -> None:
        self._interaction_states.pop(
            self._require_id(interaction_id, "interaction_id"),
            None,
        )

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        self._audit_entries.append(deepcopy(entry))

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        return [deepcopy(entry) for entry in self._audit_entries]

    def _require_id(self, value: str, field_name: str) -> str:
        """Validate a direct identifier argument."""
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _require_record_id(self, payload: dict[str, Any], *, record_name: str) -> str:
        """Extract and validate an 'id' field from a record payload."""
        record_id = payload.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{record_name} must contain a non-empty string 'id'")
        return record_id.strip()
