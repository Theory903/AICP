from __future__ import annotations

from aicp.webhooks import WebhookRegistry, WebhookRoute


def test_register_route() -> None:
    registry = WebhookRegistry()
    route = WebhookRoute(
        path="providers/github",
        event_type="push",
        handler_path="handlers.github.handle_push",
    )

    registry.register_route(route)

    assert registry.get_route("providers/github") == route
    assert registry.get_handler_path("push") == "handlers.github.handle_push"


def test_list_routes() -> None:
    registry = WebhookRegistry()
    first = WebhookRoute(
        path="providers/github",
        event_type="push",
        handler_path="handlers.github.handle_push",
    )
    second = WebhookRoute(
        path="providers/stripe",
        event_type="invoice.paid",
        handler_path="handlers.stripe.handle_invoice_paid",
    )

    registry.register_route(first)
    registry.register_route(second)

    assert registry.list_routes() == [first, second]


def test_enable_disable() -> None:
    registry = WebhookRegistry()
    route = WebhookRoute(
        path="providers/github",
        event_type="push",
        handler_path="handlers.github.handle_push",
    )
    registry.register_route(route)

    registry.disable_route("providers/github")
    disabled_route = registry.get_route("providers/github")
    assert disabled_route is not None
    assert disabled_route.enabled is False

    registry.enable_route("providers/github")
    enabled_route = registry.get_route("providers/github")
    assert enabled_route is not None
    assert enabled_route.enabled is True
