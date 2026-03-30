"""Notifications: webhooks, email, and Slack.

Provides notification delivery for approvals and events.
"""

import asyncio
import hashlib
import hmac
import json
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class Notification:
    """Notification payload."""
    id: str
    event_type: str
    title: str
    message: str
    data: dict[str, Any]
    priority: str = "normal"  # low, normal, high, urgent


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send notification."""
        pass


class WebhookChannel(NotificationChannel):
    """Webhook notification channel."""

    def __init__(
        self,
        url: str,
        secret: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        self.url = url
        self.secret = secret
        self.headers = headers or {}
        self.timeout = timeout

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
            payload["signature"] = self._sign(payload)
            headers["X-Webhook-Signature"] = payload["signature"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    return response.status >= 200 and response.status < 300
        except Exception:
            return False

    def _sign(self, payload: dict) -> str:
        """Sign webhook payload."""
        content = json.dumps(payload, sort_keys=True)
        return hmac.new(
            self.secret.encode(),
            content.encode(),
            hashlib.sha256,
        ).hexdigest()


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    def __init__(self, webhook_url: str, channel: str | None = None):
        self.webhook_url = webhook_url
        self.channel = channel

    async def send(self, notification: Notification) -> bool:
        """Send notification to Slack."""
        color = {
            "low": "#36a64f",
            "normal": "#4a90e2",
            "high": "#f5a623",
            "urgent": "#e53935",
        }.get(notification.priority, "#4a90e2")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": notification.title,
                    "text": notification.message,
                    "fields": [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in notification.data.items()
                    ],
                }
            ]
        }

        if self.channel:
            payload["channel"] = self.channel

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                ) as response:
                    return response.status == 200
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
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls

    async def send(self, notification: Notification) -> bool:
        """Send notification via email."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg["From"] = self.from_address
        msg["To"] = ",".join(notification.data.get("recipients", []))
        msg["Subject"] = notification.title

        body = f"""
{notification.message}

Event: {notification.event_type}
Priority: {notification.priority}

Additional Data:
{json.dumps(notification.data, indent=2)}
"""
        msg.attach(MIMEText(body, "plain"))

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_sync,
                msg,
                notification.data.get("recipients", []),
            )
            return True
        except Exception:
            return False

    def _send_sync(self, msg, recipients: list[str]) -> None:
        """Send email synchronously."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)


class NotificationService:
    """Central notification service."""

    def __init__(self):
        self._channels: dict[str, NotificationChannel] = {}
        self._event_subscriptions: dict[str, list[str]] = {}  # event -> channel names

    def add_channel(self, name: str, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels[name] = channel

    def subscribe(self, event_type: str, channel_name: str) -> None:
        """Subscribe channel to event type."""
        if event_type not in self._event_subscriptions:
            self._event_subscriptions[event_type] = []
        if channel_name not in self._event_subscriptions[event_type]:
            self._event_subscriptions[event_type].append(channel_name)

    async def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        data: dict[str, Any],
        priority: str = "normal",
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
        results = {}

        for name in channel_names:
            channel = self._channels.get(name)
            if channel:
                success = await channel.send(notification)
                results[name] = success

        return results


def create_webhook_handler(app, notification_service: NotificationService, path: str = "/webhooks") -> None:
    """Create webhook endpoint for external triggers."""
    from fastapi import APIRouter, HTTPException, Request

    router = APIRouter()

    @router.post(path)
    async def handle_webhook(request: Request):
        """Handle incoming webhook."""
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        event_type = payload.get("event")
        if not event_type:
            raise HTTPException(status_code=400, detail="Missing event type")

        await notification_service.notify(
            event_type=event_type,
            title=payload.get("title", "Webhook Event"),
            message=payload.get("message", ""),
            data=payload.get("data", payload),
            priority=payload.get("priority", "normal"),
        )

        return {"status": "received"}

    app.include_router(router)
