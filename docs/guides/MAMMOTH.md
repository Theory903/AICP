# Mammoth Architecture

> The Interaction OS — four channels, one execution backbone.

---

## Overview

Mammoth is the interaction layer for AICP. It provides four channels through which humans and agents issue intent, observe execution, and supervise outcomes:

| Channel | Entry Point | Description |
|---------|-------------|-------------|
| **Terminal** | `mammoth` | Conversational REPL — full-capability, streaming, keyboard-driven |
| **Web** | `mammoth serve` | Studio supervision console + conversational UI — approvals, audit, workflows |
| **CLI** | `mammoth <subcommand>` | Multi-channel dispatcher and programmatic interface |
| **Extension** | `mammoth ext` | Chrome MV3 — page-aware agent overlay backed by Mammoth Web |

Every channel is a different rendering surface for the same underlying thing: a governed, stateful, policy-evaluated agent session backed by AICP.

---

## Crate Structure

Mammoth is a Rust Cargo workspace at `apps/mammoth/`.

```
apps/mammoth/
├── Cargo.toml             # workspace root
├── crates/
│   ├── aicp/              # AICP middleware (L1 complete)
│   ├── api/               # Provider API clients
│   ├── runtime/           # Conversation runtime + channel abstraction
│   ├── tools/             # ~18 tool implementations
│   ├── mammoth-cli/       # Terminal + CLI channel (binary: mammoth)
│   ├── server/            # Web channel backend (axum)
│   ├── commands/          # Slash command implementations
│   ├── plugins/           # Plugin system
│   └── lsp/               # LSP integration
└── extension/             # Chrome MV3 extension
    ├── manifest.json
    ├── background.js
    ├── content.js
    ├── popup.html
    └── popup.js
```

---

## Channel Abstraction

The `Channel` trait in `crates/runtime/src/channel.rs` is the interface all four channels implement:

```rust
use serde_json::Value;

/// Discriminant for routing and logging.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChannelKind {
    Terminal,
    Web,
    Cli,
    Extension,
}

/// A Mammoth interaction channel.
pub trait Channel: Send + Sync {
    fn kind(&self) -> ChannelKind;

    /// Render a model or tool message to the user.
    fn render_message(&self, message: &ConversationMessage);

    /// Present an AICP approval request and return the user's decision.
    fn request_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;

    /// Called on tool progress events (streaming tool output).
    fn on_tool_progress(&self, tool_use_id: &str, partial: &str);

    /// Called when the channel should clean up (session end).
    fn shutdown(&self);
}

/// AICP approval request routed to the channel's approval UI.
#[derive(Debug, Clone)]
pub struct ApprovalRequest {
    pub approval_id: String,
    pub capability_name: String,
    pub description: String,
    pub risk_summary: String,
    pub channel: ChannelKind,
}

/// Decision returned by the channel's approval UI.
#[derive(Debug, Clone)]
pub struct ApprovalDecision {
    pub approved: bool,
    pub comment: Option<String>,
    pub decided_by: Option<String>,
}
```

---

## Terminal Channel

**Entry point:** `crates/mammoth-cli/src/main.rs`
**Binary:** `mammoth`

The terminal channel is a full-featured conversational REPL. It:

- Streams AI model responses character-by-character with syntax highlighting
- Renders tool calls and results inline
- Presents AICP approval prompts as interactive inline questions
- Supports `--yes` flag to auto-approve all governance gates
- Supports `--no-input` for non-interactive scripted use

### Slash Commands

The following slash commands are currently implemented (`crates/mammoth-cli/src/app.rs`):

| Command | Description |
|---------|-------------|
| `/help` | Print available slash commands |
| `/status` | Show current session status (model, token usage, AICP connection) |
| `/compact` | Compact conversation history to reduce token usage |

The following slash commands are **planned** (Phase 3, v0.4.0+):

| Command | Description |
|---------|-------------|
| `/approve` | Approve a pending AICP governance gate |
| `/audit` | Show audit trail for the current session |
| `/workflow` | Show workflow status |
| `/plan` | Enter plan mode (worktree-isolated) |

### TUI Components (Planned)

The following TUI panels are planned for v0.4.0 (Phase 3) and are **not yet built**:

- Model picker (`m` key)
- Session browser (`s` key)
- Tool execution timeline
- Context sidebar (token budget, active files)
- Plan viewer (when in plan mode)

### Key Types

```
LiveCli
  └── ConversationRuntime<DefaultRuntimeClient, AicpToolExecutor<CliToolExecutor>>
        └── AicpToolExecutor (crates/aicp/) — AICP middleware (L1)
              └── CliToolExecutor (crates/tools/) — actual tool implementations
```

### Starting the Terminal Channel

```bash
mammoth                    # interactive REPL, default model
mammoth --model opus       # specify model
mammoth "fix this bug"     # single-turn prompt mode
mammoth --yes              # auto-approve AICP governance gates
```

---

## Web Channel

**Entry point:** `crates/server/src/lib.rs` (axum server)
**Started via:** `mammoth serve [--port N]`

The web channel serves the Mammoth Studio — the supervision console and conversational UI. It is the successor to `apps/studio/`.

> **Current state (v0.3.0):** The axum server is fully implemented with session management, SSE streaming, and the extension bridge. The Studio HTML served at `/` is a placeholder stub. A full supervision UI (approval queue, audit viewer, workflow timeline) is planned for Phase 3 (v0.4.0).

### HTTP API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sessions` | Create new conversation session |
| `GET` | `/sessions` | List all sessions |
| `GET` | `/sessions/{id}` | Get session details |
| `GET` | `/sessions/{id}/events` | SSE stream of session events |
| `POST` | `/sessions/{id}/message` | Send message to session |
| `GET` | `/ext/events` | SSE stream for Chrome extension bridge |
| `POST` | `/ext/message` | Receive message from Chrome extension |
| `GET` | `/` | Studio HTML (embedded) |
| `GET` | `/health` | Health check |

### Session Events (SSE)

```json
{ "type": "snapshot", "session_id": "session-1", "session": { ... } }
{ "type": "message", "session_id": "session-1", "message": { ... } }
{ "type": "approval_request", "session_id": "session-1", "request": { ... } }
{ "type": "tool_use", "session_id": "session-1", "name": "bash", "input": { ... } }
```

### Starting the Web Channel

```bash
mammoth serve              # default port 3000
mammoth serve --port 8080  # custom port
```

Open `http://localhost:3000` in a browser to access the Studio console.

---

## CLI Channel

**Entry point:** `crates/mammoth-cli/src/main.rs`

The CLI channel is the programmatic dispatcher. It routes to other channels and provides direct command access.

### Output Formats

When running `mammoth "prompt"` (non-interactive), output format is controlled by `--output`:

| Format | Flag | Description |
|--------|------|-------------|
| Text | `--output text` (default) | Human-readable streamed text |
| JSON | `--output json` | Structured JSON response envelope |
| NDJSON | `--output ndjson` | Newline-delimited JSON events (for piping) |

```bash
mammoth "summarize this file" --output json | jq .data
mammoth "list open PRs" --output ndjson | while read line; do echo "$line"; done
```

### Commands

```
mammoth                         → terminal REPL (interactive)
mammoth serve [--port N]        → start web channel
mammoth ext                     → start extension bridge
mammoth "prompt text"           → single-turn prompt
mammoth --resume <session>      → resume a session
mammoth agents                  → list agents
mammoth skills                  → list skills
mammoth login                   → authenticate
mammoth logout                  → deauthenticate
mammoth init                    → initialize project
mammoth --version               → print version
mammoth --help                  → print help
```

---

## Extension Channel

**Location:** `apps/mammoth/extension/`
**Started via:** `mammoth ext` (starts bridge endpoint on Mammoth Web)

The Chrome extension is a MV3 overlay that connects to the Mammoth Web channel. It:

1. Captures page context (URL, a11y tree, active element) via content script
2. Relays user intent to Mammoth Web via SSE/POST
3. Renders AI responses as an overlay on the current page

### Files

| File | Role |
|------|------|
| `manifest.json` | Chrome MV3 manifest (permissions: `activeTab`, `storage`, `scripting`) |
| `background.js` | Service worker — maintains SSE connection to Mammoth Web |
| `content.js` | Content script — page context capture, relay to background |
| `popup.html` | Browser action popup — minimal conversational UI |
| `popup.js` | Popup logic — send/receive via background |

### Extension ↔ Web Channel Protocol

```
Extension background.js
    ↓ EventSource('/ext/events')
Mammoth Web (crates/server) /ext/events SSE
    ↓ broadcasts events

Extension popup.js
    → POST /ext/message { "message": "...", "page_context": { ... } }
Mammoth Web → ConversationRuntime → AICP → response
    → SSE event back to extension
```

### Required Permissions

```json
{
  "permissions": ["activeTab", "storage", "scripting"],
  "host_permissions": ["http://localhost:*/*"]
}
```

---

## AICP Integration

Mammoth integrates with AICP at exactly one point: the `AicpToolExecutor<T>` wrapper in `crates/aicp/`.

```rust
// All channels use this composition pattern:
let executor = AicpToolExecutor::new(
    underlying_tool_executor,  // e.g. CliToolExecutor
    aicp_config,               // AICP_URL, trust_tier, etc.
);
let conversation = ConversationRuntime::new(client, executor);
```

The `AicpToolExecutor` intercepts every tool call and:

1. Sends it to AICP for policy evaluation
2. If `allow` → executes the tool
3. If `require_approval` → routes to the channel's `request_approval()` method
4. If `deny` → returns structured error with `fix_hint`
5. Wraps all results in AICP `ExecutionEnvelope`

### AicpConfig

```rust
// crates/runtime/src/config.rs
pub struct AicpConfig {
    pub url: String,          // default: http://localhost:10003
    pub trust_tier: u8,       // 0–4
    pub enabled: bool,
}
```

Set `AICP_URL` environment variable to override the default endpoint.

---

## Compliance Levels (Mammoth)

| Level | Mammoth Feature | Status |
|-------|----------------|--------|
| L1 | AicpToolExecutor wrapping all tool calls | Complete |
| L2 | ComputerUseTool (Anthropic `computer_20251124` API) | Planned |
| L3 | Dream memory crate | Planned |
| L4 | AICP slash commands (`/approve`, `/audit`, `/workflow`) | Planned |
| L5 | AICP tool wrappers (capabilities, workflows, policies via Mammoth) | Planned |
| L6 | Heartbeat + channel health monitoring | Planned |
| L7 | OpenAI-compatible API via `mammoth serve` | Planned |

---

## See Also

- [VISION.md](../overview/VISION.md) — Mammoth + AICP dual OS vision
- [ARCHITECTURE.md](./ARCHITECTURE.md) — Full system architecture with data flow
- [COMPARISON.md](../overview/COMPARISON.md) — Mammoth vs Claude Code, OpenCode, Cursor, Windsurf, Warp
- [/apps/mammoth/crates/aicp/](../../apps/mammoth/crates/aicp/) — AICP middleware source
- [/apps/mammoth/crates/server/](../../apps/mammoth/crates/server/) — Web channel backend source
- [/apps/mammoth/extension/](../../apps/mammoth/extension/) — Chrome extension source
