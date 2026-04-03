"""SSE (Server-Sent Events) transport adapter for AICP.

Provides streaming capability execution via Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

import aiohttp
from aiohttp import web

from aicp.plugins import PluginMetadata, TransportPlugin, register_transport


def _join_url(base: str | None, path: str) -> str:
    """Join a base URL and path safely."""
    if not base:
        return path
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


@register_transport("sse")
class SSETransport(TransportPlugin):
    """SSE transport for streaming capability execution.

    Supports:
    - request/response via POST for final results
    - streaming event consumption via SSE
    """

    def __init__(
        self,
        url: str | None = None,
        event_endpoint: str = "/events",
        timeout_seconds: float = 60.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.event_endpoint = event_endpoint
        self.timeout_seconds = timeout_seconds
        self.headers = dict(headers or {})
        self._session: aiohttp.ClientSession | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sse-transport",
            version="1.0.0",
            description="Server-Sent Events transport for streaming execution",
            tags=["sse", "streaming", "events"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize transport from config."""
        if not config:
            return

        self.url = config.get("url", self.url)
        self.event_endpoint = config.get("event_endpoint", self.event_endpoint)
        self.timeout_seconds = float(config.get("timeout_seconds", self.timeout_seconds))

        config_headers = config.get("headers")
        if isinstance(config_headers, dict):
            self.headers = {str(k): str(v) for k, v in config_headers.items()}

    def shutdown(self) -> None:
        """Compatibility sync shutdown hook.

        Prefer awaiting close() where possible.
        """
        pass

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    def get_transport_type(self) -> str:
        return "sse"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request and receive a final JSON response."""
        url = _join_url(self.url, self.event_endpoint)
        session = await self._get_session()

        async with session.post(url, json=request, headers=self._build_headers()) as response:
            if response.status >= 400:
                body = await response.text()
                return {
                    "success": False,
                    "error": f"SSE request failed with status {response.status}",
                    "error_code": "http_error",
                    "status_code": response.status,
                    "body": body,
                }

            try:
                data = await response.json()
            except Exception:
                text = await response.text()
                return {
                    "success": False,
                    "error": "Expected JSON response from SSE endpoint",
                    "error_code": "invalid_response",
                    "body": text,
                }

            return {
                "success": True,
                "data": data,
            }

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use stream_events() for SSE streams.")

    async def stream_events(
        self,
        request: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream SSE events from the server.

        Args:
            request: Request payload to send.

        Yields:
            Parsed SSE event dictionaries.
        """
        url = _join_url(self.url, self.event_endpoint)
        session = await self._get_session()

        async with session.post(
            url,
            json=request,
            headers=self._build_headers(accept_sse=True),
        ) as response:
            if response.status >= 400:
                body = await response.text()
                yield {
                    "type": "error",
                    "error": f"SSE stream failed with status {response.status}",
                    "error_code": "http_error",
                    "status_code": response.status,
                    "body": body,
                }
                return

            event_name: str | None = None
            data_lines: list[str] = []

            async for raw_line in response.content:
                line = raw_line.decode("utf-8").strip()

                if not line:
                    if not data_lines:
                        continue

                    payload = "\n".join(data_lines)
                    data_lines.clear()

                    if payload == "[DONE]":
                        break

                    parsed = self._parse_event_payload(payload)
                    if event_name is not None:
                        parsed.setdefault("event", event_name)
                    yield parsed
                    event_name = None
                    continue

                if line.startswith(":"):
                    continue  # comment/heartbeat

                if line.startswith("event:"):
                    event_name = line[len("event:") :].strip()
                    continue

                if line.startswith("data:"):
                    data_lines.append(line[len("data:") :].strip())
                    continue

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _build_headers(self, *, accept_sse: bool = False) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self.headers)
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Accept", "text/event-stream" if accept_sse else "application/json")
        return headers

    @staticmethod
    def _parse_event_payload(payload: str) -> dict[str, Any]:
        """Parse SSE payload as JSON when possible."""
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
            return {"type": "message", "data": parsed}
        except json.JSONDecodeError:
            return {"type": "message", "data": payload}


class SSEServerTransport(TransportPlugin):
    """SSE server transport for sending streaming events."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        path: str = "/events",
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sse-server-transport",
            version="1.0.0",
            description="SSE server for streaming events to clients",
            tags=["sse", "server", "streaming"],
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
        """Shutdown the server runner."""
        if self._runner is not None:
            await self._runner.cleanup()
        self._runner = None
        self._site = None

    def get_transport_type(self) -> str:
        return "sse-server"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Use serve() for SSE server transport.")

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use serve() for SSE server transport.")

    async def serve(
        self,
        handler: Callable[[web.Request], AsyncGenerator[Any, None] | Awaitable[AsyncGenerator[Any, None]]],
    ) -> None:
        """Start the SSE server.

        Args:
            handler: Async handler that accepts an aiohttp request and yields events.
        """

        async def sse_handler(request: web.Request) -> web.StreamResponse:
            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
            await response.prepare(request)

            try:
                stream = handler(request)
                if asyncio.iscoroutine(stream):
                    stream = await stream

                async for event in stream:
                    payload = self._serialize_event(event)
                    await response.write(payload.encode("utf-8"))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                error_event = self._serialize_event(
                    {"type": "error", "error": str(exc)},
                    event_name="error",
                )
                await response.write(error_event.encode("utf-8"))
            finally:
                with contextlib.suppress(Exception):
                    await response.write(b"data: [DONE]\n\n")
                with contextlib.suppress(Exception):
                    await response.write_eof()

            return response

        app = web.Application()
        app.router.add_post(self.path, sse_handler)

        self._runner = web.AppRunner(app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

    @staticmethod
    def _serialize_event(event: Any, event_name: str | None = None) -> str:
        """Serialize an event into SSE wire format."""
        payload = json.dumps(event) if isinstance(event, dict) else str(event)

        lines: list[str] = []
        if event_name:
            lines.append(f"event: {event_name}")
        for line in payload.splitlines() or [""]:
            lines.append(f"data: {line}")
        lines.append("")
        return "\n".join(lines)
