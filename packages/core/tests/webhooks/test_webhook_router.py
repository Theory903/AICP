from __future__ import annotations

from aicp.webhooks import WebhookEvent, WebhookRegistry, WebhookRoute, WebhookRouter


def test_route_finds_handler() -> None:
    registry = WebhookRegistry()
    registry.register_route(
        WebhookRoute(
            path="providers/github",
            event_type="push",
            handler_path="handlers.github.handle_push",
        )
    )
    router = WebhookRouter(registry)

    route = router.route(
        WebhookEvent(
            id="evt_1",
            source="github",
            event_type="push",
            payload={"id": "evt_1"},
        )
    )

    assert route == "handlers.github.handle_push"


def test_route_returns_none_when_no_handler() -> None:
    registry = WebhookRegistry()
    router = WebhookRouter(registry)

    route = router.route(
        WebhookEvent(
            id="evt_1",
            source="github",
            event_type="push",
            payload={"id": "evt_1"},
        )
    )

    assert route is None
