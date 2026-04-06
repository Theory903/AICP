from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .manifest import PluginManifest


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNLOADED = "unloaded"


@dataclass(slots=True)
class PluginRecord:
    manifest: PluginManifest
    path: Path
    version: str
    bundled: bool = False
    state: PluginState = PluginState.DISCOVERED


class PluginRegistry:
    def __init__(self) -> None:
        self._records: dict[str, PluginRecord] = {}

    def register(
        self,
        manifest: PluginManifest,
        path: Path,
        bundled: bool = False,
        *,
        overwrite: bool = True,
    ) -> PluginRecord:
        if not overwrite and manifest.id in self._records:
            raise ValueError(f"Plugin already registered: {manifest.id}")
        record = PluginRecord(
            manifest=manifest,
            path=path,
            version=manifest.version,
            bundled=bundled,
            state=PluginState.DISCOVERED,
        )
        self._records[manifest.id] = record
        return record

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._records.get(plugin_id)

    def require(self, plugin_id: str) -> PluginRecord:
        record = self.get(plugin_id)
        if record is None:
            raise KeyError(f"Plugin not found: {plugin_id}")
        return record

    def list_all(self) -> list[PluginRecord]:
        return [self._records[key] for key in sorted(self._records)]

    def list_enabled(self) -> list[PluginRecord]:
        return [record for record in self.list_all() if record.state == PluginState.ENABLED]

    def get_version(self, plugin_id: str) -> str | None:
        record = self.get(plugin_id)
        return None if record is None else record.version

    def mark_loaded(self, plugin_id: str) -> None:
        self.require(plugin_id).state = PluginState.LOADED

    def enable(self, plugin_id: str) -> None:
        self.require(plugin_id).state = PluginState.ENABLED

    def disable(self, plugin_id: str) -> None:
        self.require(plugin_id).state = PluginState.DISABLED

    def unload(self, plugin_id: str) -> None:
        self.require(plugin_id).state = PluginState.UNLOADED
