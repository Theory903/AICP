from enum import Enum
from typing import Any, Callable, Optional


class HookEvent(str, Enum):
    BEFORE_QUERY = "beforeQuery"
    AFTER_QUERY = "afterQuery"
    BEFORE_TOOL = "beforeTool"
    AFTER_TOOL = "afterTool"
    ON_ERROR = "onError"
    SESSION_START = "sessionStart"
    SESSION_END = "sessionEnd"


class HookRegistry:
    def __init__(self):
        self._hooks: dict[HookEvent, list[Callable]] = {}

    def register(self, event: HookEvent, handler: Callable):
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    def trigger(self, event: HookEvent, context: dict[str, Any]):
        for handler in self._hooks.get(event, []):
            handler(context)

    def unregister(self, event: HookEvent, handler: Callable):
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h != handler]