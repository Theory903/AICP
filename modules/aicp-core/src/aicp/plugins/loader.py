from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .hooks import HookRegistry
from .manifest import PluginManifest
from .registry import PluginRecord, PluginRegistry
from .sandbox import PluginSandbox, SandboxPolicy
from .sdk import BasePlugin


class PluginLoader:
    def __init__(
        self,
        plugin_dirs: list[Path],
        bundled_plugin_dirs: list[Path] | None = None,
        *,
        sandbox: PluginSandbox | None = None,
    ) -> None:
        self.plugin_dirs = plugin_dirs
        self.bundled_plugin_dirs = bundled_plugin_dirs or []
        self.registry = PluginRegistry()
        self.hooks = HookRegistry()
        self.sandbox = sandbox or PluginSandbox(SandboxPolicy())
        self._instances: dict[str, BasePlugin] = {}

    def discover(self) -> list[PluginRecord]:
        discovered: list[PluginRecord] = []
        for root, bundled in [
            *[(path, True) for path in self.bundled_plugin_dirs],
            *[(path, False) for path in self.plugin_dirs],
        ]:
            if not root.exists():
                continue
            for entry in sorted(item for item in root.iterdir() if item.is_dir()):
                manifest_path = entry / "plugin.json"
                if not manifest_path.exists():
                    continue
                manifest = self._read_manifest(manifest_path)
                discovered.append(self.registry.register(manifest, entry, bundled=bundled))
        return discovered

    async def load(self, plugin_id: str) -> BasePlugin:
        record = self.registry.require(plugin_id)
        if plugin_id in self._instances:
            return self._instances[plugin_id]
        self.sandbox.validate_permissions(record.manifest.permissions, bundled=record.bundled)
        plugin = self._load_plugin_class(record.path / record.manifest.entry_point)()
        await plugin.setup({})
        self._instances[plugin_id] = plugin
        self.registry.mark_loaded(plugin_id)
        return plugin

    async def enable(self, plugin_id: str) -> BasePlugin:
        plugin = await self.load(plugin_id)
        await plugin.on_startup()
        for hook_type, handlers in plugin.register_hooks().items():
            for handler in handlers:
                self.hooks.register(hook_type, plugin.manifest.id, handler)
        self.registry.enable(plugin_id)
        return plugin

    async def disable(self, plugin_id: str) -> None:
        plugin = self._instances.get(plugin_id)
        if plugin is None:
            return
        self.hooks.unregister_plugin(plugin_id)
        await plugin.on_shutdown()
        self.registry.disable(plugin_id)

    async def unload(self, plugin_id: str) -> None:
        self._instances.pop(plugin_id, None)
        self.hooks.unregister_plugin(plugin_id)
        self.registry.unload(plugin_id)

    def _read_manifest(self, manifest_path: Path) -> PluginManifest:
        with manifest_path.open() as handle:
            data = json.load(handle)
        return PluginManifest.model_validate(data)

    def _load_plugin_class(self, file_path: Path) -> type[Any]:
        module_name = f"aicp_plugin_{file_path.parent.name}_{abs(hash(str(file_path)))}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load plugin module: {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        plugin_class = getattr(module, "PLUGIN_CLASS", None)
        if plugin_class is None or not issubclass(plugin_class, BasePlugin):
            raise TypeError(f"PLUGIN_CLASS missing or invalid in {file_path}")
        return plugin_class
