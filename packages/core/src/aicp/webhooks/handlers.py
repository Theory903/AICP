from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Awaitable, Callable

from .models import WebhookEvent, WebhookSignatureError, WebhookValidationError


class WebhookHandler:
    def __init__(self, secret: str | None = None) -> None:
        self.secret = secret
        self._handlers: dict[str, Callable[[WebhookEvent], Awaitable[dict[str, Any]]]] = {}

    def register(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Awaitable[dict[str, Any]]],
    ) -> None:
        self._handlers[event_type] = handler

    async def handle(self, event: WebhookEvent) -> dict[str, Any]:
        if not event.id:
            raise WebhookValidationError("Webhook event id is required")
        if not event.event_type:
            raise WebhookValidationError("Webhook event type is required")

        handler = self._handlers.get(event.event_type)
        if handler is None:
            return {"status": "no_handler", "event_type": event.event_type}
        return await handler(event)

    def verify_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        if not self.secret:
            return True

        if timestamp:
            try:
                ts = int(timestamp)
            except ValueError as exc:
                raise WebhookSignatureError("Invalid timestamp") from exc
            if abs(time.time() - ts) > 300:
                raise WebhookSignatureError("Timestamp expired")

        expected = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
