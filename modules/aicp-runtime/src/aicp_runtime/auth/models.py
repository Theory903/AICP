"""Session and auth state models for runtime-backed execution."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionCookie(BaseModel):
    """Serializable HTTP cookie artifact."""

    model_config = ConfigDict(extra="allow")

    name: str
    value: str
    domain: str | None = None
    path: str | None = "/"
    secure: bool = False
    http_only: bool = False

    @field_validator("name", "value", "domain", "path", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class SessionAuthRecipe(BaseModel):
    """Declarative auth/session attachment recipe."""

    model_config = ConfigDict(extra="allow")

    kind: str
    header_name: str | None = None
    token_field: str | None = None
    csrf_header_name: str | None = None
    csrf_token_field: str | None = None
    org_header_name: str | None = None
    org_context_field: str | None = None
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: list[str] = Field(default_factory=list)
    audience: str | None = None
    extra_payload: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "kind",
        "header_name",
        "token_field",
        "csrf_header_name",
        "csrf_token_field",
        "org_header_name",
        "org_context_field",
        "token_url",
        "client_id",
        "client_secret",
        "audience",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("extra_payload", mode="before")
    @classmethod
    def _normalize_payload_map(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("must be an object")
        normalized: dict[str, str] = {}
        for key, item in value.items():
            key_text = str(key).strip()
            item_text = str(item).strip()
            if key_text and item_text:
                normalized[key_text] = item_text
        return normalized


class SessionState(BaseModel):
    """First-class runtime session state for UI-less agent execution."""

    model_config = ConfigDict(extra="allow")

    id: str
    provider_name: str
    auth_mode: str
    cookies: list[SessionCookie] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    tokens: dict[str, str] = Field(default_factory=dict)
    csrf_tokens: dict[str, str] = Field(default_factory=dict)
    auth_recipe: SessionAuthRecipe | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    selected_context: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    last_used_at: str | None = None
    expires_at: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    refreshable: bool = False
    revoked_at: str | None = None
    health_status: str | None = None
    requires_reauth: bool = False

    @field_validator(
        "id",
        "provider_name",
        "auth_mode",
        "created_at",
        "updated_at",
        "last_used_at",
        "expires_at",
        "tenant_id",
        "user_id",
        "revoked_at",
        "health_status",
        mode="before",
    )
    @classmethod
    def _normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("headers", "tokens", "csrf_tokens", mode="before")
    @classmethod
    def _normalize_text_map(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("must be an object")
        normalized: dict[str, str] = {}
        for key, item in value.items():
            key_text = str(key).strip()
            item_text = str(item).strip()
            if key_text and item_text:
                normalized[key_text] = item_text
        return normalized
