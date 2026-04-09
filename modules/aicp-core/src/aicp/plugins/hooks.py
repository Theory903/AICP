from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .manifest import HookType


class HookContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    hook: HookType
    plugin_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    execution_id: str | None = None


@dataclass(slots=True)
class RegisteredHook:
    hook: HookType
    plugin_id: str
    handler: Callable[[HookContext], Any]
    priority: int = 100


@dataclass(slots=True)
class HookResult:
    hook: HookType
    plugin_id: str
    value: Any


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[HookType, list[RegisteredHook]] = {hook: [] for hook in HookType}

    def register(
        self,
        hook: HookType,
        plugin_id: str,
        handler: Callable[[HookContext], Any],
        *,
        priority: int = 100,
    ) -> None:
        self._hooks.setdefault(hook, []).append(
            RegisteredHook(hook=hook, plugin_id=plugin_id, handler=handler, priority=priority)
        )
        self._hooks[hook].sort(key=lambda item: (item.priority, item.plugin_id))

    def unregister_plugin(self, plugin_id: str) -> None:
        for hook in HookType:
            self._hooks[hook] = [item for item in self._hooks.get(hook, []) if item.plugin_id != plugin_id]

    async def emit(
        self,
        hook: HookType,
        *,
        payload: dict[str, Any],
        execution_id: str | None = None,
    ) -> list[HookResult]:
        results: list[HookResult] = []
        for item in self._hooks.get(hook, []):
            context = HookContext(
                hook=hook,
                plugin_id=item.plugin_id,
                payload=dict(payload),
                execution_id=execution_id,
            )
            value = item.handler(context)
            if inspect.isawaitable(value):
                value = await value
            results.append(HookResult(hook=hook, plugin_id=item.plugin_id, value=value))
        return results
