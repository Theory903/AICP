"""Interaction state models for AI-facing runtime memory."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentInteractionState(BaseModel):
    """Durable interaction state separate from auth sessions."""

    model_config = ConfigDict(extra="allow")

    id: str
    session_id: str | None = None
    selected_context: dict[str, Any] = Field(default_factory=dict)
    resource_cache: dict[str, Any] = Field(default_factory=dict)
    pending_forms: dict[str, Any] = Field(default_factory=dict)
    pagination_state: dict[str, Any] = Field(default_factory=dict)
    upload_state: dict[str, Any] = Field(default_factory=dict)
    last_capability: str | None = None
    last_result_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str

    @field_validator(
        "id", "session_id", "last_capability", "created_at", "updated_at", mode="before"
    )
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
