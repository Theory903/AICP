from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from aicp.webhooks import WebhookEvent, WebhookHandler
from aicp.webhooks.models import WebhookSignatureError


@pytest.mark.asyncio
async def test_register_and_handle() -> None:
    handler = WebhookHandler()

    async def process(event: WebhookEvent) -> dict[str, str]:
        return {"status": "handled", "event_id": event.id}

    handler.register("order.created", process)

    result = await handler.handle(
        WebhookEvent(
            id="evt_1",
            source="orders",
            event_type="order.created",
            payload={"id": "evt_1"},
        )
    )

    assert result == {"status": "handled", "event_id": "evt_1"}


def test_verify_signature_accepts_valid() -> None:
    secret = "top-secret"
    payload = '{"id":"evt_1"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    handler = WebhookHandler(secret)

    assert handler.verify_signature(payload, signature, timestamp) is True


def test_verify_signature_rejects_invalid() -> None:
    handler = WebhookHandler("top-secret")

    assert handler.verify_signature('{"id":"evt_1"}', "bad-signature", str(int(time.time()))) is False


def test_verify_signature_rejects_expired_timestamp() -> None:
    handler = WebhookHandler("top-secret")
    old_timestamp = str(int(time.time()) - 301)

    with pytest.raises(WebhookSignatureError, match="Timestamp expired"):
        handler.verify_signature('{"id":"evt_1"}', "bad-signature", old_timestamp)
