import asyncio
import json
from typing import Callable, Optional


class STTClient:
    def __init__(self, ws_url: str, api_key: str):
        self.ws_url = ws_url
        self.api_key = api_key
        self._ws: Optional[asyncio.WebSocketServer] = None
        self._on_transcript: Optional[Callable] = None
        self._connected = False

    async def connect(self):
        self._connected = True

    async def send_audio(self, audio_chunk: bytes):
        pass

    async def receive_transcript(self) -> str:
        return ""

    def on_transcript(self, callback: Callable):
        self._on_transcript = callback

    async def close(self):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected
