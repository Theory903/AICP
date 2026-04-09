from pathlib import Path

import pytest

from aicp.plugins import PluginManifest, PluginRegistry, PluginState, PluginType


def _manifest(version: str = "1.0.0") -> PluginManifest:
    return PluginManifest(
        id="demo.echo",
        name="Demo Echo",
        version=version,
        description="Echo capability plugin",
        author="Demo Team",
        plugin_type=PluginType.TOOL,
        hooks=[],
        capabilities=["demo.echo"],
        dependencies=[],
        config_schema={"type": "object"},
    )


def test_registry_tracks_version_path_and_enablement() -> None:
    registry = PluginRegistry()
    record = registry.register(_manifest(), Path("/plugins/demo.echo"), bundled=True)

    assert record.version == "1.0.0"
    assert record.bundled is True
    assert record.state == PluginState.DISCOVERED

    registry.mark_loaded("demo.echo")
    registry.enable("demo.echo")

    loaded = registry.require("demo.echo")
    assert loaded.state == PluginState.ENABLED
    assert registry.get_version("demo.echo") == "1.0.0"
    assert [item.manifest.id for item in registry.list_enabled()] == ["demo.echo"]

    registry.disable("demo.echo")
    assert registry.require("demo.echo").state == PluginState.DISABLED


def test_registry_rejects_duplicate_plugin_ids_without_overwrite() -> None:
    registry = PluginRegistry()
    registry.register(_manifest("1.0.0"), Path("/plugins/demo.echo"))

    with pytest.raises(ValueError):
        registry.register(_manifest("2.0.0"), Path("/plugins/demo.echo-v2"), overwrite=False)
