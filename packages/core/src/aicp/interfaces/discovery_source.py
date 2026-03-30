"""Discovery source interface.

Defines the contract for discovering capabilities from various sources.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aicp.capability import Capability


class DiscoveryError(Exception):
    """Raised when capability discovery fails."""

    def __init__(
        self,
        message: str,
        source_name: str | None = None,
        source_type: str | None = None,
        details: Any = None,
    ):
        self.source_name = source_name
        self.source_type = source_type
        self.details = details

        prefix_parts: list[str] = []
        if source_type:
            prefix_parts.append(source_type)
        if source_name:
            prefix_parts.append(source_name)

        prefix = f"[{'/'.join(prefix_parts)}] " if prefix_parts else ""
        super().__init__(f"{prefix}{message}")


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
        """Type identifier for this source."""
        raise NotImplementedError

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique name for this source instance."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this source."""
        raise NotImplementedError

    @abstractmethod
    async def discover(self) -> list[Capability]:
        """Discover all capabilities from this source.

        Returns:
            List of capabilities available from this source.

        Raises:
            DiscoveryError: If discovery fails.
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh(self) -> list[Capability]:
        """Refresh capabilities and bypass any cached state.

        Returns:
            Fresh list of capabilities.

        Raises:
            DiscoveryError: If refresh fails.
        """
        raise NotImplementedError

    async def list_capability_names(self) -> list[str]:
        """List capability names from this source."""
        capabilities = await self.discover()
        return [capability.name for capability in capabilities]

    async def has_capability(self, name: str) -> bool:
        """Check whether a capability exists in this source."""
        return await self.get_capability(name) is not None

    async def get_capability(self, name: str) -> Capability | None:
        """Get a specific capability by name.

        Default implementation:
        1. exact name match
        2. suffix match on segment boundary

        Sources can override for efficiency.
        """
        capabilities = await self.discover()

        for capability in capabilities:
            if capability.name == name:
                return capability

        suffix = f".{name}"
        for capability in capabilities:
            if capability.name.endswith(suffix):
                return capability

        return None

    async def discover_with_metadata(self) -> list["DiscoveredCapability"]:
        """Discover capabilities wrapped with source metadata."""
        discovered_at = time.time()
        capabilities = await self.discover()

        return [
            DiscoveredCapability(
                capability=capability,
                source_type=self.source_type,
                source_name=self.source_name,
                discovered_at=discovered_at,
            )
            for capability in capabilities
        ]


class DiscoveredCapability(BaseModel):
    """A capability discovered from a source, with source metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    capability: Capability
    source_type: str
    source_name: str
    discovered_at: float = Field(default_factory=time.time)

    # Additional metadata from the source
    raw_data: dict[str, Any] | None = None
    source_uri: str | None = None
    version: str | None = None