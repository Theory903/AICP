"""Capability model.

The core AICP capability definition with rich metadata for AI agents.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CapabilityKind(str, Enum):
    """The kind of capability."""

    QUERY = "query"  # Read-only, no side effects
    ACTION = "action"  # Write operation with side effects
    WORKFLOW = "workflow"  # Multi-step capability
    ASYNC_ACTION = "async_action"  # Long-running action
    BATCH_ACTION = "batch_action"  # Batch operation


class InputSchema(BaseModel):
    """Input schema for a capability."""

    model_config = ConfigDict(extra="allow")

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        return str(value).strip() if value is not None else "object"

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None


class OutputSchema(BaseModel):
    """Output schema for a capability."""

    model_config = ConfigDict(extra="allow")

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        return str(value).strip() if value is not None else "object"

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None


class RenderSpec(BaseModel):
    """Specification for rendering capability results."""

    model_config = ConfigDict(extra="forbid")

    format: str = "text"  # text, json, table, code, image
    fields: list[str] | None = None
    table_columns: list[str] | None = None
    max_length: int | None = Field(default=None, ge=1)
    truncate: bool = True
    syntax: str | None = None

    @field_validator("format", "syntax", mode="before")
    @classmethod
    def _normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("fields", "table_columns", mode="after")
    @classmethod
    def _dedupe_fields(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            item = str(item).strip()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized


class PolicyRef(BaseModel):
    """Reference to a policy for this capability."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_name", mode="before")
    @classmethod
    def _normalize_policy_name(cls, value: Any) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("policy_name cannot be empty")
        return value


class ContinuationSpec(BaseModel):
    """Specification for continuing after execution."""

    model_config = ConfigDict(extra="forbid")

    can_continue: bool = True
    next_capabilities: list[str] = Field(default_factory=list)
    next_hint: str | None = None
    poll_capability: str | None = None
    poll_after_ms: int | None = Field(default=None, ge=0)
    poll_argument: str | None = None

    @field_validator("next_hint", "poll_capability", "poll_argument", mode="before")
    @classmethod
    def _normalize_next_hint(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("next_capabilities", mode="after")
    @classmethod
    def _dedupe_next_capabilities(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            item = str(item).strip()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized


class AuthRequirement(BaseModel):
    """Auth and session requirements for capability execution."""

    model_config = ConfigDict(extra="forbid")

    mode: str
    requires_session: bool = False
    csrf_required: bool = False
    refreshable: bool = False
    required_session_provider: str | None = None
    allowed_scopes: list[str] = Field(default_factory=list)

    @field_validator("mode", "required_session_provider", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("allowed_scopes", mode="after")
    @classmethod
    def _normalize_scopes(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            scope = str(item).strip()
            if scope and scope not in seen:
                seen.add(scope)
                normalized.append(scope)
        return normalized


class ProviderInfo(BaseModel):
    """Information about the capability provider."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: str | None = None
    url: str | None = None

    @field_validator("name", "type", "url", mode="before")
    @classmethod
    def _normalize_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None


class Capability(BaseModel):
    """An AICP capability.

    This is the core unit of AICP: a meaningful action that can be
    discovered, executed, and governed with rich metadata.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    kind: CapabilityKind = CapabilityKind.ACTION

    input_schema: InputSchema = Field(default_factory=InputSchema)
    output_schema: OutputSchema = Field(default_factory=OutputSchema)

    tags: list[str] = Field(default_factory=list)

    # Policy reference
    policy: PolicyRef | None = None

    # Rendering hints
    render: RenderSpec | None = None

    # Continuation hints
    continuation: ContinuationSpec | None = None

    # Graph and relationship hints
    dependency_capabilities: list[str] = Field(default_factory=list)
    often_follows: list[str] = Field(default_factory=list)
    rollback_capability: str | None = None

    # Auth/session requirements
    auth: AuthRequirement | None = None

    # Provider info
    provider: ProviderInfo | None = None

    # Metadata
    output_validation_mode: str | None = None
    version: str | None = None
    deprecated: bool = False
    deprecation_message: str | None = None

    @property
    def is_query(self) -> bool:
        """Return True when the capability is read-oriented."""
        return self.kind == CapabilityKind.QUERY

    @property
    def is_action(self) -> bool:
        """Return True when the capability has action semantics."""
        return self.kind in {
            CapabilityKind.ACTION,
            CapabilityKind.ASYNC_ACTION,
            CapabilityKind.BATCH_ACTION,
        }

    @property
    def is_destructive(self) -> bool:
        """Infer destructive behavior from tags."""
        truthy_markers = {"destructive", "destructive:true", "destructive:yes", "destructive:1"}
        return any(tag.lower() in truthy_markers for tag in self.tags)

    @property
    def risk(self) -> str | None:
        """Return risk value if encoded in tags like 'risk:high'."""
        allowed = {"low", "medium", "high", "critical"}
        for tag in self.tags:
            if tag.startswith("risk:"):
                _, _, value = tag.partition(":")
                value = value.strip().lower()
                return value if value in allowed else None
        return None

    def model_dump_clean(self) -> dict[str, Any]:
        """Return a stable serialized form for CLI/exporter use."""
        return self.model_dump(exclude_none=True, mode="json")

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: Any) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value

    @field_validator(
        "description",
        "output_validation_mode",
        "rollback_capability",
        "version",
        "deprecation_message",
        mode="before",
    )
    @classmethod
    def _normalize_optional_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value: Any) -> Any:
        if isinstance(value, CapabilityKind):
            return value
        if value is None:
            return CapabilityKind.ACTION
        return str(value).strip().lower()

    @field_validator("dependency_capabilities", "often_follows", mode="after")
    @classmethod
    def _normalize_capability_lists(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            item_str = str(item).strip()
            if item_str and item_str not in seen:
                seen.add(item_str)
                normalized.append(item_str)
        return normalized

    @model_validator(mode="before")
    @classmethod
    def _normalize_provider_fields(cls, data: Any) -> Any:
        """Accept legacy flat provider fields and normalize to provider object."""
        if not isinstance(data, dict):
            return data

        raw = dict(data)

        provider = raw.get("provider")
        provider_name = raw.pop("provider_name", None)
        provider_type = raw.pop("provider_type", None)
        provider_url = raw.pop("provider_url", None)

        if provider is None and any(value is not None for value in (provider_name, provider_type, provider_url)):
            raw["provider"] = {
                "name": provider_name,
                "type": provider_type,
                "url": provider_url,
            }

        return raw

    @model_validator(mode="after")
    def _normalize_fields(self) -> Capability:
        """Normalize tags and deprecation metadata after validation."""
        seen: set[str] = set()
        normalized_tags: list[str] = []

        for tag in self.tags:
            tag_str = str(tag).strip()
            if tag_str and tag_str not in seen:
                seen.add(tag_str)
                normalized_tags.append(tag_str)

        self.tags = normalized_tags

        if not self.deprecated and self.deprecation_message:
            self.deprecated = True

        if self.output_validation_mode is not None:
            allowed = {"strict", "warn", "disabled"}
            normalized_mode = self.output_validation_mode.strip().lower()
            if normalized_mode not in allowed:
                raise ValueError("output_validation_mode must be one of: strict, warn, disabled")
            self.output_validation_mode = normalized_mode

        return self
