"""Audit service for immutable runtime journal entries."""

from __future__ import annotations

import uuid
from copy import deepcopy
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
        """Append an immutable audit entry."""
        event_type = self._require_text(event_type, field_name="event_type")
        actor = self._require_text(actor, field_name="actor")

        entry = {
            "id": f"audit_{uuid.uuid4().hex[:8]}",
            "timestamp": utc_now_rfc3339(),
            "event_type": event_type,
            "actor": actor,
            **{
                key: deepcopy(value)
                for key, value in fields.items()
                if value is not None
            },
        }

        await self._store.append_audit_entry(entry)
        return deepcopy(entry)

    async def list_entries(
        self,
        workflow_id: str | None = None,
        capability_name: str | None = None,
        approval_request_id: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List audit entries with optional in-memory filtering."""
        workflow_id = self._normalize_optional_text(workflow_id)
        capability_name = self._normalize_optional_text(capability_name)
        approval_request_id = self._normalize_optional_text(approval_request_id)
        event_type = self._normalize_optional_text(event_type)
        status = self._normalize_optional_text(status)

        entries = await self._store.list_audit_entries()

        if workflow_id is not None:
            entries = [
                entry for entry in entries if entry.get("workflow_id") == workflow_id
            ]

        if capability_name is not None:
            entries = [
                entry
                for entry in entries
                if entry.get("capability_name") == capability_name
            ]

        if approval_request_id is not None:
            entries = [
                entry
                for entry in entries
                if entry.get("approval_request_id") == approval_request_id
            ]

        if event_type is not None:
            entries = [
                entry for entry in entries if entry.get("event_type") == event_type
            ]

        if status is not None:
            entries = [entry for entry in entries if entry.get("status") == status]

        entries.sort(key=lambda entry: str(entry.get("timestamp", "")))
        return [deepcopy(entry) for entry in entries]

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        """Require a non-empty text value."""
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        """Normalize optional text to stripped string or None."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
