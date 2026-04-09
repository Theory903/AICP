from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .hooks import HookContext
from .manifest import HookType, PluginManifest


class BasePlugin:
    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest
        self._config: dict[str, Any] = {}

    async def setup(self, config: dict[str, Any] | None = None) -> None:
        self._config = dict(config or {})

    async def on_startup(self) -> None:
        return None

    async def on_shutdown(self) -> None:
        return None

    def register_hooks(self) -> dict[HookType, list[Callable[[HookContext], Any]]]:
        return {}


class BaseChannelPlugin(BasePlugin):
    async def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


class BaseProviderPlugin(BasePlugin):
    async def provide(self, request: dict[str, Any]) -> dict[str, Any]:
        return request


class BaseToolPlugin(BasePlugin):
    async def execute_tool(self, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError


class BaseSkillPlugin(BasePlugin):
    async def execute_skill(self, arguments: dict[str, Any]) -> Any:
        raise NotImplementedError
