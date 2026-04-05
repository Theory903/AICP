# Remote Sessions and Web Channel

> Implementation guide for remote session context, the upstream proxy, and the web channel server in Mammoth. An engineer with zero prior context should be able to implement all three systems from this document alone.

---

## Overview

This document covers two related but distinct systems inside Mammoth:

**1. Remote Session / Upstream Proxy (`crates/runtime/src/remote.rs`)**

When Mammoth runs inside a controlled remote environment (e.g., a cloud sandbox or CI container), it needs to route outbound API calls through a locally-running HTTP proxy that can inject TLS certificates and forward a session authentication token. The upstream proxy system handles bootstrapping that proxy: reading config from the environment, reading the session token from disk, deriving the WebSocket URL used to connect to the proxy control channel, and constructing the environment variables injected into every subprocess spawned by Mammoth.

**2. Web Channel HTTP Server (`crates/server/src/lib.rs`)**

`mammoth serve` starts an axum HTTP server that exposes:
- A Studio supervision UI (HTML embedded at compile time)
- A REST + SSE API for managing conversation sessions
- A bridge for the Chrome MV3 extension (`GET /ext/events`, `POST /ext/message`)

Both systems implement parts of the larger Channel abstraction defined in `crates/runtime/src/channel.rs`. The `Channel` trait is also covered here because it is the interface that ties all four Mammoth channels (Terminal, Web, CLI, Extension) to the same execution backbone.

---

## Remote Session Context

### What it is

`RemoteSessionContext` captures whether Mammoth is running in remote mode, what its session identity is, and what base URL to use for API calls. It is always constructed from environment variables — there is no config file.

Remote mode is opt-in. When disabled (the default), Mammoth communicates directly with the Anthropic API with no proxy and no session token. When enabled, all outbound HTTPS traffic from subprocesses is routed through the upstream proxy.

### Struct

```rust
pub struct RemoteSessionContext {
    pub enabled: bool,           // MAMMOTH_CODE_REMOTE — truthy: "1", "true", "yes", "on"
    pub session_id: Option<String>,  // MAMMOTH_CODE_REMOTE_SESSION_ID
    pub base_url: String,        // ANTHROPIC_BASE_URL, default: https://api.anthropic.com
}
```

**Field semantics:**

| Field | Source | Default | Notes |
|-------|--------|---------|-------|
| `enabled` | `MAMMOTH_CODE_REMOTE` | `false` | Truthy values: `"1"`, `"true"`, `"yes"`, `"on"` (case-insensitive). Any other value → false. |
| `session_id` | `MAMMOTH_CODE_REMOTE_SESSION_ID` | `None` | If unset or empty, remote mode cannot fully activate even if `enabled = true`. |
| `base_url` | `ANTHROPIC_BASE_URL` | `"https://api.anthropic.com"` | Used to derive the WebSocket URL for the upstream proxy control channel. |

### Truthy boolean parsing

The `MAMMOTH_CODE_REMOTE` env var is parsed as a boolean. Only these four values (compared case-insensitively after trimming whitespace) are truthy:

```
"1"   "true"   "yes"   "on"
```

Everything else — including empty string, `"0"`, `"false"`, unset — is falsy. Implement this as an explicit allowlist, not a generic truthiness check.

---

## Upstream Proxy

### What it is

The upstream proxy is a local HTTP proxy process that Mammoth boots to intercept outbound HTTPS traffic from all subprocesses (tool runners, language runtimes, package managers). Its two jobs are:

1. **TLS certificate injection** — it presents a locally-trusted CA certificate so it can inspect and re-sign TLS traffic.
2. **Auth token forwarding** — it reads a session token from disk and forwards it in outbound requests to Anthropic infrastructure.

Mammoth does not implement the proxy itself. It bootstraps the connection to an externally-managed proxy process over a WebSocket control channel, and then injects the correct environment variables into every subprocess it spawns so that subprocess traffic flows through the proxy.

### UpstreamProxyBootstrap struct

`UpstreamProxyBootstrap` holds all configuration needed to decide whether to enable the proxy and how to connect to it.

```rust
pub struct UpstreamProxyBootstrap {
    pub remote: RemoteSessionContext,
    pub upstream_proxy_enabled: bool,  // CCR_UPSTREAM_PROXY_ENABLED (truthy semantics)
    pub token_path: PathBuf,           // CCR_SESSION_TOKEN_PATH, default: /run/ccr/session_token
    pub ca_bundle_path: PathBuf,       // CCR_CA_BUNDLE_PATH, default: ~/.ccr/ca-bundle.crt
    pub system_ca_path: PathBuf,       // CCR_SYSTEM_CA_BUNDLE, default: /etc/ssl/certs/ca-certificates.crt
    pub token: Option<String>,         // Contents of token_path, trimmed. None if file missing or empty.
}
```

**Field sources:**

| Field | Env var | Default |
|-------|---------|---------|
| `upstream_proxy_enabled` | `CCR_UPSTREAM_PROXY_ENABLED` | `false` |
| `token_path` | `CCR_SESSION_TOKEN_PATH` | `/run/ccr/session_token` |
| `ca_bundle_path` | `CCR_CA_BUNDLE_PATH` | `~/.ccr/ca-bundle.crt` (expand `~` to `$HOME`) |
| `system_ca_path` | `CCR_SYSTEM_CA_BUNDLE` | `/etc/ssl/certs/ca-certificates.crt` |
| `token` | _(read from `token_path` at construction time)_ | `None` |

The `remote` field is a `RemoteSessionContext` constructed from its own env vars (see above).

`token` is populated during construction by calling `read_token(token_path)`.

### should_enable()

The upstream proxy is enabled only when ALL FOUR of the following conditions are true:

```
remote.enabled == true
AND upstream_proxy_enabled == true
AND remote.session_id.is_some()
AND token.is_some()
```

If any condition fails, the proxy is disabled and subprocesses receive no proxy environment variables. This is fail-safe: a misconfigured or partially-configured remote environment runs without a proxy rather than with a broken one.

### ws_url()

The WebSocket URL for the proxy's control channel is derived from `remote.base_url` by:

1. Replacing the URL scheme: `https://` → `wss://`, `http://` → `ws://`
2. Appending the path `/v1/code/upstreamproxy/ws`

Examples:

| base_url | ws_url |
|----------|--------|
| `https://api.anthropic.com` | `wss://api.anthropic.com/v1/code/upstreamproxy/ws` |
| `http://localhost:8080` | `ws://localhost:8080/v1/code/upstreamproxy/ws` |

No other part of the URL (host, port, existing path, query) is modified.

```rust
pub fn ws_url(&self) -> String {
    upstream_proxy_ws_url(&self.remote.base_url)
}

fn upstream_proxy_ws_url(base_url: &str) -> String {
    let ws_base = if let Some(rest) = base_url.strip_prefix("https://") {
        format!("wss://{}", rest)
    } else if let Some(rest) = base_url.strip_prefix("http://") {
        format!("ws://{}", rest)
    } else {
        base_url.to_string()
    };
    // strip any trailing slash before appending path
    let ws_base = ws_base.trim_end_matches('/');
    format!("{}/v1/code/upstreamproxy/ws", ws_base)
}
```

### state_for_port(port)

Once the proxy process is running on a known local port, call `state_for_port(port)` to produce the `UpstreamProxyState` used by the rest of Mammoth:

```rust
pub fn state_for_port(&self, port: u16) -> UpstreamProxyState {
    UpstreamProxyState {
        enabled: true,
        proxy_url: Some(format!("http://127.0.0.1:{}", port)),
        ca_bundle_path: Some(self.ca_bundle_path.clone()),
        no_proxy: no_proxy_list(),
    }
}
```

The proxy URL is always `http://127.0.0.1:{port}` — it is a plain HTTP proxy on loopback (TLS is handled by the proxy itself for outbound traffic, not for the loopback leg).

### UpstreamProxyState struct

```rust
pub struct UpstreamProxyState {
    pub enabled: bool,
    pub proxy_url: Option<String>,       // "http://127.0.0.1:{port}"
    pub ca_bundle_path: Option<PathBuf>, // path to the locally-trusted CA bundle
    pub no_proxy: String,                // comma-separated list of bypass hosts
}
```

When `enabled = false`, `proxy_url` and `ca_bundle_path` are `None` and `no_proxy` is empty.

### subprocess_env()

`UpstreamProxyState::subprocess_env()` returns a `BTreeMap<String, String>` that is merged into the environment of every subprocess Mammoth spawns. This ensures tool runners, shells, npm, pip, cargo, curl, and every other subprocess routes traffic through the proxy.

When `enabled = true`, all 8 keys are set:

| Env var | Value |
|---------|-------|
| `HTTPS_PROXY` | `proxy_url` (e.g. `http://127.0.0.1:8888`) |
| `https_proxy` | same as `HTTPS_PROXY` |
| `NO_PROXY` | `no_proxy` (comma-separated bypass list) |
| `no_proxy` | same as `NO_PROXY` |
| `SSL_CERT_FILE` | `ca_bundle_path` as string |
| `NODE_EXTRA_CA_CERTS` | `ca_bundle_path` as string |
| `REQUESTS_CA_BUNDLE` | `ca_bundle_path` as string |
| `CURL_CA_BUNDLE` | `ca_bundle_path` as string |

Both the uppercase and lowercase variants of `HTTPS_PROXY` and `NO_PROXY` are set because different programs check different casings. When `enabled = false`, `subprocess_env()` returns an empty map — callers must not unconditionally merge; an empty result means no proxy vars are set.

### read_token(path)

```rust
fn read_token(path: &Path) -> Result<Option<String>, std::io::Error> {
    match std::fs::read_to_string(path) {
        Ok(contents) => {
            let trimmed = contents.trim().to_string();
            if trimmed.is_empty() {
                Ok(None)
            } else {
                Ok(Some(trimmed))
            }
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e),
    }
}
```

Rules:
- File not found → `Ok(None)` (not an error — proxy simply won't enable)
- File exists but empty (or only whitespace after trimming) → `Ok(None)`
- File exists with content → `Ok(Some(trimmed_string))`
- I/O error other than NotFound → `Err(e)` (propagate)

Always trim the token. Token files often have a trailing newline written by shell scripts or secret-injection tooling.

### no_proxy_list()

`no_proxy_list()` returns the complete comma-separated NO_PROXY string. It concatenates the 16-entry `NO_PROXY_HOSTS` constant with 3 additional package registry hosts:

```rust
pub const NO_PROXY_HOSTS: [&str; 16] = [
    "localhost",
    "127.0.0.1",
    "::1",
    "169.254.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "anthropic.com",
    ".anthropic.com",
    "*.anthropic.com",
    "github.com",
    "api.github.com",
    "*.github.com",
    "*.githubusercontent.com",
    "registry.npmjs.org",
    "index.crates.io",
];

fn no_proxy_list() -> String {
    let mut hosts: Vec<&str> = NO_PROXY_HOSTS.to_vec();
    hosts.extend_from_slice(&["pypi.org", "files.pythonhosted.org", "proxy.golang.org"]);
    hosts.join(",")
}
```

The final list has **19 entries**. Anthropic and GitHub hosts are bypassed so that direct API calls and source fetches do not go through the proxy. Package registries are bypassed so that dependency installs are not intercepted.

### inherited_upstream_proxy_env()

When Mammoth itself is launched from an environment that already has an upstream proxy configured, it may need to inherit that configuration. `inherited_upstream_proxy_env()` inspects a provided env map and returns the proxy env vars — but **only if BOTH `HTTPS_PROXY` AND `SSL_CERT_FILE` are present**.

```rust
pub const UPSTREAM_PROXY_ENV_KEYS: [&str; 8] = [
    "HTTPS_PROXY", "https_proxy",
    "NO_PROXY",    "no_proxy",
    "SSL_CERT_FILE", "NODE_EXTRA_CA_CERTS",
    "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
];

fn inherited_upstream_proxy_env(env_map: &HashMap<String, String>) -> HashMap<String, String> {
    let has_proxy = env_map.contains_key("HTTPS_PROXY");
    let has_cert  = env_map.contains_key("SSL_CERT_FILE");
    if has_proxy && has_cert {
        UPSTREAM_PROXY_ENV_KEYS
            .iter()
            .filter_map(|k| env_map.get(*k).map(|v| (k.to_string(), v.clone())))
            .collect()
    } else {
        HashMap::new()
    }
}
```

The dual-key requirement prevents partial proxy configurations from being silently forwarded. A proxy without a CA bundle would cause TLS errors in subprocesses.

---

## Web Channel Server

### Architecture

The `server` crate (`crates/server/`) is an [axum](https://github.com/tokio-rs/axum) HTTP server. It holds all state in `AppState`, which is `Clone`-able and injected into every handler via axum's `Extension` extractor.

```rust
pub struct AppState {
    sessions: SessionStore,               // Arc<RwLock<HashMap<SessionId, Session>>>
    next_session_id: Arc<AtomicU64>,
    ext_events: ExtBroadcast,            // broadcast::Sender<ExtEvent>, capacity 64
    runner: Option<Arc<dyn TurnRunner>>,
}
```

- `sessions` — `Arc<RwLock<HashMap<SessionId, Session>>>`. Read lock for list/get/SSE; write lock for create/send-message.
- `next_session_id` — monotonically incrementing `AtomicU64` used to generate session IDs.
- `ext_events` — a tokio broadcast channel (capacity 64) for pushing events to Chrome extension SSE subscribers.
- `runner` — optional AI inference backend. If `None`, user messages are stored but receive no AI reply.

`SessionId` is a `String` of the form `"session-{n}"` where `n` is the atomic counter value.

### Session struct

```rust
pub struct Session {
    pub id: SessionId,
    pub created_at: u64,              // unix timestamp in milliseconds
    pub conversation: RuntimeSession, // full conversation state (messages, metadata)
    events: broadcast::Sender<SessionEvent>,  // capacity 64
}
```

Each session has its own broadcast channel. When a client connects to `GET /sessions/{id}/events`, it subscribes to this channel. On connect, the server immediately sends a `Snapshot` event so the client gets full state without polling. Subsequent messages are delivered as `Message` events.

### Routes

All 9 routes, with request and response types:

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `GET` | `/health` | — | `{"status":"ok","service":"mammoth-web"}` | Plain JSON, 200 |
| `GET` | `/` | — | HTML | Studio HTML, `include_str!("studio.html")` |
| `POST` | `/sessions` | — | `CreateSessionResponse` | 201 Created |
| `GET` | `/sessions` | — | `ListSessionsResponse` | 200 |
| `GET` | `/sessions/{id}` | — | `SessionDetailsResponse` | 200, 404 if not found |
| `GET` | `/sessions/{id}/events` | — | SSE stream | `text/event-stream` |
| `POST` | `/sessions/{id}/message` | `SendMessageRequest` | — | 204 No Content |
| `GET` | `/ext/events` | — | SSE stream | Extension SSE, `text/event-stream` |
| `POST` | `/ext/message` | `SendMessageRequest` | — | 204 No Content |

### Response types

```rust
pub struct CreateSessionResponse {
    pub session_id: SessionId,
}

pub struct SessionSummary {
    pub id: SessionId,
    pub created_at: u64,
    pub message_count: usize,
}

pub struct ListSessionsResponse {
    pub sessions: Vec<SessionSummary>,
}

pub struct SessionDetailsResponse {
    pub id: SessionId,
    pub created_at: u64,
    pub session: RuntimeSession,
}

pub struct SendMessageRequest {
    pub message: String,
}
```

All response types serialize to JSON. `created_at` is Unix time in milliseconds.

### Session lifecycle

1. **Create** (`POST /sessions`)
   - Atomically increment `next_session_id` to get `n`
   - Construct `id = format!("session-{}", n)`
   - Set `created_at = SystemTime::now()` as Unix millis
   - Create a new `broadcast::channel(64)` for session events
   - Insert into `sessions` map under write lock
   - Return `201 { "session_id": "session-{n}" }`

2. **List** (`GET /sessions`)
   - Acquire read lock
   - Collect all sessions as `SessionSummary` (id, created_at, message_count)
   - Return sorted by creation time (ascending) or insertion order

3. **Get** (`GET /sessions/{id}`)
   - Acquire read lock
   - Look up session, return 404 if not found
   - Return full `SessionDetailsResponse` including `RuntimeSession`

4. **Send message** (`POST /sessions/{id}/message`)
   - Acquire write lock, look up session, return 404 if not found
   - Append the user message to `conversation`
   - Release write lock
   - If `runner` is `Some`:
     - Clone `history` and `user_text`
     - Spawn `tokio::task::spawn_blocking(|| runner.run_turn(history, user_text))`
     - On success: acquire write lock, append each returned `ConversationMessage`, broadcast each as a `Message` SSE event
     - On error: broadcast a synthetic message with content `format!("[error] {}", msg)`
   - Return 204

5. **SSE stream** (`GET /sessions/{id}/events`)
   - Look up session, return 404 if not found
   - Subscribe to session's broadcast channel: `events.subscribe()`
   - Immediately send a `Snapshot` event with the full current session state
   - Stream subsequent events as they arrive
   - Set keepalive interval to **15 seconds**

### SSE event format

Session SSE events:

```rust
enum SessionEvent {
    Snapshot { session_id: SessionId, session: RuntimeSession },
    Message  { session_id: SessionId, message: ConversationMessage },
}
```

SSE wire format:

```
event: snapshot
data: {"session_id":"session-1","session":{...}}

event: message
data: {"session_id":"session-1","message":{...}}
```

The `Snapshot` event is always the first event sent to any new subscriber. Clients must handle receiving a snapshot at connect time and use it to initialize their local state before applying incremental `message` events.

### Broadcast capacity

- Per-session event channel: **64** messages
- Extension event channel: **64** messages

When a subscriber is too slow and the channel fills, the oldest messages are dropped (tokio broadcast semantics). Clients that fall behind will miss events and should reconnect, at which point they receive a fresh `Snapshot`.

### TurnRunner trait

`TurnRunner` is the interface for plugging in an AI inference backend:

```rust
pub trait TurnRunner: Send + Sync {
    fn run_turn(
        &self,
        history: Vec<ConversationMessage>,
        user_message: String,
    ) -> Result<Vec<ConversationMessage>, String>;
}
```

- The method is synchronous (`fn`, not `async fn`). The server wraps it in `tokio::task::spawn_blocking`.
- `history` is the full conversation history before the current user message.
- Returns `Vec<ConversationMessage>` — the new messages to append (typically one assistant message, but may be multiple for tool-use turns).
- Returns `Err(String)` on failure. The error message is surfaced to the client as a synthetic `[error] {msg}` message in the session.
- If `AppState::runner` is `None`, no inference is performed. The user message is stored and the session receives no reply.

Implement `TurnRunner` on a struct that holds your API client, model config, and system prompt. Wrap it in `Arc<dyn TurnRunner>` before passing to `AppState`.

### serve() convenience function

```rust
pub async fn serve(
    listener: tokio::net::TcpListener,
    state: AppState,
) -> Result<(), std::io::Error>
```

Builds the axum router, attaches `state` as a shared extension, and calls `axum::serve(listener, router).await`. The caller is responsible for binding the `TcpListener` to the desired address/port. This function does not return unless the server errors.

---

## Extension Bridge

The Chrome MV3 extension communicates with the Mammoth server over two dedicated routes:

### GET /ext/events

Server-Sent Events stream for the extension background service worker. The extension connects on startup and holds the connection open.

```rust
pub enum ExtEvent {
    Message {
        content: String,
    },
    ApprovalRequest {
        approval_id: String,
        capability_name: String,
        description: String,
    },
}
```

SSE wire format:

```
event: message
data: {"content":"Hello from the agent"}

event: approval_request
data: {"approval_id":"apr_123","capability_name":"browser.click","description":"Click the submit button"}
```

The extension's `background.js` maintains an `EventSource` to this endpoint and forwards incoming events to the popup and content scripts via `chrome.runtime.sendMessage`.

### POST /ext/message

Receives messages from the extension popup:

```
POST /ext/message
Content-Type: application/json

{"message": "user text from popup"}
```

Returns `204 No Content`. The message is broadcast to all current extension SSE subscribers via `ext_events`. It is not stored in any session by default — the caller (the `mammoth ext` command handler) is responsible for routing it to the appropriate session if desired.

---

## Channel Trait

### Definition

The `Channel` trait in `crates/runtime/src/channel.rs` is the interface all four Mammoth channels implement. It is object-safe and designed to be used as `Arc<dyn Channel>`.

```rust
pub trait Channel: Send + Sync {
    fn name(&self) -> &str;
    fn kind(&self) -> ChannelKind;
    fn render_message(&self, content: &str);
    fn request_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;
    fn on_tool_progress(&self, tool_name: &str, message: &str) {}  // default: no-op
    fn shutdown(&self) {}                                           // default: no-op
}
```

### Methods

| Method | Required | Semantics |
|--------|----------|-----------|
| `name()` | Yes | Human-readable channel name for logging and display (e.g., `"terminal"`, `"web"`) |
| `kind()` | Yes | `ChannelKind` discriminant for routing and audit |
| `render_message(content)` | Yes | Display or stream a message to the user. Implementation determines presentation (terminal output, SSE event, etc.) |
| `request_approval(request)` | Yes | Block until the user makes an approval decision. Returns an `ApprovalDecision`. |
| `on_tool_progress(tool_name, message)` | No (default no-op) | Called during long-running tool execution to provide progress updates. Channels that support streaming UI implement this; others ignore it. |
| `shutdown()` | No (default no-op) | Called when the session is ending. Channels that hold resources (open files, network connections) clean up here. |

### ChannelKind

```rust
pub enum ChannelKind {
    Terminal,
    Web,
    Cli,
    Extension,
}
```

`ChannelKind` is `Copy + Clone + PartialEq + Eq + Hash`. It is included in execution envelopes as the `actor.channel` field so audit entries record which surface initiated the action.

### ApprovalRequest

```rust
pub struct ApprovalRequest {
    pub approval_id: String,
    pub capability_name: String,
    pub description: String,
    pub risk_summary: Option<String>,
    pub channel: ChannelKind,
}
```

`approval_id` is a stable identifier for this approval request, used to correlate the decision with the pending execution in the governance engine. `channel` indicates which channel surface should handle the approval — this allows the runtime to route approval requests to the correct channel even in multi-channel scenarios.

### ApprovalDecision

```rust
pub struct ApprovalDecision {
    pub approval_id: String,
    pub approved: bool,
    pub comment: Option<String>,
    pub decided_by: Option<String>,
}
```

`decided_by` is the human principal identifier (username, email) when the decision was made by a human. It is `None` for programmatic or automated approvals.

### Implementation rules

- Channels **MUST NOT** contain orchestration logic. A channel renders and collects input; it does not drive the execution loop.
- `request_approval` **MUST** block (or async-await) until the decision is made. The execution engine calls this synchronously and expects a decision before proceeding.
- `render_message` **MUST NOT** fail silently. If the output surface is unavailable, log the error and continue — do not panic.
- `shutdown` **MUST** be idempotent. It may be called more than once.

---

## Integration: Connecting Channels to AICP

### ChannelKind in execution envelopes

Every AICP execution envelope includes an `actor` field. When a capability execution is initiated through a Mammoth channel, the `actor` is populated as:

```json
{
  "actor": {
    "type": "agent",
    "agent_id": "mammoth",
    "session_id": "sess_...",
    "channel": "web"
  }
}
```

The `channel` value is the lowercase string representation of `ChannelKind`. This flows into audit journal entries, allowing post-hoc analysis of which surface initiated which actions.

### Approval request flow

When the AICP governance engine evaluates a capability with `effect: "require_approval"`, it calls `channel.request_approval(request)`. The flow is:

1. Governance engine constructs `ApprovalRequest` with a fresh `approval_id`
2. Calls `channel.request_approval(&request)`
3. Channel blocks until human decision:
   - **Terminal channel**: renders an interactive prompt, reads keyboard input
   - **Web channel**: broadcasts `ExtEvent::ApprovalRequest` via SSE, blocks waiting for a response on the approval endpoint
   - **CLI channel**: prints to stdout, reads from stdin
   - **Extension channel**: sends `approval_request` SSE event to `background.js`, blocks until popup posts decision
4. Channel returns `ApprovalDecision`
5. Governance engine records the decision in the audit journal
6. If `approved == true`: execution proceeds
7. If `approved == false`: execution is rejected with `effect: "deny"`

The `approval_id` in the `ApprovalDecision` **MUST** match the `approval_id` in the `ApprovalRequest`. The governance engine validates this before accepting the decision.

---

## Studio HTML

`GET /` serves the Studio supervision UI. The HTML is embedded at compile time using Rust's `include_str!` macro:

```rust
async fn serve_root() -> impl IntoResponse {
    Html(include_str!("studio.html"))
}
```

The `studio.html` file lives at `crates/server/src/studio.html` and is compiled into the binary. No filesystem access occurs at runtime. This means:

- No external file serving configuration is needed
- The binary is self-contained and deployable as a single file
- Changes to `studio.html` require recompilation

The current `studio.html` is a minimal placeholder. The planned state is a full SPA build output embedded via the same mechanism (or served from a static directory in development mode with a feature flag).

---

## Planned Extensions

The following capabilities are planned but not yet implemented. Do not present them as available.

| Feature | Description | Blocking on |
|---------|-------------|-------------|
| **SPA build** | Full Studio SPA (React/Svelte) served from compiled binary or static dir | Studio UI build pipeline |
| **RemoteSessionManager** | Long-lived manager that maintains the WebSocket connection to the upstream proxy, handles reconnection, and exposes session lifecycle events | Upstream proxy server implementation |
| **WebPTY server** | WebSocket-based PTY server for streaming terminal output from tool runners to the Studio UI | PTY multiplexing design |
| **Desktop deep-link handoff** | `mammoth://` URL scheme for handing off sessions between browser and native TUI | macOS/Linux URL scheme registration |
| **Multi-session routing** | Route messages to named sessions by ID from the extension | Session routing table |
| **Approval webhook** | Push approval requests to an external URL instead of blocking the SSE channel | Governance engine webhook support |

---

## Environment Variable Reference

All environment variables consumed by the remote session and upstream proxy systems:

| Variable | System | Default | Truthy semantics | Notes |
|----------|--------|---------|-----------------|-------|
| `MAMMOTH_CODE_REMOTE` | RemoteSessionContext | `false` | `"1"`, `"true"`, `"yes"`, `"on"` | Master switch for remote mode |
| `MAMMOTH_CODE_REMOTE_SESSION_ID` | RemoteSessionContext | — | N/A (string) | Required for proxy to enable |
| `ANTHROPIC_BASE_URL` | RemoteSessionContext | `https://api.anthropic.com` | N/A | Also used by API clients directly |
| `CCR_UPSTREAM_PROXY_ENABLED` | UpstreamProxyBootstrap | `false` | same as above | Must be true alongside remote mode |
| `CCR_SESSION_TOKEN_PATH` | UpstreamProxyBootstrap | `/run/ccr/session_token` | N/A (path) | File must exist and be non-empty |
| `CCR_CA_BUNDLE_PATH` | UpstreamProxyBootstrap | `~/.ccr/ca-bundle.crt` | N/A (path) | Locally-trusted CA bundle for TLS |
| `CCR_SYSTEM_CA_BUNDLE` | UpstreamProxyBootstrap | `/etc/ssl/certs/ca-certificates.crt` | N/A (path) | System CA bundle |
| `HTTPS_PROXY` | subprocess_env / inherited | — | N/A | Set to `http://127.0.0.1:{port}` |
| `https_proxy` | subprocess_env / inherited | — | N/A | Lowercase alias, same value |
| `NO_PROXY` | subprocess_env / inherited | — | N/A | Comma-separated bypass list |
| `no_proxy` | subprocess_env / inherited | — | N/A | Lowercase alias, same value |
| `SSL_CERT_FILE` | subprocess_env / inherited | — | N/A | Path to CA bundle for OpenSSL-based tools |
| `NODE_EXTRA_CA_CERTS` | subprocess_env / inherited | — | N/A | Path to CA bundle for Node.js |
| `REQUESTS_CA_BUNDLE` | subprocess_env / inherited | — | N/A | Path to CA bundle for Python requests |
| `CURL_CA_BUNDLE` | subprocess_env / inherited | — | N/A | Path to CA bundle for curl |

`inherited_upstream_proxy_env()` requires **both** `HTTPS_PROXY` and `SSL_CERT_FILE` to be present in the parent environment before it forwards any proxy vars. A lone `HTTPS_PROXY` without `SSL_CERT_FILE` is treated as absent.

---

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| `RemoteSessionContext` | Complete | `crates/runtime/src/remote.rs` |
| `UpstreamProxyBootstrap` | Complete | `crates/runtime/src/remote.rs` |
| `UpstreamProxyState` | Complete | `crates/runtime/src/remote.rs` |
| `subprocess_env()` | Complete | `crates/runtime/src/remote.rs` |
| `no_proxy_list()` | Complete | `crates/runtime/src/remote.rs` |
| `inherited_upstream_proxy_env()` | Complete | `crates/runtime/src/remote.rs` |
| Web channel server (axum) | Complete | `crates/server/src/lib.rs` |
| Session store | Complete | `crates/server/src/lib.rs` |
| SSE session events | Complete | `crates/server/src/lib.rs` |
| Extension bridge (SSE + message) | Complete | `crates/server/src/lib.rs` |
| `TurnRunner` trait | Complete | `crates/server/src/lib.rs` |
| `serve()` fn | Complete | `crates/server/src/lib.rs` |
| `Channel` trait | Complete | `crates/runtime/src/channel.rs` |
| Studio HTML placeholder | Complete | `crates/server/src/studio.html` |
| Studio SPA build | Planned | — |
| RemoteSessionManager | Planned | — |
| WebPTY server | Planned | — |
| Desktop deep-link handoff | Planned | — |

---

## File Locations

| File | Purpose |
|------|---------|
| `apps/mammoth/crates/runtime/src/remote.rs` | `RemoteSessionContext`, `UpstreamProxyBootstrap`, `UpstreamProxyState`, all helper functions |
| `apps/mammoth/crates/runtime/src/channel.rs` | `Channel` trait, `ChannelKind`, `ApprovalRequest`, `ApprovalDecision` |
| `apps/mammoth/crates/server/src/lib.rs` | Axum server, `AppState`, `Session`, all route handlers, `TurnRunner` trait, `serve()` |
| `apps/mammoth/crates/server/src/studio.html` | Studio placeholder HTML, embedded at compile time |
| `apps/mammoth/extension/background.js` | Chrome MV3 service worker, connects to `/ext/events` |
| `apps/mammoth/extension/popup.js` | Extension popup, posts to `/ext/message` |
