"""WebSocket transport adapter for AICP.

Provides WebSocket-based capability execution.
"""

import asyncio
import json
from typing import Any, AsyncGenerator

from aicp.plugins import TransportPlugin, PluginMetadata, register_transport


@register_transport("websocket")
class WebSocketTransport(TransportPlugin):
    """WebSocket transport for real-time capability execution.
    
    Supports both client (outgoing) and server (incoming) WebSocket connections.
    """
    
    def __init__(
        self,
        url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        path: str | None = None,
    ):
        self.url = url
        self.host = host
        self.port = port
        self.path = path or "/ws"
        self._ws = None
        self._server = None
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="websocket-transport",
            version="1.0.0",
            description="WebSocket transport for real-time capability execution",
            tags=["websocket", "streaming", "real-time"],
        )
        
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize WebSocket transport."""
        if config:
            self.url = config.get("url", self.url)
            self.host = config.get("host", self.host)
            self.port = config.get("port", self.port)
            self.path = config.get("path", self.path)
            
    def shutdown(self) -> None:
        """Close WebSocket connections."""
        if self._ws:
            asyncio.create_task(self._ws.close())
        if self._server:
            self._server.close()
            
    def get_transport_type(self) -> str:
        return "websocket"
    
    async def connect(self) -> None:
        """Connect to WebSocket server."""
        import websockets
        if self.url:
            self._ws = await websockets.connect(self.url)
    
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request via WebSocket."""
        if not self._ws:
            await self.connect()
            
        await self._ws.send(json.dumps(request))
        response = await self._ws.recv()
        return json.loads(response)
    
    async def receive(self) -> dict[str, Any]:
        """Receive response from WebSocket."""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")
        response = await self._ws.recv()
        return json.loads(response)
    
    async def send_stream(self, request: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Send request and receive streaming response."""
        if not self._ws:
            await self.connect()
            
        await self._ws.send(json.dumps(request))
        
        try:
            while True:
                message = await self._ws.recv()
                data = json.loads(message)
                yield data
                if data.get("type") == "end":
                    break
        except asyncio.CancelledError:
            await self._ws.close()
            raise


class WebSocketServerTransport(TransportPlugin):
    """WebSocket server transport for handling incoming connections."""
    
    def __init__(self, host: str = "localhost", port: int = 8765, path: str = "/ws"):
        self.host = host
        self.port = port
        self.path = path
        self._handler = None
        
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="websocket-server-transport",
            version="1.0.0",
            description="WebSocket server for handling incoming connections",
            tags=["websocket", "server"],
        )
        
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        if config:
            self.host = config.get("host", self.host)
            self.port = config.get("port", self.port)
            self.path = config.get("path", self.path)
            
    def shutdown(self) -> None:
        pass
        
    def get_transport_type(self) -> str:
        return "websocket-server"
    
    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Use start_server() for server transport")
    
    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError("Use start_server() for server transport")
        
    async def start_server(
        self,
        handler: callable,
    ) -> None:
        """Start WebSocket server with request handler.
        
        Args:
            handler: Async function that handles requests and returns responses.
        """
        import websockets
        
        async def ws_handler(ws):
            request = await ws.recv()
            response = await handler(json.loads(request))
            await ws.send(json.dumps(response))
            
        self._server = await websockets.serve(ws_handler, self.host, self.port)
        
    async def serve_forever(self, handler: callable) -> None:
        """Start server and run forever."""
        import websockets
        
        async def ws_handler(ws):
            try:
                async for message in ws:
                    request = json.loads(message)
                    response = await handler(request)
                    await ws.send(json.dumps(response))
            except websockets.exceptions.ConnectionClosed:
                pass
                
        await websockets.serve(ws_handler, self.host, self.port)
        await asyncio.Future()
