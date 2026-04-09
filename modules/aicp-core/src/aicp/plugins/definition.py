"""Plugin definition and factory for AICP plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class PluginKind(str):
    """Plugin type enumeration."""
    CAPABILITY_SOURCE = "capability_source"
    WORKFLOW_PLUGIN = "workflow_plugin"
    APPROVAL_PLUGIN = "approval_plugin"
    POLICY_PLUGIN = "policy_plugin"
    PERCEPTION_PLUGIN = "perception_plugin"
    LEARNING_PLUGIN = "learning_plugin"
    GENERIC = "generic"


class HookPhase(str):
    """Lifecycle hook phases."""
    PLUGIN_INITIALIZE = "on_plugin_initialize"
    PLUGIN_SHUTDOWN = "on_plugin_shutdown"
    CAPABILITY_EXECUTE_BEFORE = "on_capability_execute_before"
    CAPABILITY_EXECUTE_AFTER = "on_capability_execute_after"
    APPROVAL_REQUEST = "on_approval_request"
    APPROVAL_DECISION = "on_approval_decision"
    POLICY_EVALUATE_BEFORE = "on_policy_evaluate_before"
    POLICY_EVALUATE_AFTER = "on_policy_evaluate_after"
    WORKFLOW_STEP_BEFORE = "on_workflow_step_before"
    WORKFLOW_STEP_AFTER = "on_workflow_step_after"
    PERCEPTION_EVENT = "on_perception_event"
    SIGNAL_INGESTION = "on_signal_ingestion"
    LEARNING_EVENT = "on_learning_event"


class HookContext(BaseModel):
    """Context passed to hook handlers."""
    phase: str
    plugin_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: "")

    class Config:
        extra = "allow"


class CapabilityInfo(BaseModel):
    """Info about capabilities provided by plugin."""
    name: str
    kind: str  # query, action, workflow, async_action, batch_action
    description: str | None = None


class RequirementsInfo(BaseModel):
    """System and runtime requirements."""
    aicp_version_min: str | None = None
    aicp_version_max: str | None = None
    python_version_min: str | None = None
    dependencies: dict[str, str] = Field(default_factory=dict)


class LifecycleInfo(BaseModel):
    """Plugin lifecycle configuration."""
    auto_enable: bool = False
    auto_enable_when_configured: list[str] = Field(default_factory=list)
    lazy_load: bool = True
    isolation_mode: str = "sandbox"  # main or sandbox


class PermissionsInfo(BaseModel):
    """Permission boundaries and trust."""
    access_level: str = "minimal"  # unrestricted, scoped, minimal
    requires_approval: bool = False
    trust_tier: int = 0  # 0-4


class PluginMetadata(BaseModel):
    """Metadata for an AICP plugin."""
    id: str
    kind: str
    name: str
    version: str
    description: str | None = None
    author: str | None = None
    license: str | None = None
    repository: str | None = None
    tags: list[str] = Field(default_factory=list)
    requirements: RequirementsInfo = Field(default_factory=RequirementsInfo)
    lifecycle: LifecycleInfo = Field(default_factory=LifecycleInfo)
    capabilities: list[CapabilityInfo] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    permissions: PermissionsInfo = Field(default_factory=PermissionsInfo)
    enabled_by_default: bool = False


class PluginAPI(ABC):
    """Base interface for all AICP plugins.

    Public SDK: plugins inherit from this to implement hook handlers,
    expose capabilities, or integrate with workflow/approval/policy engines.
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with config."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up plugin resources."""

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""


class PluginEntry:
    """Factory entry point for defining plugins.

    Plugins expose a factory function that returns PluginEntry,
    which AICP loads and invokes to get the plugin instance.

    Usage:
        def define_plugin() -> PluginEntry:
            return PluginEntry(
                metadata=PluginMetadata(...),
                factory=lambda config: MyPlugin(config)
            )
    """

    def __init__(
        self,
        metadata: PluginMetadata,
        factory: Callable[[dict[str, Any]], PluginAPI],
        hooks: dict[str, Callable[[HookContext], Any]] | None = None,
    ):
        self.metadata = metadata
        self.factory = factory
        self.hooks = hooks or {}

    async def create_instance(self, config: dict[str, Any]) -> PluginAPI:
        """Create a plugin instance."""
        instance = self.factory(config)
        await instance.initialize(config)
        return instance


def define_plugin(
    metadata: PluginMetadata,
    factory: Callable[[dict[str, Any]], PluginAPI],
    hooks: dict[str, Callable[[HookContext], Any]] | None = None,
) -> PluginEntry:
    """Factory function to define a plugin entry.

    This is the primary public API for plugin developers.

    Args:
        metadata: Plugin metadata (id, kind, name, version, etc.)
        factory: Callable that returns a PluginAPI instance
        hooks: Optional dict mapping hook phases to handlers

    Returns:
        PluginEntry ready for registration and loading
    """
    return PluginEntry(metadata=metadata, factory=factory, hooks=hooks)


__all__ = [
    "PluginKind",
    "HookPhase",
    "HookContext",
    "CapabilityInfo",
    "RequirementsInfo",
    "LifecycleInfo",
    "PermissionsInfo",
    "PluginMetadata",
    "PluginAPI",
    "PluginEntry",
    "define_plugin",
]
