# MCP Integration Guide — Mammoth

**Status:** Implemented (client stack) / Planned (dynamic tools, OAuth flow UI)
**Source:** `apps/mammoth/crates/runtime/src/mcp_client.rs`, `mcp.rs`, `mcp_stdio.rs`, `config.rs`
**Also see:** `mcp/` (MCP server — exposes AICP capabilities outward to MCP clients)

---

## Two Directions

Mammoth has two separate MCP roles that solve opposite problems:

| Direction | Location | Purpose |
|-----------|----------|---------|
| **MCP Client** | `apps/mammoth/crates/runtime/src/mcp_client.rs` | Mammoth *consumes* external MCP servers as tool sources |
| **MCP Server** | `mcp/` | Mammoth/AICP *exposes* its capabilities to external MCP clients |

This document covers the **MCP Client** stack — how Mammoth connects to, names, and calls tools
from external MCP servers.

---

## Transport Types

All MCP server connections are represented as a `McpClientTransport` enum:

```rust
// apps/mammoth/crates/runtime/src/mcp_client.rs
pub enum McpClientTransport {
    Stdio(McpStdioTransport),
    Sse(McpRemoteTransport),
    Http(McpRemoteTransport),
    WebSocket(McpRemoteTransport),
    Sdk(McpSdkTransport),
    ManagedProxy(McpManagedProxyTransport),
}
```

### `Stdio`

Launches a local subprocess and communicates via stdin/stdout (JSON-RPC over pipes).

```rust
pub struct McpStdioTransport {
    pub command: String,           // e.g. "uvx"
    pub args: Vec<String>,         // e.g. ["mcp-server-git"]
    pub env: BTreeMap<String, String>, // injected into subprocess environment
}
```

**Config example (`~/.mammoth/config.toml`):**
```toml
[mcp.servers.git]
type = "stdio"
command = "uvx"
args = ["mcp-server-git"]

[mcp.servers.filesystem]
type = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
```

### `Sse` / `Http`

Remote MCP servers reachable over HTTP. SSE uses server-sent events for streaming; HTTP uses
request/response polling.

```rust
pub struct McpRemoteTransport {
    pub url: String,
    pub headers: BTreeMap<String, String>,  // static auth headers
    pub headers_helper: Option<String>,      // path to script that emits dynamic headers
    pub auth: McpClientAuth,                 // None or OAuth(config)
}
```

**Config example:**
```toml
[mcp.servers.vendor]
type = "http"
url = "https://api.vendor.example/mcp"

[mcp.servers.vendor.headers]
"X-API-Key" = "sk-..."

# Dynamic headers via helper script
headers_helper = ".mammoth/vendor-headers.sh"
```

**Headers helper script** (`vendor-headers.sh`):
```bash
#!/bin/sh
# Output must be JSON: {"Header-Name": "value", ...}
echo '{"Authorization": "Bearer '$(cat ~/.vendor-token)'"}'
```

### `WebSocket`

Full-duplex WebSocket connection. Does not support OAuth (no `auth` field).

```toml
[mcp.servers.live-feed]
type = "ws"
url = "wss://live.vendor.example/mcp"
```

### `Sdk`

A named SDK-provided transport (for integrations that ship their own Rust/Node SDK). No signature
can be computed for SDK transports (signature is `None`).

```toml
[mcp.servers.internal]
type = "sdk"
name = "mammoth-internal"
```

### `ManagedProxy`

Used for proxied connections (e.g. through the AICP control plane's CCR proxy layer). The `id`
field identifies the session on the proxy.

```toml
[mcp.servers.proxied]
type = "managed_proxy"
url = "https://api.anthropic.com/v2/ccr-sessions/abc123"
id = "abc123"
```

---

## Authentication

```rust
pub enum McpClientAuth {
    None,
    OAuth(McpOAuthConfig),
}
```

### OAuth

```rust
pub struct McpOAuthConfig {
    /// OAuth client ID (optional — some flows use PKCE without pre-registered client ID)
    pub client_id: Option<String>,
    /// Local port for the OAuth callback server (default: random ephemeral port)
    pub callback_port: Option<u16>,
    /// URL to the OAuth Authorization Server metadata document
    pub auth_server_metadata_url: Option<String>,
    /// XAA (Cross-Agent Authorization) extension flag
    pub xaa: Option<bool>,
}
```

**Config example:**
```toml
[mcp.servers.vendor]
type = "http"
url = "https://api.vendor.example/mcp"

[mcp.servers.vendor.oauth]
client_id = "mammoth-client"
callback_port = 7777
auth_server_metadata_url = "https://auth.vendor.example/.well-known/oauth-authorization-server"
```

**OAuth flow (planned TUI):**
1. On first connection, Mammoth opens a browser tab to the authorization URL
2. User grants access; browser redirects to `http://localhost:7777/callback`
3. Mammoth exchanges the code for tokens
4. Tokens stored in `~/.mammoth/mcp-tokens/{server-name}.json`
5. Tokens refreshed automatically when expired

`requires_user_auth()` returns `true` for OAuth transports:
```rust
impl McpClientAuth {
    pub const fn requires_user_auth(&self) -> bool {
        matches!(self, Self::OAuth(_))
    }
}
```

---

## Bootstrap

`McpClientBootstrap` is the pre-computed connection descriptor built at startup for each
configured MCP server.

```rust
pub struct McpClientBootstrap {
    /// Raw server name as configured (e.g. "My GitHub Server")
    pub server_name: String,
    /// Normalized name safe for tool prefixes (e.g. "My_GitHub_Server")
    pub normalized_name: String,
    /// Prefix for all tool names from this server (e.g. "mcp__My_GitHub_Server__")
    pub tool_prefix: String,
    /// Content-based signature for change detection (None for SDK transports)
    pub signature: Option<String>,
    /// Resolved transport target
    pub transport: McpClientTransport,
}
```

**Building a bootstrap:**
```rust
let bootstrap = McpClientBootstrap::from_scoped_config("github.com", &scoped_config);
// bootstrap.normalized_name == "github_com"
// bootstrap.tool_prefix     == "mcp__github_com__"
// bootstrap.signature       == Some("url:https://github.example/mcp")
```

---

## Tool Naming

MCP tool names follow a deterministic namespaced format to prevent collisions.

### Functions (source: `apps/mammoth/crates/runtime/src/mcp.rs`)

```rust
/// Normalize a server name: replace non-alphanumeric chars with '_'
pub fn normalize_name_for_mcp(name: &str) -> String
// "github.com"             → "github_com"
// "tool name!"             → "tool_name_"
// "claude.ai Example   Server!!" → "claude_ai_Example_Server"  (collapses underscores, trims)

/// Full prefix for all tools from a server
pub fn mcp_tool_prefix(server_name: &str) -> String
// "github.com"  → "mcp__github_com__"

/// Full scoped tool name
pub fn mcp_tool_name(server_name: &str, tool_name: &str) -> String
// ("github.com", "create_issue") → "mcp__github_com__create_issue"
```

### Naming rules

1. Server name is normalized: any character outside `[a-zA-Z0-9_-]` becomes `_`
2. Special case: `claude.ai ` prefix gets consecutive underscores collapsed and leading/trailing
   underscores trimmed
3. Tool name from the server is normalized with the same rules
4. Final form: `mcp__{normalized_server}__{normalized_tool}`

### Scoped tool name in usage

When the model calls a tool, the tool name in `ContentBlock::ToolUse.name` is the full scoped
name. The runtime strips the prefix to find the server and dispatches accordingly:

```rust
fn dispatch_mcp_tool(full_name: &str, input: &str) -> Result<String, ToolError> {
    // "mcp__github_com__create_issue"
    //  → server = "github_com", tool = "create_issue"
    let (server_prefix, tool_name) = split_mcp_tool_name(full_name)?;
    let bootstrap = find_bootstrap_by_prefix(&server_prefix)?;
    bootstrap.call_tool(tool_name, input).await
}
```

---

## Server Signature and Config Hash

### Signature

Used for change detection when reconnecting: if the signature hasn't changed since the last
connection, the server's tool list can be used from cache.

```rust
pub fn mcp_server_signature(config: &McpServerConfig) -> Option<String>
// Stdio:  "stdio:[uvx|mcp-server-git]"
// HTTP:   "url:https://api.vendor.example/mcp"
// SSE:    "url:https://api.vendor.example/mcp"
// WS:     "url:wss://live.vendor.example/mcp"
// Proxy:  "url:wss://vendor.example/mcp"  (unwraps CCR proxy URL)
// SDK:    None
```

CCR proxy URLs are unwrapped before signing — the signature tracks the real upstream URL, not
the proxy path:
```rust
pub fn unwrap_ccr_proxy_url(url: &str) -> String
// "https://api.anthropic.com/v2/ccr-sessions/1?mcp_url=wss%3A%2F%2Fvendor.example%2Fmcp"
// → "wss://vendor.example/mcp"
```

### Config hash

A stable 16-character hex hash of the full config (including headers, OAuth params). Used for
cache invalidation — if the hash changes, all cached tool lists for that server are discarded.

```rust
pub fn scoped_mcp_config_hash(config: &ScopedMcpServerConfig) -> String
```

Hash inputs by transport type:
- **Stdio:** `stdio|{command}|{args}|{env}`
- **SSE:** `sse|{url}|{headers}|{headers_helper}|{oauth}`
- **HTTP:** `http|{url}|{headers}|{headers_helper}|{oauth}`
- **WS:** `ws|{url}|{headers}|{headers_helper}`
- **SDK:** `sdk|{name}`
- **Proxy:** `claudeai-proxy|{url}|{id}`

Hash function: FNV-1a (64-bit), output as zero-padded 16-char hex. Scope (`user`/`project`/`local`)
is intentionally excluded — a server's hash should be the same regardless of which config file
declared it.

---

## Config Scopes

MCP server configurations can come from three sources, merged in precedence order:

| Scope | File | Precedence |
|-------|------|-----------|
| `local` | `.mammoth/config.toml` (project, git-ignored) | Highest |
| `project` | `.mammoth/config.shared.toml` (project, committed) | Middle |
| `user` | `~/.mammoth/config.toml` (global) | Lowest |

Project config is committed and shared. Local config overrides for personal dev setup.

---

## Dynamic Tools

When connected to an MCP server, Mammoth:

1. Calls `mcp/list_tools` at startup (and on reconnect)
2. Converts each tool's JSON schema to Mammoth's internal `ToolDef`
3. Injects all tools into the model's tool list for the session

Tools from MCP servers appear in the model context exactly like built-in tools, except:
- Their names carry the `mcp__<server>__` prefix
- Their descriptions are taken verbatim from the MCP server's `list_tools` response
- Permission mode for MCP tool calls defaults to `DangerFullAccess` (requires approval unless
  the session is in `allow` or `danger-full-access` mode)

### Dynamic commands (planned)

If the MCP server implements `mcp/list_commands`, Mammoth registers each command as a slash
command: `/mcp-<server>-<command-name>`.

### Dynamic resources (planned)

`ListMcpResourcesTool` and `ReadMcpResourceTool` allow the model to browse and read resources
exposed by the MCP server:

```
list_mcp_resources(server="github_com")
→ [{uri: "github://owner/repo/issues", name: "Issues list", mimeType: "application/json"}, ...]

read_mcp_resource(server="github_com", uri="github://owner/repo/issues")
→ "[{\"id\": 1, \"title\": \"...\"}]"
```

---

## Reconnect and Backoff

For remote transports (SSE, HTTP, WebSocket), Mammoth uses exponential backoff on failure:

```
Attempt 1: connect
Failure → wait 1s
Attempt 2: connect
Failure → wait 2s
Attempt 3: connect
Failure → wait 4s
...
Max wait: 30s
After 5 consecutive failures: mark server as unavailable, remove tools from context
```

Stdio transports do not reconnect — if the subprocess exits, the server is permanently
unavailable for that session.

---

## Built-in MCP Tool Wrappers

Three built-in tools provide direct MCP server access to the model:

| Tool | Description |
|------|-------------|
| `mcp` | Low-level: call any method on any connected MCP server |
| `list_mcp_resources` | List resources available from a server |
| `read_mcp_resource` | Read the content of a specific resource URI |

See `docs/guides/TOOLS_REFERENCE.md` for full schemas.

---

## The MCP Server (Outward Direction)

`mcp/` exposes AICP capabilities to external MCP clients (e.g. Claude Desktop, other agents).

```
External MCP Client
    ↓ mcp/call_tool("aicp.capability.execute", {...})
AICP MCP Server (mcp/)
    ↓ HTTP POST /api/capabilities/{name}/execute
AICP Runtime
```

This is separate from the MCP client stack described above. The server is a standalone binary
that wraps the AICP HTTP API as MCP tool definitions.

---

## Adding a New MCP Server

### Via config file

```toml
# ~/.mammoth/config.toml
[mcp.servers.my-server]
type = "stdio"
command = "npx"
args = ["-y", "@my-org/mcp-server"]

[mcp.servers.my-server.env]
MY_TOKEN = "..."
```

### Via `/mcp add` slash command (planned)

```
/mcp add stdio --name my-server --command "npx" --args "-y,@my-org/mcp-server"
/mcp add http  --name my-api --url https://api.example.com/mcp --oauth
/mcp list
/mcp remove my-server
```

### Via TUI model picker MCP tab (planned)

The model picker (`Ctrl+M`) includes an MCP tab showing all configured servers, their connection
status, and a button to add new ones.

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| `McpClientTransport` enum | **Done** | `runtime/src/mcp_client.rs` |
| `McpClientBootstrap` | **Done** | `runtime/src/mcp_client.rs` |
| `McpClientAuth` + OAuth config | **Done** | `runtime/src/mcp_client.rs` |
| `normalize_name_for_mcp` | **Done** | `runtime/src/mcp.rs` |
| `mcp_tool_name` / `mcp_tool_prefix` | **Done** | `runtime/src/mcp.rs` |
| `mcp_server_signature` | **Done** | `runtime/src/mcp.rs` |
| `scoped_mcp_config_hash` | **Done** | `runtime/src/mcp.rs` |
| `unwrap_ccr_proxy_url` | **Done** | `runtime/src/mcp.rs` |
| Stdio subprocess launcher | **Done** | `runtime/src/mcp_stdio.rs` |
| SSE/HTTP/WS client | Planned | `runtime/src/mcp_remote.rs` |
| OAuth browser flow + token store | Planned | `runtime/src/oauth.rs` |
| Dynamic tool injection | Planned | `runtime/src/mcp_client.rs` |
| Dynamic command registration | Planned | `runtime/src/mcp_client.rs` |
| `list_mcp_resources` tool | Planned | `tools/src/list_mcp_resources.rs` |
| `read_mcp_resource` tool | Planned | `tools/src/read_mcp_resource.rs` |
| Reconnect + backoff | Planned | `runtime/src/mcp_client.rs` |
| `/mcp` slash commands | Planned | `mammoth-cli/src/commands/mcp.rs` |
