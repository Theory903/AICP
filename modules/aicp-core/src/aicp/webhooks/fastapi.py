from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response

from .handlers import WebhookHandler
from .models import WebhookEvent, WebhookSignatureError
from .registry import WebhookRegistry


def create_webhook_app(secret: str | None = None) -> tuple[FastAPI, WebhookHandler, WebhookRegistry]:
    app = FastAPI()
    handler = WebhookHandler(secret)
    registry = WebhookRegistry()

    @app.post("/{path:path}")
    async def handle_webhook(path: str, request: Request) -> Response:
        body = await request.body()
        payload = body.decode()
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")

        try:
            if not handler.verify_signature(payload, signature, timestamp):
                raise HTTPException(status_code=401, detail="Invalid signature")
        except WebhookSignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        try:
            data: dict[str, Any] = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

        event = WebhookEvent(
            id=data.get("id", ""),
            source=path,
            event_type=data.get("type", "unknown"),
            payload=data,
            headers=dict(request.headers),
        )
        result = await handler.handle(event)
        return Response(content=str(result), status_code=200)

    return app, handler, registry
