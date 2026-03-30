"""SSE (Server-Sent Events) transport adapter for AICP.

Provides streaming capability execution via Server-Sent Events.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from aicp.plugins import PluginMetadata, TransportPlugin, register_transport


@register_transport("sse")
class SSETransport(TransportPlugin):
    """SSE transport for streaming capability execution.

    Supports both client (receiving) and server (sending) SSE streams.
    """

    def __init__(self, url: str | None = None, event_endpoint: str | None = None):
        self.url = url
        self.event_endpoint = event_endpoint or "/events"
        self._session = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sse-transport",
            version="1.0.0",
            description="Server-Sent Events transport for streaming execution",
            tags=["sse", "streaming", "events"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self.url = config.get("url", self.url)
            self.event_endpoint = config.get("event_endpoint", self.event_endpoint)

    def shutdown(self) -> None:
        if self._session:
            asyncio.create_task(self._session.close())

    def get_transport_type(self) -> str:
        return "sse"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request, receive final response."""
        import aiohttp

        url = f"{self.url}{self.event_endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request) as response:
                return await response.json()

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use stream_events() for SSE")

    async def stream_events(self, request: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream events from server.

        Args:
            request: Request to send.

        Yields:
            Event data as dict.
        """
        import aiohttp

        url = f"{self.url}{self.event_endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request) as response:
                async for line in response.content:
                    decoded = line.decode().strip()
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]":
                            break
                        yield json.loads(data)


class SSEServerTransport(TransportPlugin):
    """SSE server transport for sending streaming events."""

    def __init__(self, host: str = "localhost", port: int = 8080, path: str = "/events"):
        self.host = host
        self.port = port
        self.path = path
        self._server = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sse-server-transport",
            version="1.0.0",
            description="SSE server for streaming events to clients",
            tags=["sse", "server", "streaming"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self.host = config.get("host", self.host)
            self.port = config.get("port", self.port)
            self.path = config.get("path", self.path)

    def shutdown(self) -> None:
        if self._server:
            self._server.close()

    def get_transport_type(self) -> str:
        return "sse-server"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Use serve() for SSE server")

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use serve() for SSE server")

    async def serve(
        self,
        handler: callable,
    ) -> None:
        """Start SSE server.

        Args:
            handler: Async function that handles requests and yields events.
        """
        from aiohttp import web

        async def sse_handler(request):
            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
            await response.prepare(request)

            try:
                async for event in handler(request):
                    if isinstance(event, dict):
                        data = json.dumps(event)
                    else:
                        data = str(event)
                    await response.write(f"data: {data}\n\n".encode())
                    await response.drain()
            except asyncio.CancelledError:
                pass
            finally:
                await response.write(b"data: [DONE]\n\n")
                await response.write_eof()

        app = web.Application()
        app.router.add_post(self.path, sse_handler)

        self._server = await app.make_handler()
        runner = web.AppRunner(self._server)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
