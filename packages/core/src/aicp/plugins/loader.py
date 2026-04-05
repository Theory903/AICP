from pathlib import Path
from typing import Optional

from .hooks import HookRegistry
from .manifest import PluginManifest


class PluginLoader:
    def __init__(self, plugin_dirs: list[Path]):
        self.plugin_dirs = plugin_dirs

    def discover(self) -> list[tuple[PluginManifest, Path]]:
        plugins = []
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            for entry in plugin_dir.iterdir():
                if entry.is_dir():
                    manifest_file = entry / "manifest.json"
                    if manifest_file.exists():
                        try:
                            import json
                            data = json.loads(manifest_file.read_text())
                            manifest = PluginManifest.model_validate(data)
                            plugins.append((manifest, entry))
                        except Exception:
                            continue
        return plugins

    def load_plugin(self, path: Path) -> Optional[PluginManifest]:
        manifest_file = path / "manifest.json"
        if not manifest_file.exists():
            return None
        try:
            import json
            data = json.loads(manifest_file.read_text())
            return PluginManifest.model_validate(data)
        except Exception:
            return None