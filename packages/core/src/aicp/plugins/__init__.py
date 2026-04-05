from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class PluginType(str, Enum):
    """Plugin type enumeration"""
    COMMAND = "command"
    SKILL = "skill"
    MCP = "mcp"
    TRANSPORT = "transport"
    SOURCE = "source"


class PluginMetadata(BaseModel):
    """Plugin metadata for registration"""
    name: str
    version: str
    plugin_type: PluginType
    description: Optional[str] = None
    author: Optional[str] = None
    commands: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    mcp_servers: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TransportPlugin(BaseModel):
    """Transport plugin for protocol adapters"""
    name: str
    adapter_class: str
    config: dict[str, Any] = Field(default_factory=dict)


class SourcePlugin(BaseModel):
    """Source plugin for discovery adapters"""
    name: str
    adapter_class: str
    config: dict[str, Any] = Field(default_factory=dict)


def register_transport(name: str = None, adapter_class: str = None, config: dict[str, Any] = None):
    """Register a transport plugin - can be used as decorator or function"""
    def decorator(cls):
        return TransportPlugin(name=name or cls.__name__, adapter_class=cls.__name__, config=config or {})
    if adapter_class is not None:
        return decorator
    return decorator


def register_source(name: str = None, adapter_class: str = None, config: dict[str, Any] = None):
    """Register a source plugin - can be used as decorator or function"""
    def decorator(cls):
        return SourcePlugin(name=name or cls.__name__, adapter_class=cls.__name__, config=config or {})
    if adapter_class is not None:
        return decorator
    return decorator


from .hooks import HookEvent, HookRegistry
from .loader import PluginLoader
from .manifest import PluginManifest

__all__ = [
    "PluginType",
    "PluginMetadata",
    "TransportPlugin",
    "SourcePlugin",
    "register_transport",
    "register_source",
    "HookEvent",
    "HookRegistry",
    "PluginLoader",
    "PluginManifest",
]