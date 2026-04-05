# Team Workflows and Studio Console Guide

> **Target audience:** Operators, developers, and team leads deploying Mammoth in multi-session or supervised environments.
>
> **Version:** v0.3.0 · **Status:** Phase 2 complete (L3 + L4 orchestration)
>
> **Implementation key:** ✅ Implemented · 🔧 Partial · 🔮 Planned

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture: Two Separate Planes](#2-architecture-two-separate-planes)
3. [Studio Web Console](#3-studio-web-console)
4. [Multi-Session Management](#4-multi-session-management)
5. [Approval Queue](#5-approval-queue)
6. [Live Session Monitoring (SSE)](#6-live-session-monitoring-sse)
7. [Audit Trail](#7-audit-trail)
8. [Channels and Trust Tiers](#8-channels-and-trust-tiers)
9. [Permission Modes](#9-permission-modes)
10. [MCP Server Configuration](#10-mcp-server-configuration)
11. [AICP Governance Bridge](#11-aicp-governance-bridge)
12. [Extension Bridge](#12-chrome-extension-bridge)
13. [REST API Reference (Mammoth Server)](#13-rest-api-reference-mammoth-server)
14. [Configuration Reference](#14-configuration-reference)
15. [Implementation Roadmap](#15-implementation-roadmap)

---

## 1. Overview

Mammoth is the primary interaction shell for AICP. It exposes four channels through which operators and agents touch the system:

| Channel | Kind | Entry Point |
|---------|------|-------------|
| **Terminal** | Interactive REPL | `mammoth` binary |
| **Web** | Studio supervision console | `GET /` (browser) |
| **CLI** | Multi-channel dispatcher | `mammoth serve`, `mammoth ext` |
| **Extension** | Chrome MV3 bridge | SSE at `GET /ext/events` |

All channels route intent into the AICP execution layer (policy evaluation, audit, approval gating, `allowed_next_actions`) and receive back an `ExecutionEnvelope`.

**Two-plane architecture:** Mammoth (Rust, port configurable) handles operator UX. AICP (Python, default port 10003) handles governed execution. They are separate processes. Mammoth calls AICP when governance is enabled.

```
Operator/Agent
      │
      ▼
┌─────────────────────────────────┐
│  Mammoth (Rust)                 │
│  Terminal · Web · CLI · Ext     │
│  Session store, SSE, Studio UI  │
└─────────────┬───────────────────┘
              │ HTTP (when aicp.enabled = true)
              ▼
┌─────────────────────────────────┐
│  AICP Runtime (Python)          │
│  Policy · Approval · Audit      │
│  Workflow · Capability registry │
└─────────────────────────────────┘
```

---

## 2. Architecture: Two Separate Planes

### Mammoth Web Server (Rust)

- **Binary:** `mammoth serve`
- **Default bind:** user-configurable; tests bind to `127.0.0.1:0`
- **Source:** `apps/mammoth/crates/server/`
- **State model:** in-memory session store (`Arc<RwLock<HashMap>>`) with per-session broadcast channels

### AICP Runtime (Python)

- **Default URL:** `http://localhost:10003`
- **Source:** `packages/runtime/src/aicp_runtime/`
- **Exposes:** `/approvals/*`, `/sessions`, `/history`, `/console` (840-line supervision surface)
- **Connection from Mammoth:** configured via `aicp.url` in settings; overridable with `AICP_URL` env var

### Key Rule

> Mammoth's web server is **not** the AICP runtime. The Studio UI in Mammoth is a lightweight web channel for session management and chat. The full AICP supervision console runs as a separate Python service. Do not confuse `GET /` on the Mammoth server with the AICP `/console` endpoint.

---

## 3. Studio Web Console

### Current State ✅

The Studio web console is served by the Mammoth web server at `GET /`. It is a functional, dark-themed single-page chat interface backed by the session API and SSE stream.

**To open Studio:**
```bash
mammoth serve          # starts the server
open http://localhost:<PORT>   # opens in browser
```

**What Studio does today:**
- Creates a session automatically on load (`POST /sessions`)
- Connects to the session's SSE stream (`GET /sessions/{id}/events`)
- Sends messages (`POST /sessions/{id}/message`)
- Renders user, assistant, and system messages in a scrollable chat view
- Sidebar links to `/sessions` (JSON) and `/health`
- Shows current session ID in the footer

**Studio HTML stub** (`apps/mammoth/crates/server/src/studio.html`): 240 lines, included at compile time via `include_str!`. Served from memory — no filesystem dependency.

```javascript
// Studio auto-creates a session and wires SSE on load
async function createSession() {
  const res = await fetch('/sessions', { method: 'POST' });
  const data = await res.json();
  sessionId = data.session_id;   // e.g. "session-1"
  connectSSE();
}
```

### Planned Features 🔮

| Feature | Target |
|---------|--------|
| Full SPA (replace stub HTML) | v0.4.0 |
| Approval queue panel | v0.4.0 |
| Multi-session sidebar with live counts | v0.4.0 |
| Audit log viewer | v0.5.0 |
| Multi-agent team panel | v0.6.0 |
| WebSocket real-time updates | v0.5.0 |

---

## 4. Multi-Session Management

### Creating and Listing Sessions ✅

Each Studio or API client creates sessions independently. Sessions are stored in-memory and identified by sequential IDs (`session-1`, `session-2`, …).

```bash
# Create a session
curl -X POST http://localhost:PORT/sessions
# → {"session_id":"session-1"}

# List all sessions
curl http://localhost:PORT/sessions
# → {"sessions":[{"id":"session-1","created_at":1743870000000,"message_count":3}]}

# Get session details (full conversation)
curl http://localhost:PORT/sessions/session-1
```

### Session Model ✅

```rust
// apps/mammoth/crates/server/src/lib.rs
pub struct Session {
    pub id: SessionId,          // "session-1", "session-2", …
    pub created_at: u64,        // Unix epoch milliseconds
    pub conversation: RuntimeSession,
    events: broadcast::Sender<SessionEvent>,
}

// apps/mammoth/crates/runtime/src/session.rs
pub struct Session {
    pub version: u32,
    pub messages: Vec<ConversationMessage>,
}

pub struct ConversationMessage {
    pub role: MessageRole,     // system | user | assistant | tool
    pub blocks: Vec<ContentBlock>,
    pub usage: Option<TokenUsage>,
}
```

**Content block types:**

```rust
pub enum ContentBlock {
    Text { text: String },
    ToolUse { id: String, name: String, input: String },
    ToolResult { tool_use_id: String, tool_name: String, output: String, is_error: bool },
}
```

### Session Persistence ✅

Sessions can be saved and loaded from disk:

```rust
session.save_to_path(".mammoth/sessions/session-1.json")?;
let session = Session::load_from_path(".mammoth/sessions/session-1.json")?;
```

Serialized format:
```json
{
  "version": 1,
  "messages": [
    {
      "role": "user",
      "blocks": [{ "type": "text", "text": "Hello" }]
    },
    {
      "role": "assistant",
      "blocks": [
        { "type": "text", "text": "Hi there!" },
        { "type": "tool_use", "id": "tool-1", "name": "bash", "input": "echo hi" }
      ],
      "usage": {
        "input_tokens": 10,
        "output_tokens": 4,
        "cache_creation_input_tokens": 1,
        "cache_read_input_tokens": 2
      }
    }
  ]
}
```

### Session Isolation ✅

- Each session has its own broadcast channel (`broadcast::channel(64)`)
- Messages in one session never leak to another session's SSE stream
- `AppState` uses `Arc<RwLock<HashMap<SessionId, Session>>>` — concurrent read access, exclusive write access

### Planned ✅→🔮

| Feature | Status |
|---------|--------|
| Persistent session storage (SQLite/file) | 🔮 v0.4.0 |
| Session sharing between team members | 🔮 v0.5.0 |
| Session tagging and search | 🔮 v0.5.0 |
| Session forking / replay | 🔮 v1.0.0 |

---

## 5. Approval Queue

### What Exists Today 🔧

The approval data model is **fully defined** but the REST endpoints are not yet wired:

```rust
// apps/mammoth/crates/runtime/src/channel.rs

pub struct ApprovalRequest {
    pub approval_id: String,
    pub capability_name: String,    // e.g. "orders.place"
    pub description: String,        // human-readable action description
    pub risk_summary: Option<String>, // e.g. "financial: 0.7, irreversibility: 0.9"
    pub channel: ChannelKind,       // which surface should present this
}

pub struct ApprovalDecision {
    pub approval_id: String,
    pub approved: bool,
    pub comment: Option<String>,    // shown in audit trail
    pub decided_by: Option<String>, // user id or context
}
```

The Chrome extension bridge already carries `ApprovalRequest` events:

```rust
// apps/mammoth/crates/server/src/lib.rs
pub enum ExtEvent {
    Message { content: String },
    ApprovalRequest {
        approval_id: String,
        capability_name: String,
        description: String,
    },
}
```

This means the **extension channel** can already surface approval prompts to users through SSE. What is missing is the REST feedback path (submitting an `ApprovalDecision` back to the server).

### Approval Flow (Current Extension Channel Path)

```
AICP policy engine
    │ effect = "require_approval"
    ▼
Mammoth broadcasts ExtEvent::ApprovalRequest over SSE
    │
    ▼
Chrome extension receives event: "approval_request"
    │
    ▼
User sees popup → approves or denies
    │
    ▼
[NO REST endpoint yet — extension must use workaround]
```

### Planned REST Endpoints 🔮

These endpoints are **not yet implemented** in `lib.rs`. They are the intended design based on the existing types:

```
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/deny
GET  /approvals                        # pending queue
GET  /approvals/{approval_id}          # single request details
```

Expected request body for approve/deny:
```json
{
  "comment": "Reviewed and approved for this order",
  "decided_by": "alice@example.com"
}
```

### AICP Runtime Approvals ✅ (separate service)

The Python AICP runtime has a **fully implemented** approval service (`packages/runtime/src/aicp_runtime/approval.py`, ~619 lines). It exposes:

```
POST /approvals/{id}/approve
POST /approvals/{id}/deny
GET  /approvals
GET  /approvals/{id}
```

When `aicp.enabled = true` in Mammoth settings, capability approval flows through the AICP runtime rather than the Mammoth server directly.

---

## 6. Live Session Monitoring (SSE)

### Connecting to a Session Stream ✅

Each session exposes a Server-Sent Events stream:

```bash
curl -N http://localhost:PORT/sessions/session-1/events
```

**On connect**, the server immediately sends a `snapshot` event with the full session state:

```
event: snapshot
data: {"type":"snapshot","session_id":"session-1","session":{"version":1,"messages":[]}}
```

**On each message**, the server sends a `message` event:

```
event: message
data: {"type":"message","session_id":"session-1","message":{"role":"user","blocks":[{"type":"text","text":"Hello"}],"usage":null}}
```

### SSE Event Types ✅

| Event name | When sent | Payload |
|------------|-----------|---------|
| `snapshot` | On SSE connect | Full `RuntimeSession` |
| `message` | After each message | Single `ConversationMessage` |

### Keep-Alive ✅

The server sends SSE keep-alive pings every 15 seconds:

```rust
Sse::new(stream).keep_alive(KeepAlive::new().interval(Duration::from_secs(15)))
```

This prevents proxies from closing idle connections.

### Lag Handling ✅

The broadcast channel has capacity 64. If a slow client falls 64 events behind, lagged frames are silently skipped (`RecvError::Lagged`). The client receives a gap but is not disconnected.

### JavaScript Client Example ✅

```javascript
const eventSource = new EventSource('/sessions/session-1/events');

// Initial full state
eventSource.addEventListener('snapshot', (e) => {
  const { session } = JSON.parse(e.data);
  renderAllMessages(session.messages);
});

// Incremental updates
eventSource.addEventListener('message', (e) => {
  const { message } = JSON.parse(e.data);
  if (message.role !== 'user') {
    appendMessage('assistant', message.blocks);
  }
});

eventSource.onerror = () => {
  console.warn('SSE connection lost, reconnecting...');
};
```

### Multi-Session Monitoring 🔮

Watching multiple sessions simultaneously requires one `EventSource` per session. A unified multi-session event bus is planned for v0.5.0.

---

## 7. Audit Trail

### Mammoth (Rust) 🔮

Mammoth does not yet expose an `/audit` REST endpoint. Session state is stored in-memory; messages are not persisted to an append-only journal in the current build.

> **Planned (v0.4.0):** Append-only audit journal for all session events, tool calls, and approval decisions. REST endpoint `GET /audit`.

### AICP Runtime (Python) 🔧

The AICP Python runtime has an audit service (`packages/runtime/src/aicp_runtime/`) with an append-only journal (partial, ~104 lines). It records:

- Capability executions
- Policy decisions (allow / deny / require_approval)
- Approval lifecycle events
- Actor attribution (agent, human, system)

```bash
# AICP runtime audit endpoint (separate from Mammoth)
curl http://localhost:10003/history
```

### Execution Envelope

Every AICP execution produces an envelope that includes all audit-relevant fields:

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "orders.place",
  "policy_result": {
    "effect": "allow",
    "trust_tier": 2,
    "risk_score": { "financial": 0.7, "irreversibility": 0.9 }
  },
  "approval_state": {
    "status": "none",
    "approval_id": null
  },
  "status": "success",
  "actor": { "type": "agent", "agent_id": "agent_y5z6" },
  "audit_correlation_id": "corr_u1v2w3x4",
  "timestamp": "2026-04-05T12:00:00.000Z"
}
```

---

## 8. Channels and Trust Tiers

### Channel Kinds ✅

```rust
// apps/mammoth/crates/runtime/src/channel.rs
pub enum ChannelKind {
    Terminal,   // mammoth binary, interactive REPL
    Web,        // Studio UI via server crate
    Cli,        // mammoth serve, mammoth ext sub-commands
    Extension,  // Chrome MV3, bridged via SSE
}
```

### Channel Trait ✅

Every Mammoth channel implements:

```rust
pub trait Channel: Send + Sync {
    fn name(&self) -> &str;
    fn kind(&self) -> ChannelKind;
    fn render_message(&self, content: &str);
    fn request_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;
    fn on_tool_progress(&self, _tool_name: &str, _message: &str) {}  // default: no-op
    fn shutdown(&self) {}
}
```

Channels **must not** contain orchestration logic. They translate only.

### Trust Tiers

Trust tiers are set per session in AICP config and passed to the policy engine on every capability call:

| Tier | Meaning |
|------|---------|
| 0 | Anonymous — no persistent identity |
| 1 | Authenticated user |
| 2 | Operator (default for Mammoth sessions) |
| 3 | Elevated operator |
| 4 | Fully autonomous agent |

Default in Mammoth:
```json
{ "aicp": { "trust_tier": "2" } }
```

Higher trust tiers allow more capabilities to execute without explicit approval. Set trust tier conservatively in production.

---

## 9. Permission Modes

### Defined Modes ✅

```rust
// apps/mammoth/crates/runtime/src/permissions.rs
pub enum PermissionMode {
    ReadOnly,           // "read-only" / "plan" / "default"
    WorkspaceWrite,     // "workspace-write" / "acceptEdits" / "auto"
    DangerFullAccess,   // "danger-full-access" / "dontAsk"
    Prompt,             // ask the user at runtime
    Allow,              // allow everything (bypass mode)
}
```

### Permission Policy ✅

```rust
pub struct PermissionPolicy {
    active_mode: PermissionMode,
    tool_requirements: BTreeMap<String, PermissionMode>,
}
```

Usage:

```rust
let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
    .with_tool_requirement("read_file", PermissionMode::ReadOnly)
    .with_tool_requirement("bash", PermissionMode::DangerFullAccess);

// Check before calling a tool:
match policy.authorize("bash", r#"{"cmd":"rm -rf /"}"#, Some(&mut prompter)) {
    PermissionOutcome::Allow => execute_tool(),
    PermissionOutcome::Deny { reason } => surface_denial(reason),
}
```

### Authorization Rules ✅

1. `Allow` mode bypasses all checks.
2. `active_mode >= required_mode` → allow.
3. `WorkspaceWrite` escalating to `DangerFullAccess` → prompt.
4. `Prompt` mode → always prompt.
5. Everything else → deny.

### Wired to Execution 🔮

`PermissionPolicy` is fully defined and tested but is **not yet wired** to the tool execution path. This is Phase 3 work (v0.4.0).

### Config Keys

```json
{
  "permissionMode": "workspace-write"
}
```

Or via `permissions.defaultMode`:
```json
{
  "permissions": { "defaultMode": "plan" }
}
```

---

## 10. MCP Server Configuration

### Supported Transport Types ✅

| Type | Config key | Use case |
|------|------------|----------|
| `stdio` | `"type": "stdio"` | Local process (default) |
| `sse` | `"type": "sse"` | Remote SSE endpoint |
| `http` | `"type": "http"` | Remote HTTP endpoint |
| `ws` | `"type": "ws"` | WebSocket endpoint |
| `sdk` | `"type": "sdk"` | Named SDK server |
| `claudeai-proxy` | managed proxy | Managed Claude.ai proxy |

### Configuration Example ✅

```json
{
  "mcpServers": {
    "local-tools": {
      "command": "uvx",
      "args": ["my-mcp-server"],
      "env": { "API_KEY": "secret" }
    },
    "remote-tools": {
      "type": "http",
      "url": "https://tools.example.com/mcp",
      "headers": { "Authorization": "Bearer token" },
      "oauth": {
        "clientId": "my-client",
        "callbackPort": 7777,
        "authServerMetadataUrl": "https://auth.example.com/.well-known/oauth-authorization-server"
      }
    },
    "ws-tools": {
      "type": "ws",
      "url": "wss://realtime.example.com/mcp",
      "headers": { "X-Team": "ops" }
    }
  }
}
```

### Scoped MCP Servers ✅

MCP servers can be defined at user scope (`~/.mammoth/settings.json`) or project scope (`.mammoth/settings.json`). Project settings override user settings for the same server name.

```rust
pub struct ScopedMcpServerConfig {
    pub scope: ConfigSource,    // User | Project | Local
    pub config: McpServerConfig,
}
```

---

## 11. AICP Governance Bridge

### Current State 🔮

The bridge between Mammoth and the AICP Python runtime (`aicp_bridge.rs`) is **not yet built**. The config types and default values are in place, but Mammoth does not currently call the AICP runtime.

### Config ✅ (types only)

```rust
pub struct AicpConfig {
    pub url: String,              // default: "http://localhost:10003"
    pub enabled: bool,            // default: false
    pub trust_tier: String,       // default: "2"
    pub session_id: Option<String>,
}
```

URL resolution checks `AICP_URL` environment variable first:

```rust
pub fn resolve_url(&self) -> String {
    std::env::var("AICP_URL").unwrap_or_else(|_| self.url.clone())
}
```

### Settings ✅ (parsing only)

```json
{
  "aicp": {
    "url": "http://localhost:10003",
    "enabled": true,
    "trustTier": "2",
    "sessionId": "sess_abc123"
  }
}
```

### When Enabled (Planned Behavior) 🔮

When `aicp.enabled = true`:
1. Every tool call is sent to `POST {aicp.url}/capabilities/{name}/execute`
2. AICP evaluates policy and returns an `ExecutionEnvelope`
3. If `policy_result.effect = "require_approval"`, Mammoth surfaces `ApprovalRequest` to the active channel
4. The channel's `request_approval()` collects an `ApprovalDecision` and submits it to AICP
5. AICP resumes execution and returns the final result

---

## 12. Chrome Extension Bridge

### Overview ✅

The extension bridge exposes a persistent SSE stream and a message intake endpoint. The Chrome extension connects here once and receives live events.

```
Chrome Extension (MV3)
  └── background service worker
        ├── GET /ext/events   ← SSE stream (connect once, receive all events)
        └── POST /ext/message ← send user message from popup
```

### Receiving Events from the Extension ✅

```javascript
// Chrome extension background.js
const eventSource = new EventSource('http://localhost:PORT/ext/events');

eventSource.addEventListener('message', (e) => {
  const { content } = JSON.parse(e.data);
  // Show content in extension popup
});

eventSource.addEventListener('approval_request', (e) => {
  const { approval_id, capability_name, description } = JSON.parse(e.data);
  // Show approval UI in popup
  // User approves/denies → POST back (endpoint not yet implemented)
});
```

### Sending a Message from the Extension ✅

```bash
curl -X POST http://localhost:PORT/ext/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What files are in the current directory?"}'
```

Response: `204 No Content`

### Extension Event Types ✅

```rust
pub enum ExtEvent {
    Message { content: String },
    ApprovalRequest {
        approval_id: String,
        capability_name: String,
        description: String,
    },
}
```

SSE event names: `message`, `approval_request`

### Limitation 🔧

There is no REST endpoint to submit `ApprovalDecision` back from the extension. The approval flow over the extension channel is one-way until v0.4.0.

---

## 13. REST API Reference (Mammoth Server)

All endpoints are served by `mammoth serve`. Base URL: `http://localhost:<PORT>`.

---

### `GET /health` ✅

Health check.

**Response `200`:**
```json
{"status": "ok", "service": "mammoth-web"}
```

---

### `GET /` ✅

Returns the Studio HTML interface.

**Response `200`:** HTML (the `studio.html` stub, ~240 lines, served inline from the binary)

---

### `POST /sessions` ✅

Create a new session.

**Request:** No body required.

**Response `201`:**
```json
{"session_id": "session-1"}
```

Sessions are numbered sequentially (`session-1`, `session-2`, …). IDs reset on server restart.

---

### `GET /sessions` ✅

List all active sessions.

**Response `200`:**
```json
{
  "sessions": [
    {
      "id": "session-1",
      "created_at": 1743870000000,
      "message_count": 3
    },
    {
      "id": "session-2",
      "created_at": 1743870060000,
      "message_count": 0
    }
  ]
}
```

Sessions are sorted by ID (lexicographic). `created_at` is Unix epoch milliseconds. `message_count` reflects the number of `ConversationMessage` entries.

---

### `GET /sessions/{id}` ✅

Get full session details including all messages.

**Path params:** `id` — session ID (e.g. `session-1`)

**Response `200`:**
```json
{
  "id": "session-1",
  "created_at": 1743870000000,
  "session": {
    "version": 1,
    "messages": [
      {
        "role": "user",
        "blocks": [{"type": "text", "text": "Hello"}],
        "usage": null
      },
      {
        "role": "assistant",
        "blocks": [
          {"type": "text", "text": "Hi there!"},
          {"type": "tool_use", "id": "tool-1", "name": "bash", "input": "echo hi"}
        ],
        "usage": {
          "input_tokens": 42,
          "output_tokens": 8,
          "cache_creation_input_tokens": 0,
          "cache_read_input_tokens": 0
        }
      },
      {
        "role": "tool",
        "blocks": [
          {
            "type": "tool_result",
            "tool_use_id": "tool-1",
            "tool_name": "bash",
            "output": "hi",
            "is_error": false
          }
        ],
        "usage": null
      }
    ]
  }
}
```

**Response `404`:**
```json
{"error": "session `session-99` not found"}
```

---

### `POST /sessions/{id}/message` ✅

Send a message to a session. If a `TurnRunner` is configured, the assistant responds asynchronously over SSE.

**Path params:** `id` — session ID

**Request body:**
```json
{"message": "List the files in the current directory"}
```

**Response `204 No Content`** (message accepted)

**Response `404`:** session not found

After responding `204`, the server:
1. Stores the user message in the session
2. Broadcasts a `message` SSE event
3. If `TurnRunner` is configured, runs inference in a blocking task and broadcasts assistant messages as they are produced

---

### `GET /sessions/{id}/events` ✅

SSE stream for a session. On connect, delivers a full `snapshot`. Delivers `message` events in real time.

**Path params:** `id` — session ID

**Response `200`** (text/event-stream):

```
event: snapshot
data: {"type":"snapshot","session_id":"session-1","session":{"version":1,"messages":[]}}

event: message
data: {"type":"message","session_id":"session-1","message":{"role":"user","blocks":[{"type":"text","text":"Hello"}],"usage":null}}

: keep-alive (every 15s)
```

**Response `404`:** session not found (before stream opens)

---

### `GET /ext/events` ✅

SSE stream for the Chrome extension bridge. Does not require a session ID. Receives all `ExtEvent`s broadcast by the server.

**Response `200`** (text/event-stream):

```
event: message
data: {"type":"message","content":"I found 3 files in the directory."}

event: approval_request
data: {"type":"approval_request","approval_id":"appr_001","capability_name":"files.delete","description":"Delete /tmp/old-build"}
```

---

### `POST /ext/message` ✅

Inject a message from the Chrome extension into the extension broadcast channel.

**Request body:**
```json
{"message": "What's in the clipboard?"}
```

**Response `204 No Content`**

---

### Not Yet Implemented 🔮

These endpoints are **planned** but do not exist in the current codebase:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/approvals` | List pending approvals |
| `GET` | `/approvals/{id}` | Get single approval request |
| `POST` | `/approvals/{id}/approve` | Submit approval decision |
| `POST` | `/approvals/{id}/deny` | Deny an approval request |
| `GET` | `/audit` | Audit event log |
| `GET` | `/sessions/{id}/replay` | Replay session from a checkpoint |

---

## 14. Configuration Reference

### Config File Locations ✅

Files are loaded in order; later files override earlier ones:

| Priority | Path | Scope |
|----------|------|-------|
| 1 (lowest) | `~/.mammoth.json` | User legacy |
| 2 | `~/.mammoth/settings.json` | User |
| 3 | `.mammoth.json` | Project legacy |
| 4 | `.mammoth/settings.json` | Project |
| 5 (highest) | `.mammoth/settings.local.json` | Local (git-ignored) |

Override config home with `MAMMOTH_CONFIG_HOME` environment variable.

### Full Settings Reference ✅

```json
{
  "model": "claude-opus-4-5",

  "permissionMode": "workspace-write",

  "permissions": {
    "defaultMode": "plan"
  },

  "aicp": {
    "url": "http://localhost:10003",
    "enabled": false,
    "trustTier": "2",
    "sessionId": null
  },

  "hooks": {
    "PreToolUse": ["./hooks/pre-tool.sh"],
    "PostToolUse": ["./hooks/post-tool.sh"]
  },

  "mcpServers": {
    "my-tools": {
      "command": "uvx",
      "args": ["my-mcp-server"],
      "env": { "DEBUG": "1" }
    }
  },

  "enabledPlugins": {
    "tool-guard@builtin": true
  },

  "plugins": {
    "externalDirectories": ["./my-plugins"],
    "installRoot": "~/.mammoth/plugins/installed",
    "registryPath": "~/.mammoth/plugins/installed.json",
    "bundledRoot": "./bundled-plugins"
  },

  "sandbox": {
    "enabled": false,
    "namespaceRestrictions": false,
    "networkIsolation": false,
    "filesystemMode": "workspace-only",
    "allowedMounts": []
  },

  "oauth": {
    "clientId": "my-client",
    "authorizeUrl": "https://auth.example.com/oauth/authorize",
    "tokenUrl": "https://auth.example.com/oauth/token",
    "callbackPort": 54545,
    "scopes": ["org:read", "user:write"]
  }
}
```

### Permission Mode Values

| Config value | `ResolvedPermissionMode` | Behavior |
|---|---|---|
| `"read-only"`, `"plan"`, `"default"` | `ReadOnly` | No writes |
| `"workspace-write"`, `"acceptEdits"`, `"auto"` | `WorkspaceWrite` | Writes in workspace |
| `"danger-full-access"`, `"dontAsk"` | `DangerFullAccess` | All tools allowed |

### Filesystem Isolation Modes

| Value | Behavior |
|-------|----------|
| `"off"` | No isolation |
| `"workspace-only"` | Restrict to current working directory |
| `"allow-list"` | Only paths in `allowedMounts` |

### Environment Variables

| Variable | Effect |
|----------|--------|
| `AICP_URL` | Overrides `aicp.url` at runtime |
| `MAMMOTH_CONFIG_HOME` | Override config directory (default: `~/.mammoth`) |

---

## 15. Implementation Roadmap

### v0.3.0 — Current ✅

- Session CRUD and SSE streaming
- Studio web console (functional stub)
- Chrome extension bridge (SSE + message POST)
- Channel abstraction (Terminal, Web, CLI, Extension)
- `ApprovalRequest` / `ApprovalDecision` types
- `PermissionPolicy` with full authorization logic
- AICP config types and URL resolution
- MCP server configuration (6 transport types)
- Session JSON serialization and persistence

### v0.4.0 — Mammoth + Agent Integration 🔮

- Wire `PermissionPolicy` to tool execution
- Build `aicp_bridge.rs` (Mammoth → AICP HTTP calls)
- Add `/approvals` REST endpoints on Mammoth server
- Approval feedback loop for extension channel
- Append-only audit journal for session events
- `GET /audit` REST endpoint
- Persistent session storage

### v0.5.0 — Supervision and Observability 🔮

- Full Studio SPA (replace HTML stub)
- Multi-session live dashboard
- Approval queue panel in Studio
- Audit log viewer in Studio
- WebSocket real-time updates (planned `ws.rs`)
- Session sharing between operators
- `GET /sessions/{id}/replay` endpoint

### v0.6.0 — Multi-Agent Swarm 🔮

- Multi-agent tools: `team_create`, `agent`, `send_message`, `task_*`
- Agent panel in Studio (team overview)
- Nano-bot team presets
- Orchestrator / specialist / worker / supervisor hierarchy
- Agent communication bus

### v1.0.0 — Full Orchestration 🔮

- Complete supervision console (absorbed Studio)
- Cross-flow events and federation
- `/.well-known/aicp` discovery
- Full audit replay and session forking
- L5 orchestration compliance

---

## Appendix: Data Types Quick Reference

### `SessionSummary`
```json
{
  "id": "session-1",
  "created_at": 1743870000000,
  "message_count": 5
}
```

### `SessionDetailsResponse`
```json
{
  "id": "session-1",
  "created_at": 1743870000000,
  "session": { "version": 1, "messages": [ /* ConversationMessage[] */ ] }
}
```

### `ConversationMessage`
```json
{
  "role": "assistant",
  "blocks": [
    { "type": "text", "text": "Here is the result:" },
    { "type": "tool_use", "id": "tool-1", "name": "bash", "input": "ls -la" }
  ],
  "usage": { "input_tokens": 100, "output_tokens": 20, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 50 }
}
```

### `ApprovalRequest`
```json
{
  "approval_id": "appr_001",
  "capability_name": "files.delete",
  "description": "Delete /var/log/old-app.log (3.2 MB)",
  "risk_summary": "irreversibility: 0.9",
  "channel": "web"
}
```

### `ApprovalDecision`
```json
{
  "approval_id": "appr_001",
  "approved": true,
  "comment": "Safe to delete, already archived",
  "decided_by": "alice@example.com"
}
```

### `ExtEvent` — ApprovalRequest (over SSE)
```
event: approval_request
data: {"type":"approval_request","approval_id":"appr_001","capability_name":"files.delete","description":"Delete /var/log/old-app.log"}
```

---

*Last updated: 2026-04-05 · AICP v0.3.0*
