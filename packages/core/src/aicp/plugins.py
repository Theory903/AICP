"""Plugin system for AICP.

Provides extensible plugin architecture for transports, auth providers,
and capability sources, similar to UTCP's plugin system.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable
from dataclasses import dataclass, field


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    author: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)


class Plugin(ABC):
    """Base class for all AICP plugins."""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        pass
    
    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin.
        
        Args:
            config: Optional configuration for the plugin.
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Clean up plugin resources."""
        pass


class TransportPlugin(Plugin):
    """Plugin for custom transport implementations.
    
    Allows adding new protocol transports (WebSocket, SSE, GraphQL, etc.)
    """
    
    @abstractmethod
    def get_transport_type(self) -> str:
        """Return the transport type identifier."""
        pass
    
    @abstractmethod
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request via this transport."""
        pass
    
    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        """Receive a response via this transport."""
        pass


class AuthProviderPlugin(Plugin):
    """Plugin for custom authentication providers."""
    
    @abstractmethod
    def get_auth_type(self) -> str:
        """Return the auth type identifier."""
        pass
    
    @abstractmethod
    def apply_auth(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        """Apply authentication to request."""
        pass


class CapabilitySourcePlugin(Plugin):
    """Plugin for discovering capabilities from external sources."""
    
    @abstractmethod
    async def discover(self) -> list[dict[str, Any]]:
        """Discover capabilities from this source."""
        pass
    
    @abstractmethod
    async def execute(self, capability_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a capability from this source."""
        pass


class PluginRegistry:
    """Central registry for AICP plugins.
    
    Manages plugin lifecycle and provides plugin lookup.
    """
    
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._transports: dict[str, type[TransportPlugin]] = {}
        self._auth_providers: dict[str, type[AuthProviderPlugin]] = {}
        self._sources: dict[str, type[CapabilitySourcePlugin]] = {}
        self._initialized: set[str] = set()
        
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        self._plugins[plugin.metadata.name] = plugin
        
    def register_transport(self, name: str, transport_class: type[TransportPlugin]) -> None:
        """Register a transport plugin class."""
        self._transports[name] = transport_class
        
    def register_auth_provider(self, name: str, provider_class: type[AuthProviderPlugin]) -> None:
        """Register an auth provider plugin class."""
        self._auth_providers[name] = provider_class
        
    def register_capability_source(self, name: str, source_class: type[CapabilitySourcePlugin]) -> None:
        """Register a capability source plugin class."""
        self._sources[name] = source_class
        
    def get_plugin(self, name: str) -> Plugin | None:
        """Get a registered plugin by name."""
        return self._plugins.get(name)
    
    def get_transport(self, name: str) -> type[TransportPlugin] | None:
        """Get a transport plugin class by name."""
        return self._transports.get(name)
    
    def get_auth_provider(self, name: str) -> type[AuthProviderPlugin] | None:
        """Get an auth provider class by name."""
        return self._auth_providers.get(name)
    
    def get_capability_source(self, name: str) -> type[CapabilitySourcePlugin] | None:
        """Get a capability source class by name."""
        return self._sources.get(name)
    
    def initialize_plugin(self, name: str, config: dict[str, Any] | None = None) -> Plugin:
        """Initialize a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin:
            plugin.initialize(config)
            self._initialized.add(name)
        return plugin
    
    def shutdown_plugin(self, name: str) -> None:
        """Shutdown a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin and name in self._initialized:
            plugin.shutdown()
            self._initialized.discard(name)
            
    def list_plugins(self) -> list[PluginMetadata]:
        """List all registered plugins."""
        return [p.metadata for p in self._plugins.values()]
    
    def list_transports(self) -> list[str]:
        """List all registered transport types."""
        return list(self._transports.keys())


_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def register_transport(name: str) -> Callable[[type[TransportPlugin]], type[TransportPlugin]]:
    """Decorator to register a transport plugin.
    
    Usage:
        @register_transport("websocket")
        class WebSocketTransport(TransportPlugin):
            ...
    """
    def decorator(cls: type[TransportPlugin]) -> type[TransportPlugin]:
        registry = get_plugin_registry()
        registry.register_transport(name, cls)
        return cls
    return decorator


def register_auth_provider(name: str) -> Callable[[type[AuthProviderPlugin]], type[AuthProviderPlugin]]:
    """Decorator to register an auth provider plugin."""
    def decorator(cls: type[AuthProviderPlugin]) -> type[AuthProviderPlugin]:
        registry = get_plugin_registry()
        registry.register_auth_provider(name, cls)
        return cls
    return decorator


def register_capability_source(name: str) -> Callable[[type[CapabilitySourcePlugin]], type[CapabilitySourcePlugin]]:
    """Decorator to register a capability source plugin."""
    def decorator(cls: type[CapabilitySourcePlugin]) -> type[CapabilitySourcePlugin]:
        registry = get_plugin_registry()
        registry.register_capability_source(name, cls)
        return cls
    return decorator
