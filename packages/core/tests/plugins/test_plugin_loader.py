import asyncio
import json
from pathlib import Path
from typing import Any

from aicp.plugins import HookType, PluginLoader, PluginState, PluginType


def _write_plugin(root: Path, plugin_id: str, *, bundled: bool = False) -> Path:
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "name": f"{plugin_id} plugin",
                "version": "1.0.0",
                "description": "Fixture plugin",
                "author": "Test Suite",
                "plugin_type": PluginType.TOOL.value,
                "hooks": [HookType.PRE_CAPABILITY.value, HookType.ON_STARTUP.value, HookType.ON_SHUTDOWN.value],
                "capabilities": [f"{plugin_id}.run"],
                "dependencies": [],
                "config_schema": {"type": "object"},
                "permissions": [f"capability:{plugin_id}.run"],
                "bundled": bundled,
            }
        )
    )
    (plugin_dir / "plugin.py").write_text(
        """
from aicp.plugins import BaseToolPlugin, HookContext, HookType, PluginManifest, PluginType


class FixturePlugin(BaseToolPlugin):
    def __init__(self):
        super().__init__(
            PluginManifest(
                id=\"demo.echo\",
                name=\"demo.echo plugin\",
                version=\"1.0.0\",
                description=\"Fixture plugin\",
                author=\"Test Suite\",
                plugin_type=PluginType.TOOL,
                hooks=[HookType.PRE_CAPABILITY, HookType.ON_STARTUP, HookType.ON_SHUTDOWN],
                capabilities=[\"demo.echo.run\"],
                dependencies=[],
                config_schema={\"type\": \"object\"},
                permissions=[\"capability:demo.echo.run\"],
            )
        )
        self.started = 0
        self.stopped = 0

    async def on_startup(self):
        self.started += 1

    async def on_shutdown(self):
        self.stopped += 1

    async def execute_tool(self, arguments):
        return {\"arguments\": arguments}

    def register_hooks(self):
        async def before_capability(context: HookContext):
            context.payload[\"plugin_id\"] = self.manifest.id
            return context.payload

        return {HookType.PRE_CAPABILITY: [before_capability]}


PLUGIN_CLASS = FixturePlugin
""".strip()
    )
    return plugin_dir


def test_loader_discovers_bundled_and_local_plugins(tmp_path: Path) -> None:
    local_root = tmp_path / "plugins"
    bundled_root = tmp_path / "bundled"
    _write_plugin(local_root, "demo.echo")
    _write_plugin(bundled_root, "bundled.echo", bundled=True)

    loader = PluginLoader(plugin_dirs=[local_root], bundled_plugin_dirs=[bundled_root])
    discovered = loader.discover()

    assert [record.manifest.id for record in discovered] == ["bundled.echo", "demo.echo"]
    assert loader.registry.require("bundled.echo").bundled is True


def test_loader_runs_full_lifecycle_and_registers_hooks(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "demo.echo")

    loader = PluginLoader(plugin_dirs=[plugin_root])
    loader.discover()

    plugin: Any = asyncio.run(loader.load("demo.echo"))
    assert loader.registry.require("demo.echo").state == PluginState.LOADED

    asyncio.run(loader.enable("demo.echo"))
    assert plugin.started == 1
    assert loader.registry.require("demo.echo").state == PluginState.ENABLED

    hook_results = asyncio.run(
        loader.hooks.emit(HookType.PRE_CAPABILITY, payload={"capability": "demo.echo.run"})
    )
    assert hook_results[0].value == {"capability": "demo.echo.run", "plugin_id": "demo.echo"}

    asyncio.run(loader.disable("demo.echo"))
    assert plugin.stopped == 1
    assert loader.registry.require("demo.echo").state == PluginState.DISABLED

    asyncio.run(loader.unload("demo.echo"))
    assert loader.registry.require("demo.echo").state == PluginState.UNLOADED
