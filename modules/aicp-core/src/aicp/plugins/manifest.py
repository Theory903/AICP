from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PluginType(str, Enum):
    CHANNEL = "channel"
    PROVIDER = "provider"
    TOOL = "tool"
    SKILL = "skill"
    TRANSPORT = "transport"


class HookType(str, Enum):
    PRE_CAPABILITY = "pre_capability"
    POST_CAPABILITY = "post_capability"
    PRE_WORKFLOW = "pre_workflow"
    POST_WORKFLOW = "post_workflow"
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"


class PluginDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str | None = None
    optional: bool = False

    @field_validator("id", "version", mode="before")
    @classmethod
    def _normalize_strings(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    hooks: list[HookType] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[PluginDependency] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    entry_point: str = "plugin.py"
    permissions: list[str] = Field(default_factory=list)
    enabled_by_default: bool = True
    bundled: bool = False

    @field_validator("id", "name", "version", "description", "author", "entry_point", mode="before")
    @classmethod
    def _normalize_required_strings(cls, value: Any) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value cannot be empty")
        return normalized

    @field_validator("capabilities", "permissions", mode="after")
    @classmethod
    def _dedupe_string_lists(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in value:
            cleaned = str(item).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized

    @field_validator("hooks", mode="after")
    @classmethod
    def _dedupe_hooks(cls, value: list[HookType]) -> list[HookType]:
        seen: set[HookType] = set()
        normalized: list[HookType] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized
