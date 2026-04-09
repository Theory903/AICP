from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .message import ChannelMessage, ChannelResponse


class ChannelError(Exception):
    pass


class ChannelUnavailableError(ChannelError):
    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        super().__init__(f"Channel unavailable: {channel_id}")


ChannelUnavailable = ChannelUnavailableError


class BaseChannel(ABC):
    def __init__(self, channel_id: str, config: dict[str, Any] | None = None) -> None:
        self.channel_id = channel_id
        self.config = config or {}
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def send(self, message: ChannelResponse) -> None:
        raise NotImplementedError

    @abstractmethod
    async def receive(self) -> ChannelMessage | None:
        raise NotImplementedError
