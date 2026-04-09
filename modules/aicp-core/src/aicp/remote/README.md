# AICP Remote

### WebSocket communication and remote session management for distributed agent execution

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/aicp-ai/aicp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)

---

## Overview

**AICP Remote** provides WebSocket-based communication and remote session management for distributed agent execution. It enables real-time event streaming, session sharing across devices, and remote capability execution.

### Features

| Feature | Description |
|---------|-------------|
| **WebSocket Client** | Real-time async communication with auto-reconnect |
| **Session Manager** | Create, share, and manage remote sessions |
| **Event Handlers** | Topic-based event routing with wildcard support |
| **Heartbeat** | Connection health monitoring |
| **Message Queue** | Queue messages during disconnection |
| **Remote Execution** | Execute capabilities remotely over WebSocket |

---

## Installation

```bash
pip install aicp-core
```

---

## Quick Start

### WebSocket Client

```python
from aicp.remote import WebSocketClient, ConnectionState, RemoteMessage, MessageType

client = WebSocketClient(
    url="wss://aicp.example.com/ws",
    api_key="your-api-key",
    auto_reconnect=True,
    max_reconnect_attempts=5,
)

await client.connect()

# Send message
await client.send(RemoteMessage(
    type=MessageType.EXECUTION,
    topic="capability.execute",
    payload={"capability_name": "notes.create", "arguments": {"title": "Hello"}},
))

# Register event handler
async def on_approval(message):
    print(f"Approval event: {message.payload}")

client.on("approval.*", on_approval)

await client.disconnect()
```

### Remote Session Manager

```python
from aicp.remote import RemoteSessionManager

manager = RemoteSessionManager(
    ws_url="wss://aicp.example.com/ws",
    api_key="your-api-key",
)

await manager.connect()

# Create session
session = await manager.create_session(
    principal_id="user-123",
    org_id="org-456",
    ttl_hours=24,
)

# Share session
share_url = await manager.share_session(session.session_id)
print(f"Share URL: {share_url}")

# Get active sessions
active = manager.get_active_sessions()

await manager.disconnect()
```

### Remote Capabilities

```python
from aicp.remote import RemoteSessionManager, RemoteCapabilities

manager = RemoteSessionManager(ws_url="wss://aicp.example.com/ws")
await manager.connect()

await manager.create_session(principal_id="user-123")

capabilities = RemoteCapabilities(manager)

# Execute capability remotely
result = await capabilities.execute(
    capability_name="notes.list",
    arguments={"limit": 10},
    timeout=30.0,
)

print(result)
```

---

## Architecture

### Connection States

```
DISCONNECTED → CONNECTING → CONNECTED
                  ↓              ↓
              RECONNECTING    ERROR
                  ↓
              CONNECTED (retry)
```

### Message Flow

```
Application → RemoteMessage → WebSocketClient → Server
                                                    ↓
Application ← RemoteMessage ← WebSocketClient ← Server
```

### Session Lifecycle

```
Create → Active → Share → Update → Expire/Delete
```

---

## API Reference

### WebSocketClient

| Method | Description |
|--------|-------------|
| `connect()` | Connect to WebSocket server |
| `disconnect()` | Disconnect from server |
| `send(message)` | Send a message |
| `emit(event, data)` | Emit an event with data |
| `on(event, handler)` | Register event handler |
| `off(event, handler)` | Unregister event handler |
| `is_connected()` | Check connection status |

### RemoteSessionManager

| Method | Description |
|--------|-------------|
| `connect()` | Connect to remote server |
| `disconnect()` | Disconnect from server |
| `create_session(principal_id, org_id, ttl_hours)` | Create a new session |
| `get_session(session_id)` | Get session by ID |
| `update_session(session_id, **updates)` | Update session state |
| `delete_session(session_id)` | Delete a session |
| `get_active_sessions()` | Get all active sessions |
| `get_current_session()` | Get the current session |
| `share_session(session_id)` | Generate shareable URL |
| `get_shared_session(share_id)` | Get session from share ID |
| `register_handler(event, handler)` | Register event handler |

### RemoteCapabilities

| Method | Description |
|--------|-------------|
| `execute(capability_name, arguments, timeout)` | Execute capability remotely |

---

## Message Types

| Type | Purpose |
|------|---------|
| `EXECUTION` | Capability execution requests/results |
| `APPROVAL` | Approval workflow events |
| `WORKFLOW` | Workflow state changes |
| `AUDIT` | Audit log entries |
| `HEARTBEAT` | Connection health checks |
| `ERROR` | Error notifications |
| `SYNC` | General synchronization |

---

## Package Layout

| Module | Purpose |
|--------|---------|
| `websocket.py` | WebSocket client, session manager, remote capabilities |
| `__init__.py` | Public API exports |

---

## Development

```bash
# Install for development
git clone https://github.com/aicp-ai/aicp.git
cd aicp/modules/aicp-core
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check .
```

---

## License

Apache 2.0. See `LICENSE`.