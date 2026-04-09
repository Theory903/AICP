"""Interaction state service for frontend-like AI runtime memory."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.interactions.models import AgentInteractionState
from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.audit import AuditService


class InteractionStateService:
    """Manage durable interaction state for agent sessions."""

    def __init__(
        self,
        runtime_store: RuntimeStore,
        audit_service: AuditService | None = None,
    ) -> None:
        self._store = runtime_store
        self._audit = audit_service

    async def create_interaction(
        self,
        *,
        session_id: str | None = None,
        selected_context: dict[str, Any] | None = None,
        resource_cache: dict[str, Any] | None = None,
        pending_forms: dict[str, Any] | None = None,
        pagination_state: dict[str, Any] | None = None,
        upload_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_rfc3339()
        interaction = AgentInteractionState.model_validate(
            {
                "id": f"itr_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "selected_context": selected_context or {},
                "resource_cache": resource_cache or {},
                "pending_forms": pending_forms or {},
                "pagination_state": pagination_state or {},
                "upload_state": upload_state or {},
                "last_result_summary": {},
                "created_at": now,
                "updated_at": now,
            }
        )
        payload = interaction.model_dump(mode="json", exclude_none=True)
        await self._store.save_interaction_state(payload)
        await self._append_audit(
            event_type="interaction_created",
            actor="runtime",
            interaction_id=interaction.id,
            status="success",
            metadata={"session_id": interaction.session_id},
        )
        return payload

    async def get_interaction(self, interaction_id: str) -> dict[str, Any] | None:
        interaction = await self._store.get_interaction_state(
            self._require_text(interaction_id, "interaction_id")
        )
        return deepcopy(interaction) if interaction is not None else None

    async def list_interactions(self) -> list[dict[str, Any]]:
        interactions = await self._store.list_interaction_states()
        interactions.sort(
            key=lambda item: str(item.get("updated_at", "")), reverse=True
        )
        return [deepcopy(item) for item in interactions]

    async def update_interaction(
        self, interaction_id: str, **patch: Any
    ) -> dict[str, Any]:
        normalized = self._require_text(interaction_id, "interaction_id")
        interaction = await self._store.get_interaction_state(normalized)
        if interaction is None:
            raise ValueError(f"Interaction not found: {normalized}")

        for key in (
            "session_id",
            "selected_context",
            "resource_cache",
            "pending_forms",
            "pagination_state",
            "upload_state",
            "last_capability",
            "last_result_summary",
        ):
            if key in patch and patch[key] is not None:
                interaction[key] = deepcopy(patch[key])

        interaction["updated_at"] = utc_now_rfc3339()
        validated = AgentInteractionState.model_validate(interaction)
        payload = validated.model_dump(mode="json", exclude_none=True)
        await self._store.save_interaction_state(payload)
        return payload

    async def delete_interaction(self, interaction_id: str) -> None:
        normalized = self._require_text(interaction_id, "interaction_id")
        await self._store.delete_interaction_state(normalized)
        await self._append_audit(
            event_type="interaction_deleted",
            actor="runtime",
            interaction_id=normalized,
            status="success",
        )

    async def record_execution(
        self,
        interaction_id: str,
        *,
        capability_name: str,
        result_summary: dict[str, Any],
    ) -> dict[str, Any] | None:
        interaction = await self.get_interaction(interaction_id)
        if interaction is None:
            return None
        return await self.update_interaction(
            interaction_id,
            last_capability=capability_name,
            last_result_summary=result_summary,
        )

    async def _append_audit(self, event_type: str, actor: str, **fields: Any) -> None:
        if self._audit is None:
            return
        await self._audit.append(event_type=event_type, actor=actor, **fields)

    def _require_text(self, value: str | None, field_name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized
