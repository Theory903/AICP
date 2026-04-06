"""Lazy loading support for AICP plugins.

Implements the `.runtime.ts` boundary pattern from OpenClaw: separates
light metadata (manifests, discovery) from heavy runtime code (executors,
providers, policy engines).
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


class LazyValue:
    """Lazy-evaluated value holder.
    
    Defers module import and attribute resolution until first access.
    Useful for separating discovery (light) from execution (heavy).
    
    Example:
        # Define lazy value in module __init__.py
        executor_runtime = LazyValue(
            module_path="my_plugin.runtime",
            attribute="CustomExecutor"
        )
        
        # Access it later (import happens on first access)
        executor_class = executor_runtime.get()
    """

    def __init__(
        self,
        module_path: str,
        attribute: str,
        factory: Callable[[], Any] | None = None,
    ):
        """Initialize lazy value.
        
        Args:
            module_path: Python module path (e.g., "my_plugin.runtime")
            attribute: Attribute name in module (e.g., "CustomExecutor")
            factory: Optional factory function instead of module import
        """
        self.module_path = module_path
        self.attribute = attribute
        self.factory = factory
        self._cache: Any = None
        self._loaded = False

    def get(self) -> Any:
        """Get the lazy value, loading on first access."""
        if self._loaded:
            return self._cache
        
        if self.factory:
            self._cache = self.factory()
        else:
            try:
                module = importlib.import_module(self.module_path)
                self._cache = getattr(module, self.attribute)
            except (ImportError, AttributeError) as e:
                raise ImportError(
                    f"Failed to lazy-load {self.module_path}.{self.attribute}: {e}"
                )
        
        self._loaded = True
        return self._cache

    def is_loaded(self) -> bool:
        """Check if lazy value has been loaded."""
        return self._loaded


class RuntimeModule:
    """Container for lazy-loaded runtime modules.
    
    Declares a module's heavy components without triggering imports.
    Used alongside lightweight metadata in plugin manifests.
    """

    def __init__(self):
        """Initialize runtime module."""
        self._components: dict[str, LazyValue] = {}

    def register(
        self,
        name: str,
        module_path: str,
        attribute: str,
    ) -> None:
        """Register a lazily-loaded component.
        
        Args:
            name: Component name
            module_path: Python module path
            attribute: Attribute name in module
        """
        self._components[name] = LazyValue(module_path, attribute)

    def get(self, name: str) -> Any:
        """Get a component by name."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' not registered")
        return self._components[name].get()

    def has(self, name: str) -> bool:
        """Check if component exists."""
        return name in self._components

    def is_loaded(self, name: str) -> bool:
        """Check if component has been loaded."""
        if name not in self._components:
            return False
        return self._components[name].is_loaded()


def lazy_import(
    module_path: str,
    attribute: str,
) -> LazyValue:
    """Create a lazy import value.
    
    Use this to defer heavy imports until needed.
    
    Example:
        # In plugin/__init__.py (light metadata)
        from aicp.plugins.lazy import lazy_import
        
        # Heavy executor only imported on first access
        CustomExecutor = lazy_import("my_plugin.runtime", "CustomExecutor")
    """
    return LazyValue(module_path, attribute)


__all__ = [
    "LazyValue",
    "RuntimeModule",
    "lazy_import",
]
