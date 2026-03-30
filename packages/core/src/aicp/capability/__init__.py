"""Capability model.

The core AICP capability definition with rich metadata for AI agents.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class OutputSchema(BaseModel):
    """Output schema for a capability."""

    model_config = ConfigDict(extra="allow")

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class RenderSpec(BaseModel):
    """Specification for rendering capability results."""

    model_config = ConfigDict(extra="forbid")

    format: str = "text"  # text, json, table, code, image
    fields: list[str] | None = None
    max_length: int | None = Field(default=None, ge=1)
    truncate: bool = True
    syntax: str | None = None


class PolicyRef(BaseModel):
    """Reference to a policy for this capability."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ContinuationSpec(BaseModel):
    """Specification for continuing after execution."""

    model_config = ConfigDict(extra="forbid")

    can_continue: bool = True
    next_capabilities: list[str] = Field(default_factory=list)
    next_hint: str | None = None


class ProviderInfo(BaseModel):
    """Information about the capability provider."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: str | None = None
    url: str | None = None


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

    # Provider info
    provider: ProviderInfo | None = None

    # Metadata
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
        return "destructive" in self.tags or any(tag.startswith("destructive:") for tag in self.tags)

    @property
    def risk(self) -> str | None:
        """Return risk value if encoded in tags like 'risk:high'."""
        for tag in self.tags:
            if tag.startswith("risk:"):
                _, _, value = tag.partition(":")
                return value or None
        return None

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
    def _normalize_fields(self) -> "Capability":
        """Normalize tags and deprecation metadata after validation."""
        # Deduplicate tags while preserving order
        seen: set[str] = set()
        normalized_tags: list[str] = []
        for tag in self.tags:
            tag_str = str(tag).strip()
            if tag_str and tag_str not in seen:
                seen.add(tag_str)
                normalized_tags.append(tag_str)
        self.tags = normalized_tags

        # Keep deprecation message meaningful
        if not self.deprecated and self.deprecation_message:
            self.deprecated = True

        return self