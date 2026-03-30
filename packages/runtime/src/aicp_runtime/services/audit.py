"""Audit service for immutable runtime journal entries."""

import uuid
from typing import Any

from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.persistence.base import RuntimeStore


class AuditService:
    """Append-only audit journal service."""

    def __init__(self, runtime_store: RuntimeStore):
        self._store = runtime_store

    async def append(
        self,
        event_type: str,
        actor: str,
        **fields: Any,
    ) -> dict[str, Any]:
        entry = {
            "id": f"audit_{uuid.uuid4().hex[:8]}",
            "timestamp": utc_now_rfc3339(),
            "event_type": event_type,
            "actor": actor,
            **{key: value for key, value in fields.items() if value is not None},
        }
        await self._store.append_audit_entry(entry)
        return entry

    async def list_entries(
        self,
        workflow_id: str | None = None,
        capability_name: str | None = None,
        approval_request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        entries = await self._store.list_audit_entries()
        if workflow_id is not None:
            entries = [entry for entry in entries if entry.get("workflow_id") == workflow_id]
        if capability_name is not None:
            entries = [entry for entry in entries if entry.get("capability_name") == capability_name]
        if approval_request_id is not None:
            entries = [
                entry for entry in entries if entry.get("approval_request_id") == approval_request_id
            ]
        return entries
