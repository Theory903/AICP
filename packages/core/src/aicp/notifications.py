"""Notifications: webhooks, email, and Slack.

Provides notification delivery for approvals and events.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import smtplib
import ssl
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Literal

import aiohttp

NotificationPriority = Literal["low", "normal", "high", "urgent"]


class NotificationError(Exception):
    """Base notification error."""


@dataclass(slots=True)
class Notification:
    """Notification payload."""

    id: str
    event_type: str
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = "normal"

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Notification id cannot be empty")
        if not self.event_type.strip():
            raise ValueError("Notification event_type cannot be empty")
        if not self.title.strip():
            raise ValueError("Notification title cannot be empty")
        if self.priority not in {"low", "normal", "high", "urgent"}:
            raise ValueError(f"Invalid priority: {self.priority}")


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send notification."""


class WebhookChannel(NotificationChannel):
    """Webhook notification channel."""

    def __init__(
        self,
        url: str,
        secret: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        if not url.strip():
            raise ValueError("url cannot be empty")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.url = url
        self.secret = secret
        self.headers = headers.copy() if headers else {}
        self.timeout = timeout
        self._session = session

    async def send(self, notification: Notification) -> bool:
        """Send notification via webhook."""
        payload = {
            "id": notification.id,
            "event": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "priority": notification.priority,
        }

        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"

        if self.secret:
            signature = self._sign(payload)
            headers["X-Webhook-Signature"] = signature

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            if self._session is not None:
                async with self._session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                ) as response:
                    return 200 <= response.status < 300

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                ) as response:
                    return 200 <= response.status < 300
        except Exception:
            return False

    def _sign(self, payload: dict[str, Any]) -> str:
        """Sign webhook payload."""
        if self.secret is None:
            raise NotificationError("Cannot sign payload without a secret")
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            self.secret.encode("utf-8"),
            content.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    def __init__(
        self,
        webhook_url: str,
        channel: str | None = None,
        username: str | None = None,
        timeout: float = 30.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        if not webhook_url.strip():
            raise ValueError("webhook_url cannot be empty")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.timeout = timeout
        self._session = session

    async def send(self, notification: Notification) -> bool:
        """Send notification to Slack."""
        color = {
            "low": "#36a64f",
            "normal": "#4a90e2",
            "high": "#f5a623",
            "urgent": "#e53935",
        }[notification.priority]

        fields = [
            {"title": str(key), "value": str(value), "short": True}
            for key, value in notification.data.items()
        ]

        payload: dict[str, Any] = {
            "attachments": [
                {
                    "color": color,
                    "title": notification.title,
                    "text": notification.message,
                    "fields": fields,
                }
            ]
        }

        if self.channel:
            payload["channel"] = self.channel
        if self.username:
            payload["username"] = self.username

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            if self._session is not None:
                async with self._session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=timeout,
                ) as response:
                    return 200 <= response.status < 300

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                ) as response:
                    return 200 <= response.status < 300
        except Exception:
            return False


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: str | None = None,
        password: str | None = None,
        from_address: str = "aicp@example.com",
        use_tls: bool = True,
        timeout: float = 30.0,
    ) -> None:
        if not smtp_host.strip():
            raise ValueError("smtp_host cannot be empty")
        if smtp_port <= 0:
            raise ValueError("smtp_port must be > 0")
        if not from_address.strip():
            raise ValueError("from_address cannot be empty")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls
        self.timeout = timeout

    async def send(self, notification: Notification) -> bool:
        """Send notification via email."""
        recipients = self._extract_recipients(notification.data.get("recipients"))
        if not recipients:
            return False

        message = self._build_message(notification, recipients)

        try:
            await asyncio.to_thread(self._send_sync, message, recipients)
            return True
        except Exception:
            return False

    def _extract_recipients(self, raw: Any) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, str):
            recipients = [raw]
        elif isinstance(raw, Iterable):
            recipients = [str(item) for item in raw]
        else:
            return []

        return [recipient.strip() for recipient in recipients if str(recipient).strip()]

    def _build_message(
        self,
        notification: Notification,
        recipients: list[str],
    ) -> EmailMessage:
        body = (
            f"{notification.message}\n\n"
            f"Event: {notification.event_type}\n"
            f"Priority: {notification.priority}\n\n"
            f"Additional Data:\n"
            f"{json.dumps(notification.data, indent=2, default=str)}"
        )

        msg = EmailMessage()
        msg["From"] = self.from_address
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = notification.title
        msg.set_content(body)
        return msg

    def _send_sync(self, message: EmailMessage, recipients: list[str]) -> None:
        """Send email synchronously."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
            server.ehlo()
            if self.use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(message, to_addrs=recipients)


class NotificationService:
    """Central notification service."""

    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel] = {}
        self._event_subscriptions: dict[str, list[str]] = {}

    def add_channel(self, name: str, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Channel name cannot be empty")
        self._channels[cleaned] = channel

    def subscribe(self, event_type: str, channel_name: str) -> None:
        """Subscribe channel to an event type."""
        event_key = event_type.strip()
        channel_key = channel_name.strip()

        if not event_key:
            raise ValueError("event_type cannot be empty")
        if not channel_key:
            raise ValueError("channel_name cannot be empty")
        if channel_key not in self._channels:
            raise KeyError(f"Unknown channel: {channel_key}")

        if event_key not in self._event_subscriptions:
            self._event_subscriptions[event_key] = []

        if channel_key not in self._event_subscriptions[event_key]:
            self._event_subscriptions[event_key].append(channel_key)

    def unsubscribe(self, event_type: str, channel_name: str) -> None:
        """Remove a channel subscription for an event type."""
        subscribed = self._event_subscriptions.get(event_type, [])
        if channel_name in subscribed:
            subscribed.remove(channel_name)
        if not subscribed and event_type in self._event_subscriptions:
            del self._event_subscriptions[event_type]

    async def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        data: dict[str, Any],
        priority: NotificationPriority = "normal",
    ) -> dict[str, bool]:
        """Send notification to all subscribed channels."""
        import secrets

        notification = Notification(
            id=secrets.token_hex(8),
            event_type=event_type,
            title=title,
            message=message,
            data=data,
            priority=priority,
        )

        channel_names = self._event_subscriptions.get(event_type, [])
        if not channel_names:
            return {}

        async def _send_one(name: str) -> tuple[str, bool]:
            channel = self._channels.get(name)
            if channel is None:
                return name, False
            try:
                success = await channel.send(notification)
                return name, success
            except Exception:
                return name, False

        results = await asyncio.gather(*(_send_one(name) for name in channel_names))
        return dict(results)


def create_webhook_handler(
    app: Any,
    notification_service: NotificationService,
    path: str = "/webhooks",
) -> None:
    """Create webhook endpoint for external triggers."""
    from fastapi import APIRouter, HTTPException, Request

    router = APIRouter()

    @router.post(path)
    async def handle_webhook(request: Request) -> dict[str, str]:
        """Handle incoming webhook."""
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Webhook payload must be an object")

        event_type = payload.get("event")
        if not isinstance(event_type, str) or not event_type.strip():
            raise HTTPException(status_code=400, detail="Missing event type")

        await notification_service.notify(
            event_type=event_type,
            title=str(payload.get("title", "Webhook Event")),
            message=str(payload.get("message", "")),
            data=payload.get("data", payload) if isinstance(payload.get("data", payload), dict) else payload,
            priority=payload.get("priority", "normal"),
        )

        return {"status": "received"}

    app.include_router(router)