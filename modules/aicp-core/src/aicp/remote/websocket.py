"""Remote session and WebSocket management for AICP.

This module provides:
- WebSocket client for real-time communication
- Session sharing across devices
- Event-driven message handling
- Connection state management

Patterns adapted from:
- OpenClaw (session isolation, state management)
- nanobot (message bus, async patterns)
- Studio (replay builder pattern)
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Core Models
# ============================================================================


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class MessageType(str, Enum):
    """Message types for WebSocket communication."""
    EXECUTION = "execution"
    APPROVAL = "approval"
    WORKFLOW = "workflow"
    AUDIT = "audit"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    SYNC = "sync"


@dataclass
class RemoteMessage:
    """Message sent over WebSocket."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: MessageType = MessageType.SYNC
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """State of a remote session."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    org_id: str | None = None
    principal_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


# ============================================================================
# WebSocket Client
# ============================================================================


class WebSocketClient:
    """WebSocket client for real-time AICP communication.

    Supports:
    - Auto-reconnection with exponential backoff
    - Event handlers for different message types
    - Message queuing during disconnection
    - Heartbeat for connection health
    """

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        session_id: str | None = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        heartbeat_interval: int = 30,
    ):
        self.url = url
        self.api_key = api_key
        self.session_id = session_id or uuid.uuid4().hex
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval

        self._ws: Any = None
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._handlers: dict[str, list[Callable[..., Coroutine[Any, Any, None]]]] = {}
        self._message_queue: asyncio.Queue[RemoteMessage] = asyncio.Queue()
        self._heartbeat_task: asyncio.Task | None = None
        self._receive_task: asyncio.Task | None = None
        self._reconnect_count: int = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == ConnectionState.CONNECTED

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        async with self._lock:
            if self._state == ConnectionState.CONNECTED:
                return

            self._state = ConnectionState.CONNECTING

            try:
                # In production, establish actual WebSocket connection
                # For now, simulate connection
                self._ws = None  # Would be actual WebSocket
                self._state = ConnectionState.CONNECTED
                self._reconnect_count = 0

                # Start background tasks
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._receive_task = asyncio.create_task(self._receive_loop())

            except Exception as e:
                self._state = ConnectionState.ERROR
                raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        async with self._lock:
            self._state = ConnectionState.DISCONNECTED

            # Cancel background tasks
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            if self._receive_task:
                self._receive_task.cancel()
                self._receive_task = None

            # Close WebSocket
            if self._ws:
                # await self._ws.close()  # In production
                self._ws = None

    async def send(self, message: RemoteMessage | dict) -> None:
        """Send a message over WebSocket."""
        if isinstance(message, dict):
            message = RemoteMessage(**message)

        if not self.is_connected():
            await self._message_queue.put(message)
            return

        # In production, serialize and send
        # await self._ws.send_json(message.model_dump())
        pass

    async def emit(self, event: str, data: dict[str, Any]) -> None:
        """Emit an event with data."""
        message = RemoteMessage(
            type=MessageType.SYNC,
            topic=event,
            payload=data,
        )
        await self.send(message)

    def on(self, event: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Register an event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Unregister an event handler."""
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    async def _handle_message(self, message: RemoteMessage) -> None:
        """Handle incoming message."""
        # Dispatch to topic handlers
        handlers = self._handlers.get(message.topic, []) + self._handlers.get("*", [])

        for handler in handlers:
            with contextlib.suppress(Exception):
                await handler(message)

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self._state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.emit("heartbeat", {"session_id": self.session_id})
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket."""
        while self._state == ConnectionState.CONNECTED:
            try:
                # In production, would receive from WebSocket
                # data = await self._ws.recv()
                # message = RemoteMessage.model_validate_json(data)
                # await self._handle_message(message)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                if self.auto_reconnect:
                    await self._reconnect()
                break

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        if self._reconnect_count >= self.max_reconnect_attempts:
            self._state = ConnectionState.ERROR
            return

        self._state = ConnectionState.RECONNECTING
        self._reconnect_count += 1

        delay = min(2 ** self._reconnect_count, 30)
        await asyncio.sleep(delay)

        with contextlib.suppress(Exception):
            await self.connect()


# ============================================================================
# Remote Session Manager
# ============================================================================


class RemoteSessionError(Exception):
    """Errors in remote session operations."""
    pass


class RemoteSessionManager:
    """Manages remote sessions and session sharing.

    Provides:
    - Create/resume sessions
    - Share sessions across devices
    - Session state persistence
    - Expiration handling
    """

    def __init__(self, ws_url: str | None = None, api_key: str | None = None):
        self.ws_url = ws_url
        self.api_key = api_key
        self._client: WebSocketClient | None = None
        self._sessions: dict[str, SessionState] = {}
        self._current_session_id: str | None = None

    async def connect(self) -> None:
        """Connect to remote server."""
        if not self.ws_url:
            return

        self._client = WebSocketClient(
            url=self.ws_url,
            api_key=self.api_key,
        )
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from remote server."""
        if self._client:
            await self._client.disconnect()

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client.is_connected() if self._client else False

    async def create_session(
        self,
        principal_id: str,
        org_id: str | None = None,
        ttl_hours: int = 24,
    ) -> SessionState:
        """Create a new remote session."""
        session_id = uuid.uuid4().hex
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours) if ttl_hours > 0 else None

        session = SessionState(
            session_id=session_id,
            org_id=org_id,
            principal_id=principal_id,
            expires_at=expires_at,
        )

        self._sessions[session_id] = session
        self._current_session_id = session_id

        # Connect client if needed
        if self._client and not self._client.is_connected():
            await self._client.connect()

        # Notify via WebSocket
        if self._client and self._client.is_connected():
            await self._client.emit("session.created", {
                "session_id": session_id,
                "principal_id": principal_id,
            })

        return session

    async def get_session(self, session_id: str) -> SessionState | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def update_session(self, session_id: str, **updates) -> SessionState:
        """Update session state."""
        session = self._sessions.get(session_id)
        if not session:
            raise RemoteSessionError(f"Session {session_id} not found")

        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.last_active = datetime.utcnow()

        # Notify via WebSocket
        if self._client and self._client.is_connected():
            await self._client.emit("session.updated", {
                "session_id": session_id,
                "updates": updates,
            })

        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self._sessions:
            # Notify via WebSocket
            if self._client and self._client.is_connected():
                await self._client.emit("session.deleted", {
                    "session_id": session_id,
                })

            del self._sessions[session_id]

            if self._current_session_id == session_id:
                self._current_session_id = None

    def get_active_sessions(self) -> list[SessionState]:
        """Get all active (non-expired) sessions."""
        now = datetime.utcnow()
        return [
            s for s in self._sessions.values()
            if s.is_active and (s.expires_at is None or s.expires_at > now)
        ]

    def get_current_session(self) -> SessionState | None:
        """Get the current session."""
        if self._current_session_id:
            return self._sessions.get(self._current_session_id)
        return None

    async def share_session(self, session_id: str) -> str:
        """Generate a shareable URL for a session."""
        session = self._sessions.get(session_id)
        if not session:
            raise RemoteSessionError(f"Session {session_id} not found")

        # Generate shareable ID
        share_id = uuid.uuid4().hex[:12]

        # In production, this would create a real shareable URL
        # For now, return a mock URL
        return f"https://aicp.sh/s/{share_id}"

    async def get_shared_session(self, share_id: str) -> SessionState | None:
        """Get a session from a share ID."""
        # In production, this would resolve the share ID
        # For now, return the current session if exists
        return self.get_current_session()

    def register_handler(self, event: str, handler: Callable) -> None:
        """Register a handler for events."""
        if self._client:
            self._client.on(event, handler)

    def unregister_handler(self, event: str, handler: Callable) -> None:
        """Unregister a handler."""
        if self._client:
            self._client.off(event, handler)


# ============================================================================
# Remote Capabilities
# ============================================================================


class RemoteCapabilities:
    """Remote execution capabilities over WebSocket.

    Allows executing capabilities remotely and receiving results
    via WebSocket callbacks.
    """

    def __init__(self, session_manager: RemoteSessionManager):
        self._session_manager = session_manager
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Execute a capability remotely."""
        if not self._session_manager.is_connected():
            raise RemoteSessionError("Not connected to remote server")

        session = self._session_manager.get_current_session()
        if not session:
            raise RemoteSessionError("No active session")

        request_id = uuid.uuid4().hex
        future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send execution request
        if self._session_manager._client:
            await self._session_manager._client.send(RemoteMessage(
                type=MessageType.EXECUTION,
                topic="capability.execute",
                correlation_id=request_id,
                payload={
                    "capability_name": capability_name,
                    "arguments": arguments,
                    "session_id": session.session_id,
                },
            ))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise RemoteSessionError(f"Execution timed out after {timeout}s") from None
        finally:
            self._pending_requests.pop(request_id, None)

    def _handle_response(self, request_id: str, result: dict[str, Any]) -> None:
        """Handle execution response."""
        future = self._pending_requests.get(request_id)
        if future and not future.done():
            future.set_result(result)
