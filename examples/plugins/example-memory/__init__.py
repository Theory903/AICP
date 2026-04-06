"""Example AICP plugin demonstrating plugin architecture."""

from aicp.plugins import (
    PluginAPI,
    PluginEntry,
    PluginMetadata,
    CapabilityInfo,
    HookContext,
    define_plugin,
)
from typing import Any


# Light metadata (Phase 1: Discovery)
METADATA = PluginMetadata(
    id="example-memory",
    kind="capability_source",
    name="Example Memory Plugin",
    version="1.0.0",
    description="Example plugin demonstrating AICP plugin architecture patterns",
    capabilities=[
        CapabilityInfo(name="memory.store", kind="action", description="Store a memory"),
        CapabilityInfo(name="memory.retrieve", kind="query", description="Retrieve memories"),
    ],
)


class ExampleMemoryPlugin(PluginAPI):
    """Example plugin implementation."""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.memories = []
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin."""
        self.config = config
        storage_path = config.get("storage_path", "/tmp/memories")
        print(f"Example Memory Plugin initialized with storage_path={storage_path}")
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        print("Example Memory Plugin shutting down")
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return METADATA


async def on_execution_completed(context: HookContext) -> None:
    """Hook: Called after capability execution."""
    print(f"Hook: Capability execution completed: {context.data}")


async def on_learning_event(context: HookContext) -> None:
    """Hook: Called when learning system generates insights."""
    print(f"Hook: Learning event received: {context.data}")


def define_plugin() -> PluginEntry:
    """Factory function to define the plugin entry point.
    
    This is the public API for plugin initialization.
    Returns a PluginEntry with metadata, factory, and hook handlers.
    """
    return define_plugin(
        metadata=METADATA,
        factory=lambda config: ExampleMemoryPlugin(config),
        hooks={
            "on_capability_execute_after": on_execution_completed,
            "on_learning_event": on_learning_event,
        }
    )
