"""Plugin system for AICP.

Provides extensible plugin architecture for transports, auth providers,
and capability sources.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar


class PluginError(Exception):
    """Base plugin system error."""


class PluginRegistrationError(PluginError):
    """Raised when plugin registration fails."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found."""


@dataclass(slots=True)
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str
    author: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.version = self.version.strip()

        if not self.name:
            raise ValueError("Plugin metadata name cannot be empty")
        if not self.version:
            raise ValueError("Plugin metadata version cannot be empty")

        self.tags = [tag.strip() for tag in self.tags if tag.strip()]


class Plugin(ABC):
    """Base class for all AICP plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        raise NotImplementedError

    @abstractmethod
    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin."""
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up plugin resources."""
        raise NotImplementedError


class TransportPlugin(Plugin):
    """Plugin for custom transport implementations."""

    @abstractmethod
    def get_transport_type(self) -> str:
        """Return the transport type identifier."""
        raise NotImplementedError

    @abstractmethod
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request via this transport."""
        raise NotImplementedError

    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        """Receive a response via this transport."""
        raise NotImplementedError


class AuthProviderPlugin(Plugin):
    """Plugin for custom authentication providers."""

    @abstractmethod
    def get_auth_type(self) -> str:
        """Return the auth type identifier."""
        raise NotImplementedError

    @abstractmethod
    def apply_auth(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        """Apply authentication to a request."""
        raise NotImplementedError


class CapabilitySourcePlugin(Plugin):
    """Plugin for discovering capabilities from external sources."""

    @abstractmethod
    async def discover(self) -> list[dict[str, Any]]:
        """Discover capabilities from this source."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, capability_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a capability from this source."""
        raise NotImplementedError


TTransport = TypeVar("TTransport", bound=TransportPlugin)
TAuth = TypeVar("TAuth", bound=AuthProviderPlugin)
TSource = TypeVar("TSource", bound=CapabilitySourcePlugin)


class PluginRegistry:
    """Central registry for AICP plugins.

    Manages plugin lifecycle and provides plugin lookup.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._transports: dict[str, type[TransportPlugin]] = {}
        self._auth_providers: dict[str, type[AuthProviderPlugin]] = {}
        self._sources: dict[str, type[CapabilitySourcePlugin]] = {}
        self._initialized: set[str] = set()

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        name = plugin.metadata.name
        if name in self._plugins:
            raise PluginRegistrationError(f"Plugin '{name}' is already registered")
        self._plugins[name] = plugin

    def register_transport(self, name: str, transport_class: type[TTransport]) -> None:
        """Register a transport plugin class."""
        cleaned = name.strip()
        if not cleaned:
            raise PluginRegistrationError("Transport name cannot be empty")
        if cleaned in self._transports:
            raise PluginRegistrationError(f"Transport '{cleaned}' is already registered")
        self._transports[cleaned] = transport_class

    def register_auth_provider(self, name: str, provider_class: type[TAuth]) -> None:
        """Register an auth provider plugin class."""
        cleaned = name.strip()
        if not cleaned:
            raise PluginRegistrationError("Auth provider name cannot be empty")
        if cleaned in self._auth_providers:
            raise PluginRegistrationError(f"Auth provider '{cleaned}' is already registered")
        self._auth_providers[cleaned] = provider_class

    def register_capability_source(self, name: str, source_class: type[TSource]) -> None:
        """Register a capability source plugin class."""
        cleaned = name.strip()
        if not cleaned:
            raise PluginRegistrationError("Capability source name cannot be empty")
        if cleaned in self._sources:
            raise PluginRegistrationError(f"Capability source '{cleaned}' is already registered")
        self._sources[cleaned] = source_class

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def require_plugin(self, name: str) -> Plugin:
        """Get a registered plugin by name or raise."""
        plugin = self.get_plugin(name)
        if plugin is None:
            raise PluginNotFoundError(f"Plugin '{name}' not found")
        return plugin

    def get_transport(self, name: str) -> type[TransportPlugin] | None:
        """Get a transport plugin class by name."""
        return self._transports.get(name)

    def get_auth_provider(self, name: str) -> type[AuthProviderPlugin] | None:
        """Get an auth provider class by name."""
        return self._auth_providers.get(name)

    def get_capability_source(self, name: str) -> type[CapabilitySourcePlugin] | None:
        """Get a capability source class by name."""
        return self._sources.get(name)

    async def initialize_plugin(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> Plugin:
        """Initialize a plugin by name."""
        plugin = self.require_plugin(name)
        if name in self._initialized:
            return plugin

        await plugin.initialize(config)
        self._initialized.add(name)
        return plugin

    async def shutdown_plugin(self, name: str) -> None:
        """Shutdown a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin is None:
            raise PluginNotFoundError(f"Plugin '{name}' not found")

        if name in self._initialized:
            await plugin.shutdown()
            self._initialized.discard(name)

    async def shutdown_all(self) -> None:
        """Shutdown all initialized plugins."""
        names = list(self._initialized)
        for name in names:
            await self.shutdown_plugin(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """List all registered plugins."""
        return [plugin.metadata for plugin in self._plugins.values()]

    def list_transports(self) -> list[str]:
        """List all registered transport types."""
        return sorted(self._transports.keys())

    def list_auth_providers(self) -> list[str]:
        """List all registered auth providers."""
        return sorted(self._auth_providers.keys())

    def list_capability_sources(self) -> list[str]:
        """List all registered capability source types."""
        return sorted(self._sources.keys())

    def is_initialized(self, name: str) -> bool:
        """Check whether a plugin has been initialized."""
        return name in self._initialized


_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def register_transport(name: str) -> Callable[[type[TTransport]], type[TTransport]]:
    """Decorator to register a transport plugin.

    Usage:
        @register_transport("websocket")
        class WebSocketTransport(TransportPlugin):
            ...
    """

    def decorator(cls: type[TTransport]) -> type[TTransport]:
        registry = get_plugin_registry()
        registry.register_transport(name, cls)
        return cls

    return decorator


def register_auth_provider(name: str) -> Callable[[type[TAuth]], type[TAuth]]:
    """Decorator to register an auth provider plugin."""

    def decorator(cls: type[TAuth]) -> type[TAuth]:
        registry = get_plugin_registry()
        registry.register_auth_provider(name, cls)
        return cls

    return decorator


def register_capability_source(name: str) -> Callable[[type[TSource]], type[TSource]]:
    """Decorator to register a capability source plugin."""

    def decorator(cls: type[TSource]) -> type[TSource]:
        registry = get_plugin_registry()
        registry.register_capability_source(name, cls)
        return cls

    return decorator