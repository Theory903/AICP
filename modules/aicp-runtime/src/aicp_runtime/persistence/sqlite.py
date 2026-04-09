"""SQLite-backed runtime persistence implementation."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState

from aicp_runtime.persistence.base import RuntimeStore

_ALLOWED_TABLES = {
    "workflows",
    "executions",
    "approval_requests",
    "approval_decisions",
    "session_states",
    "interaction_states",
    "audit_entries",
}


class SqliteRuntimeStore(RuntimeStore):
    """Persist runtime state in a local SQLite database."""

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path).resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    async def save_workflow(self, workflow: WorkflowState) -> None:
        self._upsert("workflows", workflow.id, workflow.model_dump(mode="json"))

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        payload = self._get_payload("workflows", workflow_id)
        if payload is None:
            return None
        return WorkflowState(**payload)

    async def list_workflows(self) -> list[WorkflowState]:
        rows = self._list_payloads("workflows")
        workflows: list[WorkflowState] = []
        for row in rows:
            try:
                workflows.append(WorkflowState(**row))
            except Exception:
                continue
        return workflows

    async def save_execution_record(
        self, execution_id: str, record: dict[str, Any]
    ) -> None:
        self._upsert("executions", execution_id, record)

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        return self._get_payload("executions", execution_id)

    async def list_execution_records(self) -> list[dict[str, Any]]:
        return self._list_payloads("executions")

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        request_id = self._require_record_id(request, record_name="approval request")
        self._upsert("approval_requests", request_id, request)

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._get_payload("approval_requests", approval_id)

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return self._list_payloads("approval_requests")

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        decision_id = self._require_record_id(decision, record_name="approval decision")
        self._upsert("approval_decisions", decision_id, decision)

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._get_payload("approval_decisions", decision_id)

    async def save_session_state(self, session: dict[str, Any]) -> None:
        session_id = self._require_record_id(session, record_name="session state")
        self._upsert("session_states", session_id, session)

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        return self._get_payload("session_states", session_id)

    async def list_session_states(self) -> list[dict[str, Any]]:
        return self._list_payloads("session_states")

    async def delete_session_state(self, session_id: str) -> None:
        session_id = self._require_id(session_id, field_name="session_id")
        with self._connect() as connection:
            connection.execute("DELETE FROM session_states WHERE id = ?", (session_id,))
            connection.commit()

    async def save_interaction_state(self, interaction: dict[str, Any]) -> None:
        interaction_id = self._require_record_id(
            interaction,
            record_name="interaction state",
        )
        self._upsert("interaction_states", interaction_id, interaction)

    async def get_interaction_state(self, interaction_id: str) -> dict[str, Any] | None:
        return self._get_payload("interaction_states", interaction_id)

    async def list_interaction_states(self) -> list[dict[str, Any]]:
        return self._list_payloads("interaction_states")

    async def delete_interaction_state(self, interaction_id: str) -> None:
        interaction_id = self._require_id(interaction_id, field_name="interaction_id")
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM interaction_states WHERE id = ?",
                (interaction_id,),
            )
            connection.commit()

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        audit_id = self._extract_or_create_audit_id(entry)
        self._insert_only("audit_entries", audit_id, entry)

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        return self._list_payloads("audit_entries")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.execute("PRAGMA synchronous=NORMAL;")
        connection.execute("PRAGMA foreign_keys=ON;")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            for table in _ALLOWED_TABLES:
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL
                    )
                    """
                )
            connection.commit()

    def _upsert(self, table: str, record_id: str, payload: dict[str, Any]) -> None:
        table = self._validate_table_name(table)
        record_id = self._require_id(record_id, field_name="record_id")
        serialized = self._serialize_payload(payload)

        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO {table} (id, payload)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                (record_id, serialized),
            )
            connection.commit()

    def _insert_only(self, table: str, record_id: str, payload: dict[str, Any]) -> None:
        table = self._validate_table_name(table)
        record_id = self._require_id(record_id, field_name="record_id")
        serialized = self._serialize_payload(payload)

        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO {table} (id, payload) VALUES (?, ?)",
                (record_id, serialized),
            )
            connection.commit()

    def _get_payload(self, table: str, record_id: str) -> dict[str, Any] | None:
        table = self._validate_table_name(table)
        record_id = self._require_id(record_id, field_name="record_id")

        with self._connect() as connection:
            row = connection.execute(
                f"SELECT payload FROM {table} WHERE id = ?",
                (record_id,),
            ).fetchone()

        if row is None:
            return None

        return self._deserialize_payload(row["payload"])

    def _list_payloads(self, table: str) -> list[dict[str, Any]]:
        table = self._validate_table_name(table)

        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT payload FROM {table} ORDER BY id"
            ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            payload = self._deserialize_payload(row["payload"])
            if payload is not None:
                results.append(payload)
        return results

    def _serialize_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )

    def _deserialize_payload(self, raw_payload: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _validate_table_name(self, table: str) -> str:
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"Unsupported table name: {table}")
        return table

    def _require_id(self, value: str, *, field_name: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _require_record_id(self, payload: dict[str, Any], *, record_name: str) -> str:
        record_id = payload.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{record_name} must contain a non-empty string 'id'")
        return record_id.strip()

    def _extract_or_create_audit_id(self, entry: dict[str, Any]) -> str:
        existing = entry.get("id")
        if isinstance(existing, str) and existing.strip():
            return existing.strip()
        generated = f"audit_{uuid.uuid4().hex}"
        entry["id"] = generated
        return generated
