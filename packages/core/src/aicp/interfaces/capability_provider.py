"""Capability provider interface.

Defines the contract for capability discovery and retrieval. Multiple sources
can provide capabilities: OpenAPI specs, MCP servers, code decorators, etc.
"""

from abc import ABC, abstractmethod
from typing import Any

from aicp.capability import Capability, CapabilityKind


class DiscoveryError(Exception):
    """Raised when capability discovery fails."""

    pass


class CapabilityNotFoundError(Exception):
    """Raised when a requested capability cannot be found."""

    pass


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
        """The type identifier for this provider (e.g., 'openapi', 'mcp', 'code')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider instance."""
        pass

    @abstractmethod
    async def discover(self) -> list[Capability]:
        """Discover all available capabilities from this provider.

        Returns:
            List of capabilities available from this provider.

        Raises:
            DiscoveryError: If discovery fails.
        """
        pass

    @abstractmethod
    async def get_capability(self, name: str) -> Capability | None:
        """Get a specific capability by name.

        Args:
            name: The capability name (may include provider prefix).

        Returns:
            The capability if found, None otherwise.
        """
        pass

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
            context: Optional execution context (workflow ID, user info, etc.).

        Returns:
            The capability's result.

        Raises:
            CapabilityNotFoundError: If capability doesn't exist.
            ExecutionError: If execution fails.
        """
        pass

    async def search(
        self,
        query: str,
        limit: int = 10,
        kind_filter: list[CapabilityKind] | None = None,
    ) -> list[Capability]:
        """Search for capabilities matching the query.

        Default implementation does simple text matching on name and description.
        Providers can override with more sophisticated search.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            kind_filter: Optional filter by capability kinds.

        Returns:
            List of matching capabilities.
        """
        all_caps = await self.discover()
        query_lower = query.lower()

        matches = []
        for cap in all_caps:
            if kind_filter and cap.kind not in kind_filter:
                continue
            if query_lower in cap.name.lower() or query_lower in cap.description.lower():
                matches.append(cap)

        return matches[:limit]
