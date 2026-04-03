"""Discovery source interface.

Defines the contract for discovering capabilities from various sources.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

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
    - code modules with decorators
    - manual registries
    - database or API endpoints

    Sources are responsible for:
    - converting their native format to AICP capabilities
    - providing metadata about the source
    - handling authentication if needed
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
    def description(self) -> str:
        """Human-readable description of this source."""
        return f"{self.source_type}:{self.source_name}"

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
        2. unique suffix match on segment boundary

        Sources can override for efficiency.
        """
        capabilities = await self.discover()

        exact_match = next(
            (capability for capability in capabilities if capability.name == name), None
        )
        if exact_match is not None:
            return exact_match

        suffix = f".{name}"
        suffix_matches = [
            capability for capability in capabilities if capability.name.endswith(suffix)
        ]

        if len(suffix_matches) == 1:
            return suffix_matches[0]

        return None

    async def discover_with_metadata(self) -> list[DiscoveredCapability]:
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

    def discovery_error(self, message: str, details: Any = None) -> DiscoveryError:
        """Build a DiscoveryError with this source's identity attached."""
        return DiscoveryError(
            message=message,
            source_name=self.source_name,
            source_type=self.source_type,
            details=details,
        )


class DiscoveredCapability(BaseModel):
    """A capability discovered from a source, with source metadata."""

    capability: Capability
    source_type: str
    source_name: str
    discovered_at: float = Field(default_factory=time.time)

    # Additional metadata from the source
    raw_data: dict[str, Any] | None = None
    source_uri: str | None = None
    version: str | None = None
