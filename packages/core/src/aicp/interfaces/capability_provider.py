"""Capability provider interface.

Defines the contract for capability discovery and retrieval. Multiple sources
can provide capabilities: OpenAPI specs, MCP servers, code decorators, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aicp.capability import Capability, CapabilityKind


class DiscoveryError(Exception):
    """Raised when capability discovery fails."""

    def __init__(self, message: str, provider_name: str | None = None):
        self.provider_name = provider_name
        super().__init__(message)


class CapabilityNotFoundError(Exception):
    """Raised when a requested capability cannot be found."""

    def __init__(self, capability_name: str, provider_name: str | None = None):
        self.capability_name = capability_name
        self.provider_name = provider_name
        message = f"Capability not found: {capability_name}"
        if provider_name:
            message = f"{message} (provider={provider_name})"
        super().__init__(message)


class CapabilityProvider(ABC):
    """Abstract interface for capability providers.

    A capability provider is a source of capabilities. It could be:
    - An OpenAPI specification
    - An MCP server
    - A code module with decorated functions
    - A manual registry

    Providers are responsible for:
    - Discovering available capabilities
    - Providing capability metadata
    - Executing capability calls
    """

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """The type identifier for this provider."""
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider instance."""
        raise NotImplementedError

    @abstractmethod
    async def discover(self) -> list[Capability]:
        """Discover all available capabilities from this provider.

        Returns:
            List of capabilities available from this provider.

        Raises:
            DiscoveryError: If discovery fails.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_capability(self, name: str) -> Capability | None:
        """Get a specific capability by name.

        Args:
            name: The capability name.

        Returns:
            The capability if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a capability with the given arguments.

        Args:
            capability_name: Name of the capability to execute.
            arguments: Arguments to pass to the capability.
            context: Optional execution context.

        Returns:
            The capability's result.

        Raises:
            CapabilityNotFoundError: If capability does not exist.
            Exception: If execution fails.
        """
        raise NotImplementedError

    async def has_capability(self, name: str) -> bool:
        """Check whether a capability exists."""
        return await self.get_capability(name) is not None

    async def list_capability_names(self) -> list[str]:
        """List capability names for this provider."""
        capabilities = await self.discover()
        return [capability.name for capability in capabilities]

    async def search(
        self,
        query: str,
        limit: int = 10,
        kind_filter: list[CapabilityKind] | None = None,
    ) -> list[Capability]:
        """Search for capabilities matching the query.

        Default implementation does simple ranking on:
        - exact name match
        - substring name match
        - description match
        - tag match

        Providers can override with more sophisticated search.
        """
        if limit <= 0:
            return []

        capabilities = await self.discover()
        normalized_query = query.strip().lower()

        filtered: list[tuple[int, Capability]] = []
        for capability in capabilities:
            if kind_filter and capability.kind not in kind_filter:
                continue

            if not normalized_query:
                filtered.append((0, capability))
                continue

            score = 0
            name = capability.name.lower()
            description = capability.description.lower() if capability.description else ""
            tags = [tag.lower() for tag in capability.tags]

            if name == normalized_query:
                score += 100
            elif name.startswith(normalized_query):
                score += 60
            elif normalized_query in name:
                score += 40

            if normalized_query in description:
                score += 20

            if any(normalized_query in tag for tag in tags):
                score += 15

            if score > 0:
                filtered.append((score, capability))

        filtered.sort(key=lambda item: (-item[0], item[1].name))
        return [capability for _, capability in filtered[:limit]]
