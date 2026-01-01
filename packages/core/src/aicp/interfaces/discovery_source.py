"""Discovery source interface.

Defines the contract for discovering capabilities from various sources.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from aicp.capability import Capability


class DiscoverySource(ABC):
    """Abstract interface for capability discovery sources.

    A discovery source is a place where capabilities come from:
    - OpenAPI specifications
    - MCP servers
    - Code modules with decorators
    - Manual registries
    - Database or API endpoints

    Sources are responsible for:
    - Converting their native format to AICP capabilities
    - Providing metadata about the source
    - Handling authentication if needed
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Type identifier for this source (e.g., 'openapi', 'mcp', 'code')."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique name for this source instance."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this source."""
        pass

    @abstractmethod
    async def discover(self) -> list[Capability]:
        """Discover all capabilities from this source.

        Returns:
            List of capabilities available from this source.

        Raises:
            DiscoveryError: If discovery fails.
        """
        pass

    @abstractmethod
    async def refresh(self) -> list[Capability]:
        """Refresh capabilities (re-discover).

        Some sources may cache capabilities; this forces a refresh.

        Returns:
            Fresh list of capabilities.
        """
        pass

    async def get_capability(self, name: str) -> Capability | None:
        """Get a specific capability by name.

        Default implementation uses discover().
        Sources can override for efficiency.

        Args:
            name: The capability name.

        Returns:
            The capability if found.
        """
        capabilities = await self.discover()
        for cap in capabilities:
            if cap.name == name or cap.name.endswith(f".{name}"):
                return cap
        return None


class DiscoveredCapability(BaseModel):
    """A capability discovered from a source, with source metadata."""

    capability: Capability
    source_type: str
    source_name: str
    discovered_at: float

    # Additional metadata from the source
    raw_data: dict[str, Any] | None = None
