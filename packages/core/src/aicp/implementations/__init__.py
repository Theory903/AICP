"""In-memory implementations.

A simple in-memory implementations showing how interfaces work together.
"""

from typing import Any

from aicp.capability import Capability
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.capability_provider import (
    CapabilityNotFoundError,
    CapabilityProvider,
)

__all__ = [
    "InMemoryCapabilityRepository",
    "DefaultPolicyEngine",
    "DefaultWorkflowRuntime",
]


class InMemoryCapabilityRepository(CapabilityProvider):
    """In-memory capability repository.

    Simple implementation that stores capabilities in memory.
    """

    def __init__(self, name: str = "in_memory"):
        self._name = name
        self._capabilities: dict[str, Capability] = {}

    @property
    def provider_type(self) -> str:
        return "in_memory"

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"In-memory capability repository: {self._name}"

    async def discover(self) -> list[Capability]:
        return list(self._capabilities.values())

    async def get_capability(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        cap = self._capabilities.get(capability_name)
        if not cap:
            raise CapabilityNotFoundError(f"Capability not found: {capability_name}")

        # This is a stub - real implementations would call the actual capability
        return {"executed": capability_name, "args": arguments}

    def add_capability(self, capability: Capability) -> None:
        """Add a capability to the repository."""
        self._capabilities[capability.name] = capability

    def remove_capability(self, name: str) -> bool:
        """Remove a capability."""
        if name in self._capabilities:
            del self._capabilities[name]
            return True
        return False
