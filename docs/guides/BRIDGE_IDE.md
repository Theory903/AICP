# Mammoth IDE Bridge — Implementation Guide

> **Status: Implementation Target** — This feature does not exist yet. This guide describes
> the planned architecture, protocol, and per-IDE integration approach. Sections marked
> **[PLANNED]** have no existing source. Sections marked **[GROUNDED]** reference patterns
> already present in the codebase.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Transport Layer](#3-transport-layer)
4. [Authentication and Session Binding](#4-authentication-and-session-binding)
5. [Bridge Message Protocol](#5-bridge-message-protocol)
6. [Session Creation from the IDE](#6-session-creation-from-the-ide)
7. [Permission Proxying](#7-permission-proxying)
8. [Inbound File Attachments](#8-inbound-file-attachments)
9. [REPL Bridge](#9-repl-bridge)
10. [External Editor Awareness](#10-external-editor-awareness)
11. [VS Code Extension](#11-vs-code-extension)
12. [Neovim Bridge](#12-neovim-bridge)
13. [JetBrains Plugin](#13-jetbrains-plugin)
14. [Zed Extension](#14-zed-extension)
15. [Configuration Reference](#15-configuration-reference)
16. [Implementation Roadmap](#16-implementation-roadmap)
17. [Security Considerations](#17-security-considerations)

---

## 1. Overview

The **IDE Bridge** is Mammoth's fifth channel — joining Terminal TUI, Web UI, Chrome MV3
Extension, and CLI. It enables bidirectional communication between a running Mammoth session
and an editor plugin, giving operators:

- **Context injection**: the editor sends the current file, selection, and diagnostics into
  the active Mammoth session.
- **Approval routing**: Mammoth surfaces `ApprovalRequest` events inside the editor UI,
  letting the operator approve or deny without leaving the editor.
- **REPL bridge**: Mammoth can write output, diffs, and suggestions back into editor buffers.
- **Session lifecycle**: editors can spawn, resume, and inspect Mammoth sessions via a
  first-class plugin API.

### Design Principles

- **One server, many editors.** The bridge server runs inside the Mammoth daemon; editors
  connect as clients. Mammoth never spawns processes into the editor.
- **Mirror the Chrome extension bridge.** The existing SSE + HTTP POST pattern used by the
  Chrome MV3 extension (`server/src/lib.rs`) is directly reused. IDE plugins speak the same
  `ExtEvent` envelope.
- **Reuse existing auth.** Session tokens already exist in `runtime/src/remote.rs`. The IDE
  plugin reads the same token file used by the CLI.
- **LSP-framed Unix socket for local transports.** For editors with native JSON-RPC channels
  (Neovim), the bridge uses the same `Content-Length` framing already implemented in
  `lsp/src/client.rs`.
- **No adapter logic in core.** The bridge server translates only. It does not contain
  orchestration logic.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Mammoth Daemon (tokio runtime)                                  │
│                                                                  │
│  ┌───────────────┐   broadcast::Sender<BridgeEvent>             │
│  │  Session      │──────────────────────────────────────────┐   │
│  │  Store        │                                           │   │
│  └───────────────┘                                           │   │
│                                                              ▼   │
│  ┌───────────────┐   ┌──────────────────────────────────────┐   │
│  │  AICP Runtime │   │  IdeBridgeServer (axum)              │   │
│  │  (channels,   │◄──│                                      │   │
│  │   policy,     │   │  GET  /ide/events   → SSE stream     │   │
│  │   execution)  │   │  POST /ide/message  → inbound msg    │   │
│  └───────────────┘   │  POST /ide/session  → create/resume  │   │
│                       │  GET  /ide/status   → health + info  │   │
│                       └──────────────┬───────────────────────┘   │
│                                      │ Unix socket or TCP        │
└──────────────────────────────────────┼──────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                         │
        ┌─────▼──────┐         ┌───────▼──────┐        ┌───────▼──────┐
        │ VS Code     │         │  Neovim      │        │  JetBrains   │
        │ Extension   │         │  Plugin      │        │  Plugin      │
        │ (TypeScript)│         │  (Lua/RPC)   │        │  (Kotlin)    │
        └─────────────┘         └──────────────┘        └──────────────┘
```

### Component Map

| Component | Location | Status |
|-----------|----------|--------|
| `IdeBridgeServer` | `crates/server/src/ide_bridge.rs` | **[PLANNED]** |
| `ChannelKind::Ide` variant | `crates/runtime/src/channel.rs` | **[PLANNED]** |
| `IdeBridgeConfig` in `RuntimeFeatureConfig` | `crates/runtime/src/config.rs` | **[PLANNED]** |
| Token auth (reused) | `crates/runtime/src/remote.rs` | **[GROUNDED]** |
| `ExtEvent` envelope (reused) | `crates/server/src/lib.rs` | **[GROUNDED]** |
| `ApprovalRequest` / `ApprovalDecision` | `crates/runtime/src/channel.rs` | **[GROUNDED]** |
| LSP JSON-RPC framing (reused) | `crates/lsp/src/client.rs` | **[GROUNDED]** |
| VS Code extension | `plugins/vscode/` | **[PLANNED]** |
| Neovim plugin | `plugins/neovim/` | **[PLANNED]** |
| JetBrains plugin | `plugins/jetbrains/` | **[PLANNED]** |
| Zed extension | `plugins/zed/` | **[PLANNED]** |

---

## 3. Transport Layer

**[PLANNED]** The bridge supports two transports. The server negotiates the transport at
connection time based on client capability headers.

### 3.1 HTTP/SSE Transport (primary)

Mirrors the Chrome extension bridge in `crates/server/src/lib.rs`:

- **Server → Client**: `GET /ide/events` returns an SSE stream. Each event is a
  JSON-serialised `BridgeEvent`.
- **Client → Server**: `POST /ide/message` sends a JSON body containing a `BridgeMessage`.

This transport works over both TCP (remote/WSL) and a Unix domain socket (local).

```
# Local (preferred)
MAMMOTH_IDE_BRIDGE_SOCKET=/run/mammoth/ide-bridge.sock

# Remote fallback
MAMMOTH_IDE_BRIDGE_URL=http://127.0.0.1:37291
```

### 3.2 JSON-RPC / Unix Socket Transport (Neovim, Zed)

For editors with native JSON-RPC channels, the bridge additionally exposes a Unix socket
using `Content-Length` framing identical to `crates/lsp/src/client.rs`:

```
Content-Length: <byte-length>\r\n
\r\n
<JSON body>
```

The socket path is `$XDG_RUNTIME_DIR/mammoth/ide-rpc.sock` (fallback:
`/tmp/mammoth-ide-rpc-<uid>.sock`).

The server reads requests, dispatches them synchronously to the same handler as the HTTP
transport, and writes the response frame immediately. Push events are sent as JSON-RPC
notifications with method `mammoth/event` and no `id` field.

---

## 4. Authentication and Session Binding

**[GROUNDED — mirrors `crates/runtime/src/remote.rs`]**

The IDE plugin authenticates using the same token written by the Mammoth daemon for CLI
access:

```
/run/ccr/session_token          # primary (matches remote.rs)
$HOME/.mammoth/session_token    # fallback for non-systemd environments
```

Every request to `IdeBridgeServer` must carry:

```http
Authorization: Bearer <session_token>
X-Mammoth-Session-Id: <session_id>   # optional; omit to attach to the active session
```

The server validates the token against `SessionStore` (same store used by the web and
extension bridges). On success it returns a `bridge_token` — a short-lived (15 min), scoped
credential that the plugin uses for the duration of the edit session. The `bridge_token`
carries a `trust_tier` ceiling derived from the session's trust tier; it cannot escalate.

```rust
/// [PLANNED] Token issued to an IDE client after successful auth.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeToken {
    pub token: String,           // random 32-byte hex
    pub session_id: SessionId,
    pub expires_at: DateTime<Utc>,
    pub trust_ceiling: TrustTier,
    pub editor: EditorKind,
}
```

Token refresh is handled automatically: when the plugin receives a `bridge_token_expiring`
event (emitted 2 minutes before expiry), it re-authenticates with the original session token.

---

## 5. Bridge Message Protocol

**[PLANNED]** All messages use JSON. The top-level discriminant field is `"type"`.

### 5.1 Server → Client Events (`BridgeEvent`)

```json
{
  "type": "session_snapshot",
  "session_id": "sess_abc123",
  "messages": [
    { "role": "user",      "content": "Review this function" },
    { "role": "assistant", "content": "Here is my analysis…"  }
  ],
  "active_capabilities": ["fs.read", "fs.write"],
  "trust_tier": 2,
  "timestamp": "2026-04-05T10:00:00Z"
}
```

```json
{
  "type": "message",
  "session_id": "sess_abc123",
  "role": "assistant",
  "content": "I've analysed the selection. The function has…",
  "format_hint": "markdown",
  "timestamp": "2026-04-05T10:00:01Z"
}
```

```json
{
  "type": "approval_request",
  "approval_id": "appr_xyz789",
  "session_id": "sess_abc123",
  "capability_name": "fs.write",
  "description": "Write 47 lines to src/main.rs",
  "risk_summary": "Overwrites existing file. Irreversibility: high.",
  "risk_score": {
    "financial": 0.0,
    "irreversibility": 0.9,
    "privacy": 0.1
  },
  "timeout_secs": 120,
  "timestamp": "2026-04-05T10:00:02Z"
}
```

```json
{
  "type": "tool_progress",
  "session_id": "sess_abc123",
  "tool_name": "fs.write",
  "progress_pct": 42,
  "message": "Writing chunk 3/7…",
  "timestamp": "2026-04-05T10:00:03Z"
}
```

```json
{
  "type": "buffer_write",
  "session_id": "sess_abc123",
  "uri": "file:///workspace/src/main.rs",
  "content": "fn main() {\n    println!(\"hello\");\n}\n",
  "range": {
    "start": { "line": 0, "character": 0 },
    "end":   { "line": 0, "character": 0 }
  },
  "operation": "replace_range",
  "timestamp": "2026-04-05T10:00:04Z"
}
```

```json
{
  "type": "diff_preview",
  "session_id": "sess_abc123",
  "uri": "file:///workspace/src/main.rs",
  "unified_diff": "--- a/src/main.rs\n+++ b/src/main.rs\n@@ -1,3 +1,5 @@\n+use std::io;\n fn main() {…",
  "timestamp": "2026-04-05T10:00:05Z"
}
```

```json
{
  "type": "bridge_token_expiring",
  "expires_at": "2026-04-05T10:13:00Z",
  "timestamp": "2026-04-05T10:11:00Z"
}
```

```json
{
  "type": "session_ended",
  "session_id": "sess_abc123",
  "reason": "user_exit",
  "timestamp": "2026-04-05T10:30:00Z"
}
```

### 5.2 Client → Server Messages (`BridgeMessage`)

```json
{
  "type": "context_push",
  "session_id": "sess_abc123",
  "context": {
    "uri": "file:///workspace/src/main.rs",
    "language_id": "rust",
    "version": 14,
    "selection": {
      "start": { "line": 10, "character": 4 },
      "end":   { "line": 25, "character": 1 }
    },
    "selected_text": "fn process(input: &str) -> Result<…> {…}",
    "diagnostics": [
      {
        "range": {
          "start": { "line": 12, "character": 8 },
          "end":   { "line": 12, "character": 22 }
        },
        "severity": "error",
        "message": "expected `)`",
        "source": "rustc"
      }
    ],
    "visible_range": {
      "start": { "line": 0, "character": 0 },
      "end":   { "line": 40, "character": 0 }
    }
  },
  "timestamp": "2026-04-05T10:00:00Z"
}
```

```json
{
  "type": "user_message",
  "session_id": "sess_abc123",
  "content": "Explain the error on line 12",
  "attach_context": true,
  "timestamp": "2026-04-05T10:00:01Z"
}
```

```json
{
  "type": "approval_decision",
  "approval_id": "appr_xyz789",
  "session_id": "sess_abc123",
  "decision": "allow",
  "decided_by": "human",
  "timestamp": "2026-04-05T10:00:10Z"
}
```

```json
{
  "type": "file_attach",
  "session_id": "sess_abc123",
  "files": [
    {
      "uri": "file:///workspace/src/lib.rs",
      "content": "pub mod bridge;\n…",
      "language_id": "rust"
    }
  ],
  "timestamp": "2026-04-05T10:00:02Z"
}
```

```json
{
  "type": "buffer_write_ack",
  "session_id": "sess_abc123",
  "uri": "file:///workspace/src/main.rs",
  "applied": true,
  "error": null,
  "timestamp": "2026-04-05T10:00:05Z"
}
```

```json
{
  "type": "ping",
  "timestamp": "2026-04-05T10:00:00Z"
}
```

### 5.3 Rust Type Definitions

**[PLANNED]** Full definitions for `crates/server/src/ide_bridge.rs`:

```rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ─── Shared primitives ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub line: u32,
    pub character: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Range {
    pub start: Position,
    pub end: Position,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DiagnosticSeverity {
    Error,
    Warning,
    Information,
    Hint,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Diagnostic {
    pub range: Range,
    pub severity: DiagnosticSeverity,
    pub message: String,
    pub source: Option<String>,
    pub code: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EditorContext {
    pub uri: String,
    pub language_id: String,
    pub version: u32,
    pub selection: Option<Range>,
    pub selected_text: Option<String>,
    pub diagnostics: Vec<Diagnostic>,
    pub visible_range: Option<Range>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttachedFile {
    pub uri: String,
    pub content: String,
    pub language_id: Option<String>,
}

// ─── Server → Client ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum BridgeEvent {
    SessionSnapshot {
        session_id: String,
        messages: Vec<SessionMessage>,
        active_capabilities: Vec<String>,
        trust_tier: u8,
        timestamp: DateTime<Utc>,
    },
    Message {
        session_id: String,
        role: String,
        content: String,
        format_hint: Option<String>,
        timestamp: DateTime<Utc>,
    },
    ApprovalRequest {
        approval_id: String,
        session_id: String,
        capability_name: String,
        description: String,
        risk_summary: String,
        risk_score: RiskScore,
        timeout_secs: u32,
        timestamp: DateTime<Utc>,
    },
    ToolProgress {
        session_id: String,
        tool_name: String,
        progress_pct: Option<u8>,
        message: String,
        timestamp: DateTime<Utc>,
    },
    BufferWrite {
        session_id: String,
        uri: String,
        content: String,
        range: Option<Range>,
        operation: BufferOperation,
        timestamp: DateTime<Utc>,
    },
    DiffPreview {
        session_id: String,
        uri: String,
        unified_diff: String,
        timestamp: DateTime<Utc>,
    },
    BridgeTokenExpiring {
        expires_at: DateTime<Utc>,
        timestamp: DateTime<Utc>,
    },
    SessionEnded {
        session_id: String,
        reason: String,
        timestamp: DateTime<Utc>,
    },
    Pong {
        timestamp: DateTime<Utc>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BufferOperation {
    ReplaceRange,
    InsertAfter,
    InsertBefore,
    ReplaceAll,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskScore {
    pub financial: f32,
    pub irreversibility: f32,
    pub privacy: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionMessage {
    pub role: String,
    pub content: String,
}

// ─── Client → Server ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum BridgeMessage {
    ContextPush {
        session_id: String,
        context: EditorContext,
        timestamp: DateTime<Utc>,
    },
    UserMessage {
        session_id: String,
        content: String,
        attach_context: bool,
        timestamp: DateTime<Utc>,
    },
    ApprovalDecision {
        approval_id: String,
        session_id: String,
        decision: ApprovalChoice,
        decided_by: String,
        timestamp: DateTime<Utc>,
    },
    FileAttach {
        session_id: String,
        files: Vec<AttachedFile>,
        timestamp: DateTime<Utc>,
    },
    BufferWriteAck {
        session_id: String,
        uri: String,
        applied: bool,
        error: Option<String>,
        timestamp: DateTime<Utc>,
    },
    Ping {
        timestamp: DateTime<Utc>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ApprovalChoice {
    Allow,
    Deny,
}
```

---

## 6. Session Creation from the IDE

**[PLANNED]**

### 6.1 Create a New Session

```http
POST /ide/session
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "action": "create",
  "editor": "vscode",
  "workspace_root": "/workspace",
  "initial_context": {
    "uri": "file:///workspace/src/main.rs",
    "language_id": "rust",
    "version": 1,
    "selection": null,
    "diagnostics": [],
    "visible_range": null
  }
}
```

Response:

```json
{
  "session_id": "sess_abc123",
  "bridge_token": "b64f3a...",
  "expires_at": "2026-04-05T10:15:00Z",
  "sse_url": "/ide/events",
  "socket_path": "/run/mammoth/ide-rpc.sock",
  "trust_tier": 2
}
```

### 6.2 Resume an Existing Session

```http
POST /ide/session
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "action": "resume",
  "session_id": "sess_abc123",
  "editor": "vscode"
}
```

The server replays the last `session_snapshot` event on the new SSE connection so the plugin
can reconstruct conversation state without storing it locally.

### 6.3 List Sessions

```http
GET /ide/status
Authorization: Bearer <session_token>
```

```json
{
  "active_sessions": [
    {
      "session_id": "sess_abc123",
      "created_at": "2026-04-05T09:00:00Z",
      "last_active": "2026-04-05T10:00:00Z",
      "trust_tier": 2,
      "editor": "vscode"
    }
  ],
  "bridge_version": "0.3.0",
  "supported_editors": ["vscode", "neovim", "jetbrains", "zed"]
}
```

### 6.4 Rust Handler Sketch

**[PLANNED]** `crates/server/src/ide_bridge.rs`:

```rust
pub async fn handle_session(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Json(req): Json<SessionRequest>,
) -> Result<Json<SessionResponse>, BridgeError> {
    let token = extract_bearer(&headers)?;
    let session = state.session_store.validate_token(&token).await?;

    match req.action {
        SessionAction::Create => {
            let new_session = state.session_store.create(CreateSessionParams {
                trust_tier: session.trust_tier,
                channel: ChannelKind::Ide,
                editor: req.editor,
                workspace_root: req.workspace_root,
            }).await?;

            let bridge_token = state.bridge_tokens.issue(&new_session).await;

            Ok(Json(SessionResponse {
                session_id: new_session.id,
                bridge_token: bridge_token.token,
                expires_at: bridge_token.expires_at,
                sse_url: "/ide/events".into(),
                socket_path: state.config.ide_bridge.socket_path.clone(),
                trust_tier: new_session.trust_tier,
            }))
        }
        SessionAction::Resume => {
            let existing = state.session_store
                .get(req.session_id.as_deref().ok_or(BridgeError::MissingSessionId)?)
                .await?;
            // … replay snapshot logic
        }
    }
}
```

---

## 7. Permission Proxying

**[GROUNDED — `ApprovalRequest`/`ApprovalDecision` already defined in
`crates/runtime/src/channel.rs`]**

When an `approval_gated` capability is invoked during a session attached to an IDE bridge
client, the runtime calls `Channel::request_approval`. The `IdeBridgeChannel` implementation
serialises the existing `ApprovalRequest` struct into a `BridgeEvent::ApprovalRequest` and
broadcasts it over the SSE stream.

```rust
/// [PLANNED] IdeBridgeChannel implements the Channel trait.
#[async_trait]
impl Channel for IdeBridgeChannel {
    async fn request_approval(
        &self,
        req: ApprovalRequest,
    ) -> Result<ApprovalDecision, ChannelError> {
        // Convert runtime ApprovalRequest → BridgeEvent
        let event = BridgeEvent::ApprovalRequest {
            approval_id: req.approval_id.clone(),
            session_id: self.session_id.clone(),
            capability_name: req.capability_name.clone(),
            description: req.description.clone(),
            risk_summary: req.risk_summary.clone(),
            risk_score: RiskScore {
                financial:      req.risk_score.financial,
                irreversibility: req.risk_score.irreversibility,
                privacy:        req.risk_score.privacy,
            },
            timeout_secs: req.timeout_secs.unwrap_or(120),
            timestamp: Utc::now(),
        };

        self.sender.send(event)?;

        // Block until the plugin sends back ApprovalDecision
        let decision = self
            .pending_approvals
            .wait_for(req.approval_id, Duration::from_secs(req.timeout_secs.unwrap_or(120)))
            .await?;

        Ok(decision)
    }
}
```

### Approval UI Contract

The IDE plugin **must** present approval requests visually. The minimal required elements:

1. Capability name and description
2. Risk summary (plaintext)
3. Risk score badges (financial / irreversibility / privacy — threshold: 0.6 = warn, 0.8 = danger)
4. Allow / Deny buttons
5. Countdown timer matching `timeout_secs`

If the plugin does not respond within `timeout_secs`, the bridge server automatically sends
`ApprovalDecision::Deny` on behalf of the plugin. This is the **fail-closed** default.

---

## 8. Inbound File Attachments

**[PLANNED]**

The `file_attach` message lets the plugin push file contents into the session context without
the user typing `@file`. This is triggered automatically when:

- The user opens a file in the editor while a Mammoth session is active.
- The user explicitly invokes "Attach to Mammoth" from the editor command palette.
- A `context_push` message includes a `uri` the session has not yet seen.

```rust
/// [PLANNED] Inbound file attachment handler.
pub async fn handle_file_attach(
    State(state): State<Arc<AppState>>,
    headers: HeaderMap,
    Json(msg): Json<BridgeMessage>,
) -> Result<StatusCode, BridgeError> {
    let bridge_token = extract_bridge_token(&headers)?;
    let session_id = validate_bridge_token(&state, &bridge_token).await?;

    if let BridgeMessage::FileAttach { files, .. } = msg {
        for file in files {
            state
                .session_store
                .inject_file_context(&session_id, FileContext {
                    uri: file.uri,
                    content: file.content,
                    language_id: file.language_id,
                    source: FileContextSource::IdeBridge,
                })
                .await?;
        }
    }

    Ok(StatusCode::NO_CONTENT)
}
```

### Size Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max files per `file_attach` message | 20 | Prevent context flooding |
| Max bytes per file | 512 KB | LSP context window budget |
| Total attached bytes per session | 4 MB | Runtime memory budget |

Files exceeding these limits are truncated with a `[truncated — N bytes omitted]` suffix. The
server returns a `422 Unprocessable Entity` if the total attachment size exceeds the session
limit.

---

## 9. REPL Bridge

**[PLANNED]**

The REPL bridge allows Mammoth to write output back into editor buffers. This is the reverse
direction: Mammoth → Editor. The server sends `BridgeEvent::BufferWrite` or
`BridgeEvent::DiffPreview`; the plugin applies the change and responds with
`BridgeMessage::BufferWriteAck`.

### Write Modes

| `operation` | Behaviour |
|-------------|-----------|
| `replace_range` | Replaces `range` in the buffer with `content` |
| `insert_after` | Inserts `content` after the last line of `range` |
| `insert_before` | Inserts `content` before the first line of `range` |
| `replace_all` | Replaces the entire buffer (use with care — triggers undo boundary) |

### Diff Preview Flow

When the agent produces a suggested code change, the server sends `diff_preview` instead of
`buffer_write`. The plugin renders the diff in its native diff viewer (VS Code's built-in diff
editor, Neovim's `vim.diff`, etc.). The operator can:

- **Accept**: sends `user_message` with `content: "apply the diff"` — Mammoth then sends
  `buffer_write` with `operation: replace_range`.
- **Reject**: sends `user_message` with `content: "discard the diff"`.
- **Edit**: modifies the diff in the viewer, then accepts the modified version.

### Ack Timeout

The server waits up to 5 seconds for a `buffer_write_ack`. If none arrives, it logs a warning
and continues execution. Buffer writes are best-effort — they do not block workflow execution.

---

## 10. External Editor Awareness

**[PLANNED]**

Mammoth exposes editor awareness so the TUI and web UI know when an IDE bridge is active.

### `BootstrapPhase::BridgeFastPath`

**[GROUNDED — already present in `crates/compat-harness/src/lib.rs`]**

The `remote-control` bootstrap path (`BootstrapPhase::BridgeFastPath`) is the entry point
for the IDE bridge daemon mode. When Mammoth detects the `--ide-bridge` flag, it skips the
TUI and starts only the bridge server, attaching to an existing session.

```
mammoth --ide-bridge --session sess_abc123
```

### Session Metadata

When a session has an attached IDE bridge client, `SessionStore` annotates the session with:

```rust
pub struct SessionEditorBinding {
    pub editor: EditorKind,
    pub workspace_root: PathBuf,
    pub connected_at: DateTime<Utc>,
    pub last_context_push: Option<DateTime<Utc>>,
}
```

This metadata appears in:
- The TUI status bar: `[IDE: vscode]`
- The `GET /ide/status` endpoint
- Audit log entries (all events carry `actor.channel = "ide_bridge"`)

### `ChannelKind::Ide` Variant

**[PLANNED — currently `ChannelKind` has `Terminal`, `Web`, `Cli`, `Extension` in
`crates/runtime/src/channel.rs`]**

```rust
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChannelKind {
    Terminal,
    Web,
    Cli,
    Extension,
    Ide,  // ← add this variant
}
```

The `Ide` variant is used in policy evaluation: policies can be written to allow or deny
capabilities based on the originating channel.

```yaml
# Example governance policy — restrict file writes from IDE channel to workspace root
- effect: deny
  channel: ide
  capability: fs.write
  condition: "!path.starts_with(session.workspace_root)"
```

---

## 11. VS Code Extension

**[PLANNED]** Source: `plugins/vscode/`

The VS Code extension is the most grounded IDE integration — the Chrome extension bridge
(SSE + HTTP POST) maps directly onto VS Code's `EventSource` and `fetch` APIs.

### Extension Structure

```
plugins/vscode/
├── package.json
├── src/
│   ├── extension.ts          # activation, deactivation, command registration
│   ├── bridge-client.ts      # SSE connection, message dispatch
│   ├── session-manager.ts    # session create/resume, token storage
│   ├── approval-panel.ts     # WebviewPanel for approval UI
│   ├── context-provider.ts   # pushes editor context on cursor move / file open
│   ├── diff-viewer.ts        # shows BridgeEvent::DiffPreview in diff editor
│   └── status-bar.ts         # "Mammoth: Connected | sess_abc123" status bar item
└── test/
    └── extension.test.ts
```

### Activation Events

```json
{
  "activationEvents": [
    "onCommand:mammoth.connect",
    "onCommand:mammoth.newSession",
    "onStartupFinished"
  ]
}
```

### BridgeClient (TypeScript)

```typescript
// plugins/vscode/src/bridge-client.ts   [PLANNED]

export class BridgeClient {
  private eventSource: EventSource | null = null;
  private bridgeToken: string;
  private sessionId: string;
  private baseUrl: string;

  constructor(baseUrl: string, bridgeToken: string, sessionId: string) {
    this.baseUrl = baseUrl;
    this.bridgeToken = bridgeToken;
    this.sessionId = sessionId;
  }

  connect(handlers: BridgeEventHandlers): void {
    const url = `${this.baseUrl}/ide/events`;
    // VS Code's extension host does not have native EventSource; use node-fetch SSE
    this.eventSource = new EventSource(url, {
      headers: { Authorization: `Bearer ${this.bridgeToken}` },
    } as EventSourceInit);

    this.eventSource.onmessage = (ev) => {
      const event: BridgeEvent = JSON.parse(ev.data);
      this.dispatch(event, handlers);
    };

    this.eventSource.onerror = () => {
      // Reconnect with exponential backoff, max 30s
      this.scheduleReconnect(handlers);
    };
  }

  async sendMessage(msg: BridgeMessage): Promise<void> {
    await fetch(`${this.baseUrl}/ide/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.bridgeToken}`,
      },
      body: JSON.stringify(msg),
    });
  }

  async pushContext(context: EditorContext): Promise<void> {
    await this.sendMessage({
      type: "context_push",
      session_id: this.sessionId,
      context,
      timestamp: new Date().toISOString(),
    });
  }

  async sendApprovalDecision(
    approvalId: string,
    decision: "allow" | "deny"
  ): Promise<void> {
    await this.sendMessage({
      type: "approval_decision",
      approval_id: approvalId,
      session_id: this.sessionId,
      decision,
      decided_by: "human",
      timestamp: new Date().toISOString(),
    });
  }

  private dispatch(event: BridgeEvent, handlers: BridgeEventHandlers): void {
    switch (event.type) {
      case "message":          handlers.onMessage?.(event);         break;
      case "approval_request": handlers.onApprovalRequest?.(event); break;
      case "buffer_write":     handlers.onBufferWrite?.(event);     break;
      case "diff_preview":     handlers.onDiffPreview?.(event);     break;
      case "session_ended":    handlers.onSessionEnded?.(event);    break;
      case "bridge_token_expiring": handlers.onTokenExpiring?.(event); break;
    }
  }

  private scheduleReconnect(handlers: BridgeEventHandlers): void {
    // Implementation: exponential backoff 1s → 2s → 4s → … → 30s
  }

  dispose(): void {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
```

### Approval Panel

The extension opens a `WebviewPanel` when `approval_request` arrives:

```typescript
// plugins/vscode/src/approval-panel.ts   [PLANNED]

export class ApprovalPanel {
  static createOrShow(
    extensionUri: vscode.Uri,
    event: ApprovalRequestEvent,
    onDecision: (decision: "allow" | "deny") => void
  ): void {
    const panel = vscode.window.createWebviewPanel(
      "mammothApproval",
      `Mammoth: Approve ${event.capability_name}`,
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );

    panel.webview.html = ApprovalPanel.getHtml(event);

    panel.webview.onDidReceiveMessage((msg) => {
      if (msg.command === "decide") {
        onDecision(msg.decision);
        panel.dispose();
      }
    });

    // Auto-close on timeout
    const timer = setTimeout(() => {
      onDecision("deny");
      panel.dispose();
    }, event.timeout_secs * 1000);

    panel.onDidDispose(() => clearTimeout(timer));
  }
}
```

### Context Push Triggers

The extension pushes context on:

1. `vscode.window.onDidChangeActiveTextEditor` — file switch
2. `vscode.window.onDidChangeTextEditorSelection` (debounced 500 ms) — selection change
3. `vscode.languages.onDidChangeDiagnostics` (debounced 1 s) — diagnostic update
4. Explicit `mammoth.pushContext` command

---

## 12. Neovim Bridge

**[PLANNED]** Source: `plugins/neovim/`

Neovim exposes a native JSON-RPC channel (via `vim.fn.jobstart`, `vim.rpcrequest`, and
`nvim_exec_lua`). The bridge reuses the `Content-Length` framing from `lsp/src/client.rs`
over the Unix socket transport (§3.2).

### Plugin Structure

```
plugins/neovim/
├── lua/
│   └── mammoth/
│       ├── init.lua           # public API, setup(), connect()
│       ├── bridge.lua         # socket I/O, JSON-RPC read/write loop
│       ├── session.lua        # session create/resume, token management
│       ├── approval.lua       # floating window approval UI
│       ├── context.lua        # BufEnter / CursorMoved autocmd context push
│       └── diff.lua           # shows diff_preview in a scratch buffer
└── plugin/
    └── mammoth.vim            # lazy-load entry point
```

### Socket Connection (Lua)

```lua
-- plugins/neovim/lua/mammoth/bridge.lua   [PLANNED]

local M = {}
local uv = vim.loop

function M.connect(socket_path, on_event)
  local client = uv.new_pipe(false)

  uv.pipe_connect(client, socket_path, function(err)
    if err then
      vim.notify("[mammoth] bridge connect failed: " .. err, vim.log.levels.ERROR)
      return
    end

    -- Read loop: parse Content-Length frames
    local buf = ""
    uv.read_start(client, function(read_err, data)
      if read_err or not data then return end
      buf = buf .. data

      while true do
        local header_end = buf:find("\r\n\r\n")
        if not header_end then break end

        local header = buf:sub(1, header_end - 1)
        local len_str = header:match("Content%-Length: (%d+)")
        if not len_str then break end

        local len = tonumber(len_str)
        local body_start = header_end + 4
        if #buf < body_start + len - 1 then break end

        local body = buf:sub(body_start, body_start + len - 1)
        buf = buf:sub(body_start + len)

        local ok, event = pcall(vim.json.decode, body)
        if ok then on_event(event) end
      end
    end)
  end)

  M._client = client
  return client
end

function M.send(client, msg)
  local body = vim.json.encode(msg)
  local frame = string.format("Content-Length: %d\r\n\r\n%s", #body, body)
  uv.write(client, frame)
end

return M
```

### Approval Floating Window

```lua
-- plugins/neovim/lua/mammoth/approval.lua   [PLANNED]

local M = {}

function M.show(event, on_decision)
  local lines = {
    "  MAMMOTH APPROVAL REQUEST  ",
    "",
    "Capability: " .. event.capability_name,
    "Description: " .. event.description,
    "",
    event.risk_summary,
    "",
    string.format(
      "Risk: financial=%.1f  irreversibility=%.1f  privacy=%.1f",
      event.risk_score.financial,
      event.risk_score.irreversibility,
      event.risk_score.privacy
    ),
    "",
    "[a] Allow     [d] Deny",
  }

  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)

  local width = 60
  local height = #lines + 2
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor",
    width = width,
    height = height,
    row = math.floor((vim.o.lines - height) / 2),
    col = math.floor((vim.o.columns - width) / 2),
    style = "minimal",
    border = "rounded",
    title = " Mammoth Approval ",
    title_pos = "center",
  })

  -- Timeout countdown using vim.fn.timer_start
  local remaining = event.timeout_secs
  local timer = vim.fn.timer_start(1000, function()
    remaining = remaining - 1
    if remaining <= 0 then
      vim.api.nvim_win_close(win, true)
      on_decision("deny")
    end
    -- update countdown line
  end, { ["repeat"] = event.timeout_secs })

  local opts = { buffer = buf, noremap = true, silent = true }
  vim.keymap.set("n", "a", function()
    vim.fn.timer_stop(timer)
    vim.api.nvim_win_close(win, true)
    on_decision("allow")
  end, opts)
  vim.keymap.set("n", "d", function()
    vim.fn.timer_stop(timer)
    vim.api.nvim_win_close(win, true)
    on_decision("deny")
  end, opts)
end

return M
```

### Context Push Autocmds

```lua
-- plugins/neovim/lua/mammoth/context.lua   [PLANNED]

local bridge = require("mammoth.bridge")
local M = {}

local function current_context()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  local ft = vim.bo[buf].filetype
  local cursor = vim.api.nvim_win_get_cursor(0)

  local diagnostics = vim.diagnostic.get(buf)
  local diag_list = {}
  for _, d in ipairs(diagnostics) do
    table.insert(diag_list, {
      range = {
        start = { line = d.lnum, character = d.col },
        ["end"] = { line = d.end_lnum or d.lnum, character = d.end_col or d.col },
      },
      severity = ({ "error", "warning", "information", "hint" })[d.severity],
      message = d.message,
      source = d.source,
    })
  end

  return {
    uri = "file://" .. file,
    language_id = ft,
    version = vim.api.nvim_buf_get_changedtick(buf),
    selection = {
      start = { line = cursor[1] - 1, character = cursor[2] },
      ["end"] = { line = cursor[1] - 1, character = cursor[2] },
    },
    diagnostics = diag_list,
  }
end

function M.setup(client, session_id)
  local group = vim.api.nvim_create_augroup("MammothContext", { clear = true })

  vim.api.nvim_create_autocmd({ "BufEnter", "CursorMoved" }, {
    group = group,
    callback = vim.schedule_wrap(function()
      local ctx = current_context()
      bridge.send(client, {
        type = "context_push",
        session_id = session_id,
        context = ctx,
        timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ"),
      })
    end),
  })
end

return M
```

---

## 13. JetBrains Plugin

**[PLANNED]** Source: `plugins/jetbrains/`

The JetBrains plugin is the least grounded integration — no existing Mammoth code targets the
JetBrains Platform SDK directly. The plugin targets IntelliJ IDEA, GoLand, RustRover, and
WebStorm via the IntelliJ Platform Plugin SDK.

### Transport Choice

JetBrains extensions run in a JVM process separate from the IDE UI thread. The HTTP/SSE
transport (§3.1) is the simplest option: the plugin uses OkHttp for SSE streaming and
`HttpURLConnection` (or Ktor client) for POST requests.

The Unix socket transport is available on macOS/Linux via Java's `UnixDomainSocketAddress`
(JDK 16+), which aligns with the minimum JVM target for modern JetBrains plugins.

### Plugin Structure

```
plugins/jetbrains/
├── build.gradle.kts
├── src/main/kotlin/io/aicp/mammoth/
│   ├── MammothPlugin.kt          # ApplicationService, plugin lifecycle
│   ├── BridgeClient.kt           # OkHttp SSE + POST
│   ├── SessionManager.kt         # session create/resume, SecureStore token
│   ├── ApprovalDialog.kt         # DialogWrapper approval UI
│   ├── ContextProvider.kt        # FileEditorManagerListener, caret listeners
│   └── DiffViewer.kt             # DiffContent + DiffManager for diff_preview
└── src/main/resources/
    └── META-INF/plugin.xml
```

### BridgeClient (Kotlin)

```kotlin
// plugins/jetbrains/src/main/kotlin/io/aicp/mammoth/BridgeClient.kt   [PLANNED]

class BridgeClient(
    private val baseUrl: String,
    private val bridgeToken: String,
    private val sessionId: String,
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)  // SSE: no read timeout
        .build()

    private var eventCall: Call? = null

    fun connect(handler: BridgeEventHandler) {
        val request = Request.Builder()
            .url("$baseUrl/ide/events")
            .header("Authorization", "Bearer $bridgeToken")
            .build()

        eventCall = client.newCall(request)
        eventCall!!.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                handler.onError(e)
                scheduleReconnect(handler)
            }

            override fun onResponse(call: Call, response: Response) {
                response.body?.source()?.let { source ->
                    while (!source.exhausted()) {
                        val line = source.readUtf8Line() ?: break
                        if (line.startsWith("data: ")) {
                            val json = line.removePrefix("data: ")
                            val event = Json.decodeFromString<BridgeEvent>(json)
                            handler.onEvent(event)
                        }
                    }
                }
            }
        })
    }

    fun sendMessage(msg: BridgeMessage) {
        val body = Json.encodeToString(msg)
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("$baseUrl/ide/message")
            .header("Authorization", "Bearer $bridgeToken")
            .post(body)
            .build()
        client.newCall(request).execute().close()
    }

    fun disconnect() {
        eventCall?.cancel()
        eventCall = null
    }
}
```

### Approval Dialog

```kotlin
// plugins/jetbrains/src/main/kotlin/io/aicp/mammoth/ApprovalDialog.kt   [PLANNED]

class ApprovalDialog(
    project: Project,
    private val event: BridgeEvent.ApprovalRequest,
) : DialogWrapper(project) {

    init {
        title = "Mammoth: Approve ${event.capabilityName}"
        init()
    }

    override fun createCenterPanel(): JComponent {
        val panel = JPanel(VerticalFlowLayout())
        panel.add(JLabel("<html><b>${event.capabilityName}</b></html>"))
        panel.add(JLabel(event.description))
        panel.add(JSeparator())
        panel.add(JLabel(event.riskSummary))
        panel.add(JLabel(buildRiskBadges(event.riskScore)))
        return panel
    }

    // isOK() == true → Allow, false → Deny
    private fun buildRiskBadges(score: RiskScore): String =
        "Financial: ${pct(score.financial)}  " +
        "Irreversibility: ${pct(score.irreversibility)}  " +
        "Privacy: ${pct(score.privacy)}"

    private fun pct(v: Float) = "${(v * 100).toInt()}%"
}
```

---

## 14. Zed Extension

**[PLANNED]** Source: `plugins/zed/`

Zed extensions are written in Rust and compiled to WASM. The extension API is newer and still
evolving; this integration has the least source grounding. The primary mechanism is Zed's
`language_server` extension point, which allows injecting a sidecar process that speaks
JSON-RPC. The bridge reuses the Unix socket JSON-RPC transport from §3.2.

### Extension Structure

```
plugins/zed/
├── Cargo.toml
├── extension.toml
└── src/
    └── lib.rs     # zed_extension_api::Extension impl
```

### Extension Entry Point

```rust
// plugins/zed/src/lib.rs   [PLANNED]

use zed_extension_api::{self as zed, Result};

struct MammothExtension;

impl zed::Extension for MammothExtension {
    fn new() -> Self {
        MammothExtension
    }

    fn language_server_command(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<zed::Command> {
        // Launch the bridge sidecar: `mammoth --ide-bridge --editor zed`
        // The sidecar writes its socket path to stdout on first line
        Ok(zed::Command {
            command: "mammoth".into(),
            args: vec![
                "--ide-bridge".into(),
                "--editor".into(),
                "zed".into(),
                "--workspace".into(),
                worktree.root_path().to_string(),
            ],
            env: vec![],
        })
    }
}

zed::register_extension!(MammothExtension);
```

### Limitations

- Zed's WASM sandbox has no direct socket access; the sidecar process pattern works around
  this by having Zed launch `mammoth --ide-bridge` and communicate over stdio.
- Approval UI in Zed requires `zed::workspace::open_modal`, which is not yet stable in the
  extension API. Short-term fallback: emit a notification with an "Allow" action button.
- `buffer_write` support depends on Zed's `workspace::edit` API being available in WASM
  extensions — verify against the current `zed_extension_api` crate version before
  implementing.

---

## 15. Configuration Reference

**[PLANNED]** New section added to `crates/runtime/src/config.rs` under `RuntimeFeatureConfig`:

```toml
# .mammoth/settings.json  (shown as TOML for readability; actual format is JSON)

[ide_bridge]
# Enable the IDE bridge server
enabled = true

# Unix socket path (preferred for local connections)
socket_path = "/run/mammoth/ide-bridge.sock"

# TCP fallback (useful for WSL, Docker, or remote development)
tcp_host = "127.0.0.1"
tcp_port = 37291

# Bridge token TTL in seconds
token_ttl_secs = 900

# Maximum attached file bytes per session
max_attachment_bytes = 4194304

# Maximum files per file_attach message
max_files_per_message = 20

# Context push debounce (milliseconds)
context_push_debounce_ms = 500

# Approval timeout (seconds) — overrides per-capability setting
default_approval_timeout_secs = 120

# Trust tier ceiling for IDE bridge sessions (cannot exceed session trust tier)
trust_tier_ceiling = 2

# Allowed editors (empty = all allowed)
allowed_editors = []
```

### Rust Config Struct

**[PLANNED]** `crates/runtime/src/config.rs`:

```rust
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct IdeBridgeConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,

    #[serde(default = "default_socket_path")]
    pub socket_path: String,

    pub tcp_host: Option<String>,
    pub tcp_port: Option<u16>,

    #[serde(default = "default_token_ttl")]
    pub token_ttl_secs: u64,

    #[serde(default = "default_max_attachment")]
    pub max_attachment_bytes: usize,

    #[serde(default = "default_max_files")]
    pub max_files_per_message: usize,

    #[serde(default = "default_debounce")]
    pub context_push_debounce_ms: u64,

    #[serde(default = "default_approval_timeout")]
    pub default_approval_timeout_secs: u32,

    #[serde(default = "default_trust_ceiling")]
    pub trust_tier_ceiling: u8,

    #[serde(default)]
    pub allowed_editors: Vec<String>,
}

fn default_true()              -> bool   { true }
fn default_socket_path()       -> String { "/run/mammoth/ide-bridge.sock".into() }
fn default_token_ttl()         -> u64    { 900 }
fn default_max_attachment()    -> usize  { 4 * 1024 * 1024 }
fn default_max_files()         -> usize  { 20 }
fn default_debounce()          -> u64    { 500 }
fn default_approval_timeout()  -> u32    { 120 }
fn default_trust_ceiling()     -> u8     { 2 }
```

---

## 16. Implementation Roadmap

### Phase 1 — Server Foundation (1–2 weeks)

**Files to create:**

| File | Action | Description |
|------|--------|-------------|
| `crates/server/src/ide_bridge.rs` | Create | Full `IdeBridgeServer` axum router, SSE handler, message handler, session handler, auth middleware |
| `crates/runtime/src/channel.rs` | Modify | Add `ChannelKind::Ide` variant; add `IdeBridgeChannel` struct implementing `Channel` trait |
| `crates/runtime/src/config.rs` | Modify | Add `IdeBridgeConfig` struct; add `ide_bridge: Option<IdeBridgeConfig>` field to `RuntimeFeatureConfig` |
| `crates/server/src/lib.rs` | Modify | Mount `/ide/*` router alongside existing `/ext/*` routes |

**Tests to add:**

- `crates/server/tests/ide_bridge_auth.rs` — token validation, bearer extraction
- `crates/server/tests/ide_bridge_sse.rs` — SSE stream receives `BridgeEvent`
- `crates/server/tests/ide_bridge_approval.rs` — full approval round-trip

### Phase 2 — VS Code Extension (1 week)

**Files to create:**

| File | Action |
|------|--------|
| `plugins/vscode/package.json` | Create |
| `plugins/vscode/src/extension.ts` | Create |
| `plugins/vscode/src/bridge-client.ts` | Create |
| `plugins/vscode/src/session-manager.ts` | Create |
| `plugins/vscode/src/approval-panel.ts` | Create |
| `plugins/vscode/src/context-provider.ts` | Create |
| `plugins/vscode/src/diff-viewer.ts` | Create |
| `plugins/vscode/src/status-bar.ts` | Create |

### Phase 3 — Neovim Plugin (1 week)

**Files to create:**

| File | Action |
|------|--------|
| `plugins/neovim/lua/mammoth/init.lua` | Create |
| `plugins/neovim/lua/mammoth/bridge.lua` | Create |
| `plugins/neovim/lua/mammoth/session.lua` | Create |
| `plugins/neovim/lua/mammoth/approval.lua` | Create |
| `plugins/neovim/lua/mammoth/context.lua` | Create |
| `plugins/neovim/lua/mammoth/diff.lua` | Create |
| `plugins/neovim/plugin/mammoth.vim` | Create |

### Phase 4 — JetBrains Plugin (2 weeks)

| File | Action |
|------|--------|
| `plugins/jetbrains/build.gradle.kts` | Create |
| `plugins/jetbrains/src/main/kotlin/.../BridgeClient.kt` | Create |
| `plugins/jetbrains/src/main/kotlin/.../SessionManager.kt` | Create |
| `plugins/jetbrains/src/main/kotlin/.../ApprovalDialog.kt` | Create |
| `plugins/jetbrains/src/main/kotlin/.../ContextProvider.kt` | Create |

### Phase 5 — Zed Extension (1 week, after Zed WASM API stabilises)

| File | Action |
|------|--------|
| `plugins/zed/Cargo.toml` | Create |
| `plugins/zed/extension.toml` | Create |
| `plugins/zed/src/lib.rs` | Create |

### Phase 6 — Integration and Audit (1 week)

- Wire `ChannelKind::Ide` into the policy engine (`crates/runtime/src/policy.rs`)
- Add `actor.channel = "ide_bridge"` to all audit log entries
- Add `[IDE: <editor>]` indicator to TUI status bar (`apps/mammoth/src/tui/`)
- Add `--ide-bridge` flag to `apps/mammoth/src/main.rs` to trigger `BridgeFastPath`
- Add IDE bridge section to `docs/guides/CONFIGURATION.md`
- Add `BootstrapPhase::IdeBridgeFastPath` alongside existing `BridgeFastPath` in
  `crates/compat-harness/src/lib.rs`

---

## 17. Security Considerations

### Token Scope

- Bridge tokens are scoped to a single session. They cannot be used to create new sessions.
- Bridge tokens carry an explicit `trust_tier_ceiling`. Even if the underlying session has
  trust tier 4, the IDE plugin receives at most tier 2 by default.
- Bridge tokens are stored in memory only — they are never written to disk by the server.

### Trust Boundary

The IDE bridge is treated as a **human-proxied channel** — similar to the Chrome extension,
not the CLI. This means:

- All capability invocations from IDE context go through full policy evaluation.
- `approval_gated` capabilities always produce `BridgeEvent::ApprovalRequest` — they are
  never auto-approved.
- The plugin cannot escalate trust tier by any message sequence.

### Localhost-Only Default

The TCP transport binds to `127.0.0.1` only. Remote access requires explicit configuration
(`tcp_host = "0.0.0.0"`) plus a valid session token. The Unix socket is `0600` by default
(owner-only).

### Context Injection Sanitisation

Inbound `context_push` and `file_attach` messages are treated as **untrusted input**:

- File URIs are canonicalised and checked against the session's `workspace_root`. Files
  outside the workspace root are rejected with `403 Forbidden`.
- `selected_text` and `content` fields are length-limited before being injected into session
  context.
- Diagnostic messages are stripped of ANSI escape sequences.

### Replay Attack Prevention

Each `BridgeMessage` carries a `timestamp`. The server rejects messages with timestamps more
than 60 seconds in the past or future. This prevents replay of captured approval decisions.

### Audit Trail

All IDE bridge events — context pushes, approval decisions, buffer writes — are written to
the append-only audit journal with:

```json
{
  "actor": {
    "type": "human",
    "channel": "ide_bridge",
    "editor": "vscode",
    "session_id": "sess_abc123"
  },
  "event": "approval_decision",
  "approval_id": "appr_xyz789",
  "decision": "allow",
  "timestamp": "2026-04-05T10:00:10Z"
}
```

This ensures every IDE-originated approval decision is attributable and replayable, satisfying
the architectural invariant that **every execution event MUST be attributable to agent, human,
or system actor**.

---

## Summary of Source Grounding

| IDE | Grounding level | Notes |
|-----|----------------|-------|
| VS Code | High | Chrome MV3 SSE+POST pattern maps directly. `ExtEvent`, `ApprovalRequest` shapes reused verbatim. |
| Neovim | Medium | JSON-RPC + `Content-Length` framing from `lsp/src/client.rs` maps to Neovim's socket channel. Approval UI is novel. |
| JetBrains | Low | No existing JVM code. HTTP/SSE transport reused; plugin SDK patterns are standard JetBrains boilerplate. |
| Zed | Lowest | Zed WASM extension API is unstable. Sidecar stdio pattern is a workaround, not a clean integration. |

## Protocol Design Decisions Needing Team Review

1. **Approval fail-closed on plugin timeout** — the server auto-denies if the plugin does not
   respond within `timeout_secs`. This is conservative. Should there be a per-capability
   override to fail-open for low-risk capabilities?

2. **`trust_tier_ceiling = 2` default** — IDE channel is treated as human-proxied, capped at
   tier 2. Is this the right default, or should IDE sessions start at tier 1 (requires
   explicit elevation)?

3. **`buffer_write` as best-effort vs. blocking** — currently buffer writes do not block
   workflow execution. Should high-risk `buffer_write` operations (e.g., `replace_all`) block
   until `buffer_write_ack` is received?

4. **Zed sidecar vs. native WASM** — the sidecar approach bypasses the WASM sandbox but adds
   a process dependency. Should Zed support be deferred until the `zed_extension_api` exposes
   stable socket and buffer APIs?

5. **Context push rate limiting** — `CursorMoved` can fire hundreds of times per second.
   The 500 ms debounce is a starting point. Should the server also enforce a server-side
   rate limit per session to protect against misbehaving plugins?
