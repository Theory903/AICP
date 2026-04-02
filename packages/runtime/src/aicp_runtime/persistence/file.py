"""File-backed runtime persistence implementation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState

from aicp_runtime.persistence.base import RuntimeStore


class FileRuntimeStore(RuntimeStore):
    """Persist runtime state to JSON files on disk."""

    def __init__(self, root: str | Path):
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

        self._workflows_dir = self._root / "workflows"
        self._executions_dir = self._root / "executions"
        self._approvals_dir = self._root / "approvals"
        self._decisions_dir = self._root / "decisions"
        self._sessions_dir = self._root / "sessions"
        self._interactions_dir = self._root / "interactions"
        self._audit_file = self._root / "audit.jsonl"

        for directory in (
            self._workflows_dir,
            self._executions_dir,
            self._approvals_dir,
            self._decisions_dir,
            self._sessions_dir,
            self._interactions_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    async def save_workflow(self, workflow: WorkflowState) -> None:
        self._write_json_file(
            self._workflows_dir / f"{self._safe_id(workflow.id)}.json",
            workflow.model_dump(mode="json"),
        )

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        data = self._read_json_file(
            self._workflows_dir / f"{self._safe_id(workflow_id)}.json"
        )
        if data is None:
            return None
        return WorkflowState(**data)

    async def list_workflows(self) -> list[WorkflowState]:
        workflows: list[WorkflowState] = []
        for path in sorted(self._workflows_dir.glob("*.json")):
            data = self._read_json_file(path)
            if data is None:
                continue
            try:
                workflows.append(WorkflowState(**data))
            except Exception:
                continue
        return workflows

    async def save_execution_record(
        self, execution_id: str, record: dict[str, Any]
    ) -> None:
        self._write_json_file(
            self._executions_dir / f"{self._safe_id(execution_id)}.json",
            record,
        )

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        return self._read_json_file(
            self._executions_dir / f"{self._safe_id(execution_id)}.json"
        )

    async def list_execution_records(self) -> list[dict[str, Any]]:
        return self._list_json_objects(self._executions_dir)

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        request_id = self._require_record_id(request, record_name="approval request")
        self._write_json_file(
            self._approvals_dir / f"{self._safe_id(request_id)}.json",
            request,
        )

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._read_json_file(
            self._approvals_dir / f"{self._safe_id(approval_id)}.json"
        )

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return self._list_json_objects(self._approvals_dir)

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        decision_id = self._require_record_id(decision, record_name="approval decision")
        self._write_json_file(
            self._decisions_dir / f"{self._safe_id(decision_id)}.json",
            decision,
        )

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._read_json_file(
            self._decisions_dir / f"{self._safe_id(decision_id)}.json"
        )

    async def save_session_state(self, session: dict[str, Any]) -> None:
        session_id = self._require_record_id(session, record_name="session state")
        self._write_json_file(
            self._sessions_dir / f"{self._safe_id(session_id)}.json",
            session,
        )

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        return self._read_json_file(
            self._sessions_dir / f"{self._safe_id(session_id)}.json"
        )

    async def list_session_states(self) -> list[dict[str, Any]]:
        return self._list_json_objects(self._sessions_dir)

    async def delete_session_state(self, session_id: str) -> None:
        path = self._sessions_dir / f"{self._safe_id(session_id)}.json"
        path.unlink(missing_ok=True)

    async def save_interaction_state(self, interaction: dict[str, Any]) -> None:
        interaction_id = self._require_record_id(
            interaction,
            record_name="interaction state",
        )
        self._write_json_file(
            self._interactions_dir / f"{self._safe_id(interaction_id)}.json",
            interaction,
        )

    async def get_interaction_state(self, interaction_id: str) -> dict[str, Any] | None:
        return self._read_json_file(
            self._interactions_dir / f"{self._safe_id(interaction_id)}.json"
        )

    async def list_interaction_states(self) -> list[dict[str, Any]]:
        return self._list_json_objects(self._interactions_dir)

    async def delete_interaction_state(self, interaction_id: str) -> None:
        path = self._interactions_dir / f"{self._safe_id(interaction_id)}.json"
        path.unlink(missing_ok=True)

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        with self._audit_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        if not self._audit_file.exists():
            return []

        entries: list[dict[str, Any]] = []
        with self._audit_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    entries.append(parsed)
        return entries

    def _list_json_objects(self, directory: Path) -> list[dict[str, Any]]:
        """List valid JSON object files from a directory."""
        results: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            data = self._read_json_file(path)
            if isinstance(data, dict):
                results.append(data)
        return results

    def _write_json_file(self, path: Path, payload: dict[str, Any]) -> None:
        """Write JSON atomically to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        ) as tmp:
            tmp.write(serialized)
            tmp.write("\n")
            tmp_path = Path(tmp.name)

        try:
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def _read_json_file(self, path: Path) -> dict[str, Any] | None:
        """Read a JSON object file safely."""
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

        return data if isinstance(data, dict) else None

    def _require_record_id(self, payload: dict[str, Any], *, record_name: str) -> str:
        """Extract and validate an id field from a record payload."""
        record_id = payload.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{record_name} must contain a non-empty string 'id'")
        return record_id.strip()

    def _safe_id(self, value: str) -> str:
        """Convert record identifiers into filesystem-safe names."""
        value = value.strip()
        if not value:
            raise ValueError("Identifier cannot be empty")

        # Avoid path traversal and other filesystem nonsense.
        safe = "".join(
            ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value
        )
        safe = safe.strip("._")
        if not safe:
            raise ValueError("Identifier is not filesystem-safe")
        return safe
