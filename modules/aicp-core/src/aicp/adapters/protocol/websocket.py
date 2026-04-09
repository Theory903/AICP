"""WebSocket transport adapter for AICP.

Provides WebSocket-based capability execution.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.server import Server, ServerConnection

from aicp.plugins import PluginMetadata, TransportPlugin, register_transport


def _build_ws_url(
    url: str | None,
    host: str | None,
    port: int | None,
    path: str,
) -> str:
    """Build a WebSocket URL from explicit URL or host/port/path parts."""
    if url:
        return url

    resolved_host = host or "127.0.0.1"
    resolved_port = port or 8765
    resolved_path = path if path.startswith("/") else f"/{path}"
    return f"ws://{resolved_host}:{resolved_port}{resolved_path}"


@register_transport("websocket")
class WebSocketTransport(TransportPlugin):
    """WebSocket transport for real-time capability execution.

    Supports:
    - single request/response calls
    - streaming responses over a persistent client connection
    """

    def __init__(
        self,
        url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        path: str = "/ws",
        extra_headers: dict[str, str] | None = None,
        open_timeout: float = 30.0,
        close_timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.host = host
        self.port = port
        self.path = path
        self.extra_headers = dict(extra_headers or {})
        self.open_timeout = open_timeout
        self.close_timeout = close_timeout
        self._ws: ClientConnection | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="websocket-transport",
            version="1.0.0",
            description="WebSocket transport for real-time capability execution",
            tags=["websocket", "streaming", "real-time"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize WebSocket transport from config."""
        if not config:
            return

        self.url = config.get("url", self.url)
        self.host = config.get("host", self.host)
        self.port = config.get("port", self.port)
        self.path = config.get("path", self.path)
        self.open_timeout = float(config.get("open_timeout", self.open_timeout))
        self.close_timeout = float(config.get("close_timeout", self.close_timeout))

        headers = config.get("extra_headers")
        if isinstance(headers, dict):
            self.extra_headers = {str(k): str(v) for k, v in headers.items()}

    def shutdown(self) -> None:
        """Compatibility sync shutdown hook.

        Prefer awaiting close() where possible.
        """
        pass

    async def close(self) -> None:
        """Close the active WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
        self._ws = None

    def get_transport_type(self) -> str:
        return "websocket"

    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        if self._ws is not None and not self._ws.closed:
            return

        ws_url = _build_ws_url(self.url, self.host, self.port, self.path)
        self._ws = await websockets.connect(
            ws_url,
            additional_headers=self.extra_headers or None,
            open_timeout=self.open_timeout,
            close_timeout=self.close_timeout,
        )

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request via WebSocket and wait for a single response."""
        ws = await self._ensure_connection()
        await ws.send(json.dumps(request))

        message = await ws.recv()
        return self._decode_message(message)

    async def receive(self) -> dict[str, Any]:
        """Receive a response from the connected WebSocket."""
        ws = await self._ensure_connection()
        message = await ws.recv()
        return self._decode_message(message)

    async def send_stream(
        self,
        request: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a request and receive a streaming response."""
        ws = await self._ensure_connection()
        await ws.send(json.dumps(request))

        try:
            while True:
                message = await ws.recv()
                data = self._decode_message(message)
                yield data

                if data.get("type") == "end":
                    break
        except asyncio.CancelledError:
            raise
        except websockets.ConnectionClosedOK:
            return
        except websockets.ConnectionClosedError as exc:
            yield {
                "type": "error",
                "error": f"WebSocket connection closed unexpectedly: {exc}",
                "error_code": "connection_closed",
            }

    async def _ensure_connection(self) -> ClientConnection:
        """Return an active WebSocket connection."""
        await self.connect()
        if self._ws is None:
            raise RuntimeError("WebSocket connection failed")
        return self._ws

    @staticmethod
    def _decode_message(message: str | bytes) -> dict[str, Any]:
        """Decode an incoming WebSocket message."""
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        try:
            decoded = json.loads(message)
        except json.JSONDecodeError:
            return {
                "type": "message",
                "data": message,
            }

        if isinstance(decoded, dict):
            return decoded

        return {
            "type": "message",
            "data": decoded,
        }


class WebSocketServerTransport(TransportPlugin):
    """WebSocket server transport for handling incoming connections."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        path: str = "/ws",
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self._server: Server | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="websocket-server-transport",
            version="1.0.0",
            description="WebSocket server for handling incoming connections",
            tags=["websocket", "server"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize server config."""
        if not config:
            return

        self.host = config.get("host", self.host)
        self.port = int(config.get("port", self.port))
        self.path = config.get("path", self.path)

    def shutdown(self) -> None:
        """Compatibility sync shutdown hook.

        Prefer awaiting close() where possible.
        """
        pass

    async def close(self) -> None:
        """Shut down the WebSocket server."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        self._server = None

    def get_transport_type(self) -> str:
        return "websocket-server"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Use start_server() or serve_forever() for server transport.")

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use start_server() or serve_forever() for server transport.")

    async def start_server(
        self,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """Start a request-response WebSocket server.

        Args:
            handler: Async handler that accepts a decoded request dict and returns a response.
        """

        async def ws_handler(ws: ServerConnection) -> None:
            async for message in ws:
                request = self._decode_request(message)
                response = await handler(request)
                await ws.send(json.dumps(response))

        self._server = await websockets.serve(ws_handler, self.host, self.port)

    async def serve_forever(
        self,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """Start a request-response WebSocket server and run forever."""
        await self.start_server(handler)
        await asyncio.Future()

    async def start_streaming_server(
        self,
        handler: Callable[[dict[str, Any]], AsyncGenerator[Any, None] | Awaitable[AsyncGenerator[Any, None]]],
    ) -> None:
        """Start a streaming WebSocket server.

        Args:
            handler: Async handler that accepts a request dict and yields streamed responses.
        """

        async def ws_handler(ws: ServerConnection) -> None:
            async for message in ws:
                request = self._decode_request(message)
                stream = handler(request)
                if asyncio.iscoroutine(stream):
                    stream = await stream

                async for event in stream:
                    await ws.send(json.dumps(event))

        self._server = await websockets.serve(ws_handler, self.host, self.port)

    @staticmethod
    def _decode_request(message: str | bytes) -> dict[str, Any]:
        """Decode a client request into a dictionary."""
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        try:
            decoded = json.loads(message)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON message: {exc}") from exc

        if not isinstance(decoded, dict):
            raise ValueError("WebSocket request payload must be a JSON object")

        return decoded
