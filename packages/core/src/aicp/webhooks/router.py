from __future__ import annotations

from .models import WebhookEvent
from .registry import WebhookRegistry


class WebhookRouter:
    def __init__(self, registry: WebhookRegistry) -> None:
        self._registry = registry

    def route(self, event: WebhookEvent) -> str | None:
        for route in self._registry.list_routes():
            if route.enabled and route.event_type == event.event_type:
                return route.handler_path
        return None
