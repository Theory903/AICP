"""In-memory runtime persistence implementation."""

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
        self._audit_entries: list[dict[str, Any]] = []

    async def save_workflow(self, workflow: WorkflowState) -> None:
        self._workflows[workflow.id] = workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        return self._workflows.get(workflow_id)

    async def list_workflows(self) -> list[WorkflowState]:
        return list(self._workflows.values())

    async def save_execution_record(self, execution_id: str, record: dict[str, Any]) -> None:
        self._execution_records[execution_id] = record

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        return self._execution_records.get(execution_id)

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        self._approval_requests[request["id"]] = request

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._approval_requests.get(approval_id)

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return list(self._approval_requests.values())

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        self._approval_decisions[decision["id"]] = decision

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._approval_decisions.get(decision_id)

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        self._audit_entries.append(entry)

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        return list(self._audit_entries)
