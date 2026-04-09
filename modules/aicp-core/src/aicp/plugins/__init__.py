from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .hooks import HookContext, HookRegistry, HookResult
from .loader import PluginLoader
from .manifest import HookType, PluginDependency, PluginManifest, PluginType
from .registry import PluginRecord, PluginRegistry, PluginState
from .sandbox import PluginSandbox, SandboxPolicy
from .sdk import BaseChannelPlugin, BasePlugin, BaseProviderPlugin, BaseSkillPlugin, BaseToolPlugin

# Backward compat: transport/source plugin support used by graphql, websocket, sse adapters

class PluginMetadata(BaseModel):
    name: str
    version: str
    plugin_type: PluginType
    description: str | None = None
    author: str | None = None
    commands: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    mcp_servers: dict[str, Any] = Field(default_factory=dict)


class TransportPlugin(BaseModel):
    name: str
    adapter_class: str
    config: dict[str, Any] = Field(default_factory=dict)
    plugin_type: PluginType = PluginType.TRANSPORT
    tags: list[str] = Field(default_factory=list)


class SourcePlugin(BaseModel):
    name: str
    adapter_class: str
    config: dict[str, Any] = Field(default_factory=dict)


def register_transport(
    name: str | None = None,
    adapter_class: str | None = None,
    config: dict[str, Any] | None = None,
):
    def decorator(cls):
        return TransportPlugin(
            name=name or cls.__name__,
            adapter_class=cls.__name__,
            config=config or {},
        )
    if adapter_class is not None:
        return decorator
    return decorator


def register_source(
    name: str | None = None,
    adapter_class: str | None = None,
    config: dict[str, Any] | None = None,
):
    def decorator(cls):
        return SourcePlugin(
            name=name or cls.__name__,
            adapter_class=cls.__name__,
            config=config or {},
        )
    if adapter_class is not None:
        return decorator
    return decorator


__all__ = [
    "BaseChannelPlugin",
    "BasePlugin",
    "BaseProviderPlugin",
    "BaseSkillPlugin",
    "BaseToolPlugin",
    "HookContext",
    "HookRegistry",
    "HookResult",
    "HookType",
    "PluginDependency",
    "PluginLoader",
    "PluginManifest",
    "PluginMetadata",
    "PluginRecord",
    "PluginRegistry",
    "PluginSandbox",
    "PluginState",
    "PluginType",
    "SandboxPolicy",
    "SourcePlugin",
    "TransportPlugin",
    "register_source",
    "register_transport",
]
