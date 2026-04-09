from __future__ import annotations

import sys
from collections import deque
from typing import Any, TextIO

from .base import BaseChannel, ChannelUnavailable
from .message import ChannelMessage, ChannelResponse


class ConsoleChannel(BaseChannel):
    def __init__(
        self,
        channel_id: str,
        config: dict[str, Any] | None = None,
        *,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> None:
        super().__init__(channel_id, config)
        self._input = input_stream or sys.stdin
        self._output = output_stream or sys.stdout

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def health_check(self) -> bool:
        return self._connected

    async def send(self, message: ChannelResponse) -> None:
        if not self._connected:
            raise ChannelUnavailable(self.channel_id)
        self._output.write(f"[{message.channel_id}] {message.content}\n")
        self._output.flush()

    async def receive(self) -> ChannelMessage | None:
        if not self._connected:
            raise ChannelUnavailable(self.channel_id)
        line = self._input.readline()
        content = line.strip()
        if not content:
            return None
        return ChannelMessage(channel_id=self.channel_id, sender_id="console", content=content)


class WebhookChannel(BaseChannel):
    def __init__(self, channel_id: str, webhook_url: str, config: dict[str, Any] | None = None) -> None:
        merged_config = dict(config or {})
        merged_config.setdefault("webhook_url", webhook_url)
        super().__init__(channel_id, merged_config)
        self.webhook_url = webhook_url.strip()
        self._messages: deque[ChannelMessage] = deque()
        self.last_response: ChannelResponse | None = None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def health_check(self) -> bool:
        return self._connected and bool(self.webhook_url)

    async def send(self, message: ChannelResponse) -> None:
        if not await self.health_check():
            raise ChannelUnavailable(self.channel_id)
        self.last_response = message

    async def receive(self) -> ChannelMessage | None:
        if not self._connected:
            raise ChannelUnavailable(self.channel_id)
        if not self._messages:
            return None
        return self._messages.popleft()

    def accept(self, message: ChannelMessage) -> None:
        if message.channel_id != self.channel_id:
            raise ValueError("message channel_id does not match webhook channel")
        self._messages.append(message)

    def accept_payload(self, payload: dict[str, Any]) -> ChannelMessage:
        required = {"sender_id", "content"}
        missing = sorted(required.difference(payload))
        if missing:
            raise ValueError(f"invalid webhook payload missing keys: {', '.join(missing)}")

        message = ChannelMessage(
            channel_id=self.channel_id,
            sender_id=str(payload["sender_id"]),
            content=str(payload["content"]),
            metadata=dict(payload.get("metadata") or {}),
            attachments=list(payload.get("attachments") or []),
        )
        self.accept(message)
        return message


class ApiChannel(BaseChannel):
    def __init__(self, channel_id: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(channel_id, config)
        self._messages: deque[ChannelMessage] = deque()
        self.last_response: ChannelResponse | None = None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def reconnect(self) -> None:
        await self.disconnect()
        await self.connect()

    async def health_check(self) -> bool:
        return self._connected

    async def send(self, message: ChannelResponse) -> None:
        if not self._connected:
            raise ChannelUnavailable(self.channel_id)
        self.last_response = message

    async def receive(self) -> ChannelMessage | None:
        if not self._connected:
            raise ChannelUnavailable(self.channel_id)
        if not self._messages:
            return None
        return self._messages.popleft()

    def push_message(self, message: ChannelMessage) -> None:
        if message.channel_id != self.channel_id:
            raise ValueError("message channel_id does not match api channel")
        self._messages.append(message)
