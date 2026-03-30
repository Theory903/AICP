"""SQLite-backed runtime persistence implementation."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from aicp.interfaces.workflow_runtime import WorkflowState

from aicp_runtime.persistence.base import RuntimeStore


class SqliteRuntimeStore(RuntimeStore):
    """Persist runtime state in a local SQLite database."""

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
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
        return [WorkflowState(**row) for row in rows]

    async def save_execution_record(self, execution_id: str, record: dict[str, Any]) -> None:
        self._upsert("executions", execution_id, record)

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        return self._get_payload("executions", execution_id)

    async def save_approval_request(self, request: dict[str, Any]) -> None:
        self._upsert("approval_requests", request["id"], request)

    async def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._get_payload("approval_requests", approval_id)

    async def list_approval_requests(self) -> list[dict[str, Any]]:
        return self._list_payloads("approval_requests")

    async def save_approval_decision(self, decision: dict[str, Any]) -> None:
        self._upsert("approval_decisions", decision["id"], decision)

    async def get_approval_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._get_payload("approval_decisions", decision_id)

    async def append_audit_entry(self, entry: dict[str, Any]) -> None:
        self._upsert("audit_entries", entry["id"], entry)

    async def list_audit_entries(self) -> list[dict[str, Any]]:
        return self._list_payloads("audit_entries")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            for table in (
                "workflows",
                "executions",
                "approval_requests",
                "approval_decisions",
                "audit_entries",
            ):
                connection.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
                )
            connection.commit()

    def _upsert(self, table: str, record_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO {table} (id, payload) VALUES (?, ?) "
                f"ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (record_id, json.dumps(payload, sort_keys=True)),
            )
            connection.commit()

    def _get_payload(self, table: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT payload FROM {table} WHERE id = ?",
                (record_id,),
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def _list_payloads(self, table: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()
        return [json.loads(row["payload"]) for row in rows]
