import asyncio
import json
from typing import Callable, Optional


class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self._ws: Optional[asyncio.WebSocketServer] = None
        self._connected = False
        self._handlers: dict[str, Callable] = {}

    async def connect(self):
        self._connected = True

    async def send(self, message: dict):
        if not self._connected:
            raise ConnectionError("Not connected")

    async def receive(self) -> dict:
        return {}

    def is_connected(self) -> bool:
        return self._connected

    def on(self, event: str, handler: Callable):
        self._handlers[event] = handler

    async def emit(self, event: str, data: dict):
        handler = self._handlers.get(event)
        if handler:
            handler(data)


class RemoteSessionManager:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.client = WebSocketClient(ws_url)

    async def connect(self):
        await self.client.connect()

    def is_connected(self) -> bool:
        return self.client.is_connected()

    async def share_session(self, session_id: str) -> str:
        url = f"wss://aicp.sh/session/{session_id}"
        return url

    async def get_shared_session(self, session_id: str) -> dict:
        return {"session_id": session_id, "status": "shared"}
