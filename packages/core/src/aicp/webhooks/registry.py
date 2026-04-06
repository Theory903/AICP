from __future__ import annotations

from .models import WebhookRoute


class WebhookRegistry:
    def __init__(self) -> None:
        self._routes: dict[str, WebhookRoute] = {}
        self._handlers: dict[str, str] = {}

    def register_route(self, route: WebhookRoute) -> None:
        self._routes[route.path] = route
        self._handlers[route.event_type] = route.handler_path

    def get_route(self, path: str) -> WebhookRoute | None:
        return self._routes.get(path)

    def list_routes(self) -> list[WebhookRoute]:
        return list(self._routes.values())

    def get_handler_path(self, event_type: str) -> str | None:
        return self._handlers.get(event_type)

    def enable_route(self, path: str) -> None:
        if path in self._routes:
            self._routes[path].enabled = True

    def disable_route(self, path: str) -> None:
        if path in self._routes:
            self._routes[path].enabled = False
