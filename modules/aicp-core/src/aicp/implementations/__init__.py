"""In-memory implementations.

Concrete in-memory implementations of the AICP interfaces.
Capabilities can be registered with callable handlers that are
invoked during execution.
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from aicp.capability import Capability
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.capability_provider import (
    CapabilityNotFoundError,
    CapabilityProvider,
)

# Handler signature: (arguments, context) -> result
CapabilityHandler = Callable[
    [dict[str, Any], dict[str, Any]],
    Any | Coroutine[Any, Any, Any],
]

__all__ = [
    "CapabilityHandler",
    "InMemoryCapabilityRepository",
    "DefaultPolicyEngine",
    "DefaultWorkflowRuntime",
]


class InMemoryCapabilityRepository(CapabilityProvider):
    """In-memory capability repository with handler-based execution.

    Stores capabilities and their callable handlers in memory.
    When ``execute()`` is called, the registered handler is invoked
    with the provided arguments and context.

    Usage::

        repo = InMemoryCapabilityRepository()

        async def create_note(args, ctx):
            return {"id": "1", "title": args["title"]}

        repo.add_capability(note_cap, handler=create_note)
        result = await repo.execute("notes.create", {"title": "Hello"})
    """

    def __init__(self, name: str = "in_memory"):
        self._name = name
        self._capabilities: dict[str, Capability] = {}
        self._handlers: dict[str, CapabilityHandler] = {}

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
        """Execute a capability by invoking its registered handler.

        Args:
            capability_name: Name of the capability to execute.
            arguments: Arguments to pass to the handler.
            context: Optional execution context (workflow ID, user info, etc.).

        Returns:
            The handler's return value.

        Raises:
            CapabilityNotFoundError: If the capability or its handler is not registered.
        """
        cap = self._capabilities.get(capability_name)
        if not cap:
            raise CapabilityNotFoundError(f"Capability not found: {capability_name}")

        handler = self._handlers.get(capability_name)
        if handler is None:
            return {"executed": capability_name, "args": arguments}

        ctx = context or {}
        result = handler(arguments, ctx)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def add_capability(
        self,
        capability: Capability,
        handler: CapabilityHandler | None = None,
    ) -> None:
        """Add a capability and its optional handler to the repository.

        Args:
            capability: The capability metadata to register.
            handler: Callable invoked when the capability is executed.
                     Signature: ``(arguments: dict, context: dict) -> Any``.
                     May be sync or async.
        """
        self._capabilities[capability.name] = capability
        if handler is not None:
            self._handlers[capability.name] = handler

    def register_handler(
        self,
        capability_name: str,
        handler: CapabilityHandler,
    ) -> None:
        """Register or replace a handler for an existing capability.

        Args:
            capability_name: Name of the capability.
            handler: Callable to handle execution.

        Raises:
            CapabilityNotFoundError: If the capability is not registered.
        """
        if capability_name not in self._capabilities:
            raise CapabilityNotFoundError(
                f"Cannot register handler: capability '{capability_name}' not found. "
                f"Add the capability first via add_capability()."
            )
        self._handlers[capability_name] = handler

    def remove_capability(self, name: str) -> bool:
        """Remove a capability and its handler."""
        if name in self._capabilities:
            del self._capabilities[name]
            self._handlers.pop(name, None)
            return True
        return False
