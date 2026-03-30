"""File-backed runtime persistence implementation."""

import json
from pathlib import Path
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState

from aicp_runtime.persistence.base import RuntimeStore


class FileRuntimeStore(RuntimeStore):
    """Persist runtime state to JSON files on disk."""

    def __init__(self, root: str | Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._workflows_dir = self._root / "workflows"
        self._executions_dir = self._root / "executions"
        self._approvals_dir = self._root / "approvals"
        self._decisions_dir = self._root / "decisions"
        self._audit_file = self._root / "audit.jsonl"

        for directory in (
            self._workflows_dir,
            self._executions_dir,
            self._approvals_dir,
            self._decisions_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    async def save_workflow(self, workflow: WorkflowState) -> None:
        self._write_json(self._workflows_dir / f"{workflow.id}.json", workflow.model_dump(mode="json"))

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        data = self._read_json(self._workflows_dir / f"{workflow_id}.json")
        if data is None:
            return None
        return WorkflowState(**data)

    async def list_workflows(self) -> list[WorkflowState]:
        return [WorkflowState(**json.loads(path.read_text())) for path in sorted(self._workflows_dir.glob("*.json"))]

    async def save_execution_record(self, execution_id: str, record: dict[str, Any]) -> None:
        self._write_json(self._executions_dir / f"{execution_id}.json", record)

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        return self._read_json(self._executions_dir / f"{execution_id}.json")

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        self._write_json(self._approvals_dir / f"{request['id']}.json", request)

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._read_json(self._approvals_dir / f"{approval_id}.json")

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text()) for path in sorted(self._approvals_dir.glob("*.json"))]

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        self._write_json(self._decisions_dir / f"{decision['id']}.json", decision)

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._read_json(self._decisions_dir / f"{decision_id}.json")

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        with open(self._audit_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        if not self._audit_file.exists():
            return []
        with open(self._audit_file, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
