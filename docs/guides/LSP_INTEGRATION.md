# LSP Integration

This guide covers the `lsp` crate in Mammoth: what it does, how it is architected, how to configure it, and how to integrate it with the AI prompt pipeline and TUI. An engineer with zero prior codebase context should be able to read this document and implement or extend LSP support end-to-end.

---

## 1. Overview

The `lsp` crate gives Mammoth structured, real-time intelligence from running language servers (rust-analyzer, pyright, typescript-language-server, etc.). It exposes three capabilities to the rest of Mammoth:

| Capability | Description |
|---|---|
| **Diagnostics** | Collects errors and warnings published by the server on document open/change/save |
| **Navigation** | Resolves go-to-definition and find-references for any cursor position |
| **Context enrichment** | Packages diagnostics + navigation results into a formatted string that is injected into the AI system prompt |

Mammoth uses LSP context in three places (current + planned):

- **AI prompt injection** — `LspContextEnrichment::render_prompt_section()` is appended to the system prompt so the planner knows about active errors and the symbol at the cursor.
- **TUI diagnostics display** — the diagnostics panel and status bar show counts and messages from `WorkspaceDiagnostics` (planned).
- **Context sidebar** — go-to-definition and reference lists appear beside the active file (planned).

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Mammoth TUI / AI Planner              │
└──────────────────────────┬───────────────────────────────────┘
                           │  LspManager (public API)
                           │
              ┌────────────▼────────────┐
              │        LspManager       │
              │  server_configs (map)   │
              │  extension_map (map)    │
              │  clients (Mutex<map>)   │
              └──────┬──────────┬───────┘
           lazy      │          │  lazy
        connect      │          │  connect
                     │          │
         ┌───────────▼──┐  ┌────▼──────────┐
         │  LspClient   │  │  LspClient    │
         │ rust-analyzer│  │    pyright    │
         └──────┬───────┘  └──────┬────────┘
     stdin/     │                 │  stdin/
     stdout     │                 │  stdout
          ┌─────▼──────┐   ┌──────▼──────┐
          │rust-analyzer│  │   pyright   │
          │  (process)  │  │  (process)  │
          └─────────────┘  └─────────────┘
```

Each `LspClient` manages exactly one child process. Clients are created lazily: the first time `LspManager` receives a request for a file extension, it spawns the corresponding server and runs the LSP initialize handshake. After that the client is reused for all subsequent requests to the same server.

Communication follows the standard LSP JSON-RPC framing over stdin/stdout. All I/O is async (Tokio). A background reader task handles incoming messages: it dispatches responses to waiting `oneshot` channels and stores `textDocument/publishDiagnostics` notifications in a shared `BTreeMap`.

---

## 3. Crate Location and Public Exports

**Crate path:** `apps/mammoth/crates/lsp/`

**`Cargo.toml` dependencies:**

```toml
[dependencies]
lsp-types.workspace = true
serde = { version = "1", features = ["derive"] }
serde_json.workspace = true
tokio = { version = "1", features = ["io-util", "macros", "process", "rt", "rt-multi-thread", "sync", "time"] }
url = "2"
```

**Public API (re-exported from `lib.rs`):**

```rust
pub use error::LspError;
pub use manager::LspManager;
pub use types::{
    FileDiagnostics,
    LspContextEnrichment,
    LspServerConfig,
    SymbolLocation,
    WorkspaceDiagnostics,
};
```

Everything else (`client`, internal helpers) is `pub(crate)` or private.

---

## 4. Public API Reference

### 4.1 `LspServerConfig`

Configures a single language server. One config per server binary.

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LspServerConfig {
    /// Logical name — used as the key in the client map and in error messages.
    pub name: String,

    /// Path to the server binary (e.g. "rust-analyzer", "/usr/bin/pyright-langserver").
    pub command: String,

    /// Command-line arguments passed to the server binary.
    pub args: Vec<String>,

    /// Extra environment variables merged with the current environment.
    pub env: BTreeMap<String, String>,

    /// Absolute path to the workspace root. Sent as `rootUri` in the initialize request.
    pub workspace_root: PathBuf,

    /// Sent verbatim as `initializationOptions` in the initialize request.
    /// Pass `None` to omit (most servers are fine without it).
    pub initialization_options: Option<Value>,

    /// Maps file extensions to LSP language identifiers.
    /// Keys MUST include the leading dot: ".rs", ".py", ".ts".
    /// Values are the language ID string the server expects: "rust", "python", "typescript".
    pub extension_to_language: BTreeMap<String, String>,
}
```

**Method:**

```rust
impl LspServerConfig {
    /// Returns the language ID for `path` by matching its extension
    /// against `extension_to_language`. Returns `None` if the extension
    /// is not registered. Extension matching is case-insensitive and the
    /// leading dot is normalized automatically.
    pub fn language_id_for(&self, path: &Path) -> Option<&str>
}
```

### 4.2 `FileDiagnostics`

A snapshot of all diagnostics for one file.

```rust
#[derive(Debug, Clone, PartialEq)]
pub struct FileDiagnostics {
    /// Absolute filesystem path.
    pub path: PathBuf,

    /// `file://` URI corresponding to `path`.
    pub uri: String,

    /// Diagnostics from `lsp_types::Diagnostic`. Non-empty — files with zero
    /// diagnostics are not included in `WorkspaceDiagnostics`.
    pub diagnostics: Vec<Diagnostic>,
}
```

### 4.3 `WorkspaceDiagnostics`

Aggregated diagnostics for all files across all active LSP clients.

```rust
#[derive(Debug, Clone, Default, PartialEq)]
pub struct WorkspaceDiagnostics {
    /// One entry per file with at least one diagnostic. Sorted by path.
    pub files: Vec<FileDiagnostics>,
}

impl WorkspaceDiagnostics {
    /// `true` when no file has any diagnostics.
    pub fn is_empty(&self) -> bool

    /// Total number of individual diagnostics across all files.
    pub fn total_diagnostics(&self) -> usize
}
```

### 4.4 `SymbolLocation`

A resolved location returned by go-to-definition or find-references.

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SymbolLocation {
    /// Absolute filesystem path to the file containing the symbol.
    pub path: PathBuf,

    /// The range of the symbol in the file (0-indexed, from `lsp_types::Range`).
    pub range: Range,
}

impl SymbolLocation {
    /// Line number, 1-indexed (adds 1 to `range.start.line`).
    pub fn start_line(&self) -> u32

    /// Column number, 1-indexed (adds 1 to `range.start.character`).
    pub fn start_character(&self) -> u32
}

impl Display for SymbolLocation {
    // Formats as "path:line:character", e.g. "/workspace/src/main.rs:42:7"
}
```

### 4.5 `LspContextEnrichment`

The fully assembled context object for a single cursor position. Returned by `LspManager::context_enrichment()`.

```rust
#[derive(Debug, Clone, Default, PartialEq)]
pub struct LspContextEnrichment {
    /// The file the cursor is in.
    pub file_path: PathBuf,

    /// Current workspace diagnostics (all files, all servers).
    pub diagnostics: WorkspaceDiagnostics,

    /// Go-to-definition results for the cursor position.
    pub definitions: Vec<SymbolLocation>,

    /// Find-references results for the cursor position.
    pub references: Vec<SymbolLocation>,
}

impl LspContextEnrichment {
    /// `true` when diagnostics, definitions, and references are all empty.
    pub fn is_empty(&self) -> bool

    /// Renders a human-readable section for injection into an AI system prompt.
    /// See Section 11 for the exact output format and render limits.
    pub fn render_prompt_section(&self) -> String
}
```

### 4.6 `LspManager`

The main entry point. Holds all configuration and owns the lazy client pool.

```rust
pub struct LspManager { /* private fields */ }

impl LspManager {
    /// Constructs the manager from a list of server configs.
    ///
    /// Fails with `LspError::DuplicateExtension` if two configs claim the same
    /// file extension. All other validation is deferred to connect time.
    pub fn new(server_configs: Vec<LspServerConfig>) -> Result<Self, LspError>

    /// Returns `true` if `path`'s extension is registered with any server config.
    /// Does NOT connect to the server — safe to call without async.
    pub fn supports_path(&self, path: &Path) -> bool

    /// Notifies the server that a document has been opened with the given text.
    /// Triggers `textDocument/didOpen`. The server will begin publishing diagnostics.
    /// Version is set to 1.
    pub async fn open_document(&self, path: &Path, text: &str) -> Result<(), LspError>

    /// Reads `path` from disk and calls `change_document` + `save_document`.
    /// Convenience method for syncing after an external edit.
    pub async fn sync_document_from_disk(&self, path: &Path) -> Result<(), LspError>

    /// Notifies the server of a document edit. Sends `textDocument/didChange`
    /// with a full-text replacement. Increments the version counter.
    /// If the document is not yet open, opens it first (version 1).
    pub async fn change_document(&self, path: &Path, text: &str) -> Result<(), LspError>

    /// Notifies the server that the document has been saved. Sends `textDocument/didSave`.
    /// No-op if the document is not open.
    pub async fn save_document(&self, path: &Path) -> Result<(), LspError>

    /// Notifies the server that the document has been closed. Sends `textDocument/didClose`.
    /// Removes the document from the open-document version tracker.
    /// No-op if the document is not open.
    pub async fn close_document(&self, path: &Path) -> Result<(), LspError>

    /// Resolves go-to-definition for `position` in `path`.
    /// Automatically opens the document if it is not already open.
    /// Deduplicates results by (path, start_line, start_char, end_line, end_char).
    /// Returns an empty Vec when the server returns no locations.
    pub async fn go_to_definition(
        &self,
        path: &Path,
        position: Position,
    ) -> Result<Vec<SymbolLocation>, LspError>

    /// Resolves find-references for `position` in `path`.
    /// `include_declaration` maps to the LSP `context.includeDeclaration` field.
    /// Automatically opens the document if not already open.
    /// Deduplicates results by (path, start_line, start_char, end_line, end_char).
    pub async fn find_references(
        &self,
        path: &Path,
        position: Position,
        include_declaration: bool,
    ) -> Result<Vec<SymbolLocation>, LspError>

    /// Returns a snapshot of all current diagnostics from all connected clients.
    /// Files with zero diagnostics are excluded. Results are sorted by path.
    /// This snapshot reflects the last `textDocument/publishDiagnostics` notification
    /// received; it does not send any LSP request.
    pub async fn collect_workspace_diagnostics(&self) -> Result<WorkspaceDiagnostics, LspError>

    /// Convenience method combining workspace diagnostics + go-to-definition +
    /// find-references into a single `LspContextEnrichment` for the given position.
    /// All three calls run sequentially (not concurrently).
    pub async fn context_enrichment(
        &self,
        path: &Path,
        position: Position,
    ) -> Result<LspContextEnrichment, LspError>

    /// Sends `shutdown` + `exit` to every connected client and waits for the
    /// child processes to terminate. Should be called before the program exits.
    pub async fn shutdown(&self) -> Result<(), LspError>
}
```

---

## 5. `LspError` Variants

| Variant | When it occurs | What to do |
|---|---|---|
| `Io(std::io::Error)` | File system errors (reading file, spawning process, pipe I/O) | Check path permissions; verify the server binary is installed |
| `Json(serde_json::Error)` | Malformed JSON from the server or during serialization | Usually a server bug; log and skip |
| `InvalidHeader(String)` | A line in the LSP header block is not `Key: Value` | Indicates a corrupt stream; reconnect |
| `MissingContentLength` | A message arrived with no `Content-Length` header | Server violated the LSP framing spec |
| `InvalidContentLength(String)` | `Content-Length` value cannot be parsed as `usize` | Server sent garbage; reconnect |
| `UnsupportedDocument(PathBuf)` | The file's extension has no registered server | Either configure a server or call `supports_path()` first |
| `UnknownServer(String)` | Internal inconsistency: extension map points to a name not in `server_configs` | Should not happen; indicates a bug in `LspManager::new` |
| `DuplicateExtension { extension, existing_server, new_server }` | Two configs register the same file extension | Fix your config so each extension maps to exactly one server |
| `PathToUrl(PathBuf)` | `url::Url::from_file_path` failed (e.g. relative path, non-UTF-8) | Always pass absolute paths to all `LspManager` methods |
| `Protocol(String)` | LSP response contained an error object, or a oneshot channel dropped unexpectedly | Log and surface to the user; the server may have crashed |

`LspError` implements `std::error::Error` and `Display`. `From<std::io::Error>` and `From<serde_json::Error>` are implemented for `?`-based propagation.

---

## 6. Configuration

### 6.1 Full `LspServerConfig` field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `String` | Yes | Arbitrary label. Used as the map key and in error messages. |
| `command` | `String` | Yes | Binary name (resolved via `PATH`) or absolute path. |
| `args` | `Vec<String>` | No | Additional CLI flags for the server. |
| `env` | `BTreeMap<String, String>` | No | Merged into the child's environment. |
| `workspace_root` | `PathBuf` | Yes | Must be an absolute path. Sent as `rootUri`. |
| `initialization_options` | `Option<Value>` | No | Server-specific JSON. Pass `None` unless the server requires it. |
| `extension_to_language` | `BTreeMap<String, String>` | Yes | Keys must include the leading dot. At least one entry required. |

### 6.2 Worked examples

**rust-analyzer:**

```rust
use std::collections::BTreeMap;
use std::path::PathBuf;
use lsp::LspServerConfig;

let rust_analyzer = LspServerConfig {
    name: "rust-analyzer".to_string(),
    command: "rust-analyzer".to_string(),
    args: vec![],
    env: BTreeMap::new(),
    workspace_root: PathBuf::from("/workspace/my-project"),
    initialization_options: None,
    extension_to_language: BTreeMap::from([
        (".rs".to_string(), "rust".to_string()),
    ]),
};
```

**pyright (Python):**

```rust
let pyright = LspServerConfig {
    name: "pyright".to_string(),
    command: "pyright-langserver".to_string(),
    args: vec!["--stdio".to_string()],
    env: BTreeMap::new(),
    workspace_root: PathBuf::from("/workspace/my-python-project"),
    initialization_options: None,
    extension_to_language: BTreeMap::from([
        (".py".to_string(), "python".to_string()),
        (".pyi".to_string(), "python".to_string()),
    ]),
};
```

**typescript-language-server:**

```rust
let tsserver = LspServerConfig {
    name: "typescript-language-server".to_string(),
    command: "typescript-language-server".to_string(),
    args: vec!["--stdio".to_string()],
    env: BTreeMap::new(),
    workspace_root: PathBuf::from("/workspace/my-ts-project"),
    initialization_options: None,
    extension_to_language: BTreeMap::from([
        (".ts".to_string(), "typescript".to_string()),
        (".tsx".to_string(), "typescriptreact".to_string()),
        (".js".to_string(), "javascript".to_string()),
        (".jsx".to_string(), "javascriptreact".to_string()),
    ]),
};
```

**Multi-server setup:**

```rust
let manager = LspManager::new(vec![rust_analyzer, pyright, tsserver])?;
// Each server handles its own extension set.
// DuplicateExtension is returned at construction time if any extension appears twice.
```

---

## 7. Document Lifecycle

Mammoth must notify the server of document state changes to receive accurate diagnostics and navigation results. The server's view of document content is managed via these four notifications.

```
open_document(path, text)          ← File opened in the editor
      │
      ├─ change_document(path, text) ← User edits content (send full text)
      │
      ├─ save_document(path)         ← User saves to disk
      │
      └─ close_document(path)        ← File tab closed
```

**When to call each method:**

| Method | When to call |
|---|---|
| `open_document` | When Mammoth opens a file for editing. Pass the current on-disk contents. |
| `change_document` | On every keystroke or after each edit batch. Always pass the full document text — the server uses whole-document sync. |
| `save_document` | After the file is written to disk. Triggers server-side save hooks (e.g. `cargo check`). |
| `close_document` | When the file tab is closed or the buffer is discarded. |
| `sync_document_from_disk` | When an external process changes the file and you want the server to reflect the new state without having the text in memory. Reads from disk, sends `didChange` + `didSave`. |

**Idempotency notes:**
- `save_document` and `close_document` are no-ops if the document is not open — safe to call unconditionally.
- `change_document` opens the document first (version 1) if it has not been opened yet, so a `change_document` call without a preceding `open_document` is safe.

### Version tracking

`LspClient` maintains an `open_documents: Mutex<BTreeMap<PathBuf, i32>>` that tracks the current version number for each open file. `open_document` sets version 1. Each `change_document` call increments the version. The version number is sent in every `textDocument/didChange` notification per the LSP spec.

---

## 8. Lazy Client Connection

No server process is spawned at `LspManager::new` time. Processes are started on demand via `client_for_path()`, which is called by every `async` method that operates on a file.

### How `client_for_path` works

1. Normalize the file extension (lowercase, ensure leading dot).
2. Look up the server name in `extension_map`. If missing → `LspError::UnsupportedDocument`.
3. Lock `clients` map. If a client for that server name already exists → return the `Arc<LspClient>`.
4. Otherwise: look up the `LspServerConfig` by server name, call `LspClient::connect(config).await`, insert into the map, return the `Arc`.

This means:
- **First call** to any method on a new server extension spawns the process and runs the initialize handshake. This is the only point where the process starts.
- **Subsequent calls** to the same server reuse the existing client without any lock contention beyond acquiring the clients map briefly.
- **Multiple extensions for one server** (e.g. `.ts` and `.tsx` both pointing to `typescript-language-server`) share the same `LspClient` instance.

---

## 9. LSP Initialize Handshake

When `LspClient::connect()` is called:

1. Spawn the child process with stdin/stdout/stderr piped, `current_dir` set to `workspace_root`, and the configured `env`.
2. Start `spawn_reader` background task on stdout.
3. Start `spawn_stderr_drain` background task on stderr (discards all output silently).
4. Call `initialize()` — sends an `initialize` request and waits for the response.
5. Send `initialized` notification.

The exact `initialize` request body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "processId": 12345,
    "rootUri": "file:///path/to/workspace",
    "rootPath": "/path/to/workspace",
    "workspaceFolders": [
      { "uri": "file:///path/to/workspace", "name": "rust-analyzer" }
    ],
    "initializationOptions": null,
    "capabilities": {
      "textDocument": {
        "publishDiagnostics": { "relatedInformation": true },
        "definition":         { "linkSupport": true },
        "references":         {}
      },
      "workspace": {
        "configuration":    false,
        "workspaceFolders": true
      },
      "general": {
        "positionEncodings": ["utf-16"]
      }
    }
  }
}
```

Notes:
- `processId` is the actual PID of the Mammoth process (`std::process::id()`).
- `rootUri` and `rootPath` both contain the workspace root (rootPath is for legacy servers).
- `workspaceFolders` has a single entry using the config's `name` as the folder name.
- `initializationOptions` is the value from `LspServerConfig::initialization_options`, or `null` if `None`.
- Declared capabilities are minimal: diagnostics with related info, definition with link support, references, and utf-16 encoding. Servers that advertise more capabilities (hover, completion, etc.) will not be exercised by the current client implementation.

The `initialized` notification that follows:

```json
{
  "jsonrpc": "2.0",
  "method": "initialized",
  "params": {}
}
```

---

## 10. Wire Protocol (JSON-RPC over stdin/stdout)

LSP uses HTTP-style header framing over the process's stdin/stdout pipes.

### Outgoing message format (client → server)

```
Content-Length: <N>\r\n
\r\n
<N bytes of UTF-8 JSON>
```

`send_message` in `LspClient` serializes the JSON value, computes the byte length, writes the header line, the blank line, then the body, then flushes.

### Incoming message format (server → client)

The background `spawn_reader` task reads from a `BufReader<ChildStdout>`:

1. Read header lines until `\r\n` (blank line). Parse `Content-Length`.
2. Read exactly `content_length` bytes.
3. Deserialize as `serde_json::Value`.
4. Dispatch:
   - If the message has an `id` field → it is a response. Look up the `id` in `pending_requests`, send the result over the `oneshot` channel.
   - If the message has `method == "textDocument/publishDiagnostics"` → deserialize as `PublishDiagnosticsParams`, update the `diagnostics` map (insert on non-empty, remove on empty).
   - Any other notification without an `id` is silently ignored.

### Request correlation

Each request is assigned a monotonically increasing `i64` ID via `AtomicI64`. Before sending, a `oneshot::Sender` is stored in `pending_requests` keyed by that ID. The reader task removes the sender when the matching response arrives and sends the result through it. If the reader task exits with an error, it drains all pending requests with the error.

---

## 11. Diagnostics

### How diagnostics are received

The server sends `textDocument/publishDiagnostics` notifications asynchronously — typically after `didOpen`, `didChange`, or `didSave`. The background reader task handles these without any request-response correlation:

```
server → "textDocument/publishDiagnostics" { uri, diagnostics: [...] }
reader task → diagnostics_map.insert(uri, diagnostics)
                             OR
                             diagnostics_map.remove(uri)   // if diagnostics is empty
```

The `diagnostics` field is `Arc<Mutex<BTreeMap<String, Vec<Diagnostic>>>>`, keyed by URI string. Mammoth does not need to poll — it just calls `collect_workspace_diagnostics()` whenever it needs a fresh snapshot.

### `collect_workspace_diagnostics()`

1. Lock the `clients` map and clone all `Arc<LspClient>` handles.
2. For each client, call `diagnostics_snapshot()` to get its `BTreeMap<String, Vec<Diagnostic>>`.
3. For each URI in each snapshot, parse the URI to an absolute path.
4. Skip URIs that cannot be converted to a filesystem path (e.g. non-file URIs).
5. Skip files with zero diagnostics.
6. Accumulate into `Vec<FileDiagnostics>`, sorted by path.
7. Return `WorkspaceDiagnostics { files }`.

Diagnostics from all clients are merged into a single flat list, so Mammoth does not need to know which server produced which diagnostic.

### Timing consideration

Diagnostics arrive asynchronously after document open/change events. There is no synchronous "re-check" call. If you need to wait for diagnostics before proceeding (e.g. in a test), poll `collect_workspace_diagnostics()` until `total_diagnostics() > 0` or a timeout elapses:

```rust
tokio::time::timeout(Duration::from_secs(2), async {
    loop {
        let diags = manager.collect_workspace_diagnostics().await?;
        if diags.total_diagnostics() > 0 {
            return Ok::<_, LspError>(diags);
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }
})
.await
.map_err(|_| /* timeout */)?
```

---

## 12. Navigation

### `go_to_definition`

```rust
pub async fn go_to_definition(
    &self,
    path: &Path,
    position: Position,   // lsp_types::Position { line: u32, character: u32 }  (0-indexed)
) -> Result<Vec<SymbolLocation>, LspError>
```

Sends `textDocument/definition`. The server may respond with:
- A scalar `Location` — wrapped in a single-element Vec.
- An array of `Location` — returned as-is.
- An array of `LocationLink` — the `target_selection_range` is used as the symbol range.
- `null` — returns an empty Vec.

After converting to `Vec<SymbolLocation>`, duplicate entries (same path + start/end position) are removed via `BTreeSet`.

### `find_references`

```rust
pub async fn find_references(
    &self,
    path: &Path,
    position: Position,
    include_declaration: bool,
) -> Result<Vec<SymbolLocation>, LspError>
```

Sends `textDocument/references` with `context.includeDeclaration` set to the `include_declaration` argument. Deduplication is applied using the same `BTreeSet` strategy as go-to-definition.

### Deduplication detail

```rust
fn dedupe_locations(locations: &mut Vec<SymbolLocation>) {
    let mut seen = BTreeSet::new();
    locations.retain(|location| {
        seen.insert((
            location.path.clone(),
            location.range.start.line,
            location.range.start.character,
            location.range.end.line,
            location.range.end.character,
        ))
    });
}
```

Insertion order is preserved for unique entries.

### Coordinate system

`Position` and `Range` use 0-indexed lines and characters as required by the LSP spec. `SymbolLocation::start_line()` and `start_character()` add 1 to convert to 1-indexed values for display.

---

## 13. Context Enrichment

`context_enrichment()` is the primary integration point for AI prompt injection. It calls three methods sequentially and packages the results:

```rust
pub async fn context_enrichment(
    &self,
    path: &Path,
    position: Position,
) -> Result<LspContextEnrichment, LspError> {
    Ok(LspContextEnrichment {
        file_path: path.to_path_buf(),
        diagnostics: self.collect_workspace_diagnostics().await?,
        definitions: self.go_to_definition(path, position).await?,
        references: self.find_references(path, position, true).await?,
    })
}
```

Note that `include_declaration: true` is hardcoded — the declaration is always included in references for context enrichment purposes.

### `render_prompt_section()`

Converts an `LspContextEnrichment` to a prompt-ready string. Render limits:

| Section | Maximum items rendered |
|---|---|
| Diagnostics | 12 (across all files) |
| Definitions | 12 |
| References | 12 |

When a section exceeds its limit, the message `" - Additional [section] omitted for brevity."` is appended.

### Exact output format

```
# LSP context
 - Focus file: /path/to/file.rs
 - Workspace diagnostics: 3 across 2 file(s)

Diagnostics:
 - /path/to/file.rs:1:1 [error] mock error
 - /path/to/other.rs:5:3 [warning] unused variable

Definitions:
 - /path/to/file.rs:1:1

References:
 - /path/to/file.rs:1:1
 - /path/to/file.rs:2:5
```

Format rules:
- Each line in `Diagnostics` is ` - {path}:{line}:{char} [{severity}] {message}` where line/char are 1-indexed and newlines in the message are replaced with spaces.
- Severity labels: `"error"`, `"warning"`, `"info"`, `"hint"`, `"unknown"`.
- `Definitions` and `References` lines use `SymbolLocation`'s `Display` impl: `{path}:{line}:{char}`.
- If diagnostics is empty, the `Diagnostics:` section is omitted entirely.
- If definitions is empty, the `Definitions:` section is omitted entirely.
- If references is empty, the `References:` section is omitted entirely.
- The header line (`# LSP context`) and the summary line are always present.
- Lines are joined with `\n` (no trailing newline).

---

## 14. Integration with the AI Prompt

`LspContextEnrichment::render_prompt_section()` produces a self-contained Markdown section that is appended to the system prompt passed to the AI planner. The typical integration point in Mammoth is in the prompt-building layer, just before invoking the AI provider:

```rust
use lsp::{LspManager, LspContextEnrichment};
use lsp_types::Position;

async fn build_system_prompt(
    base_prompt: &str,
    lsp: &LspManager,
    active_file: &Path,
    cursor_position: Position,
) -> String {
    // Attempt enrichment; if LSP is unavailable for this file, skip gracefully.
    let lsp_section = if lsp.supports_path(active_file) {
        match lsp.context_enrichment(active_file, cursor_position).await {
            Ok(enrichment) if !enrichment.is_empty() => {
                format!("\n\n{}", enrichment.render_prompt_section())
            }
            Ok(_) => String::new(),  // No diagnostics or navigation results.
            Err(err) => {
                tracing::warn!("LSP context enrichment failed: {err}");
                String::new()
            }
        }
    } else {
        String::new()
    };

    format!("{base_prompt}{lsp_section}")
}
```

The section is appended after the base system prompt. The AI planner sees:
- The file the user is currently editing.
- How many errors/warnings exist across the workspace and their locations.
- Where the symbol under the cursor is defined.
- All known references to that symbol.

This gives the planner enough context to suggest fixes targeted at real errors, propose refactors that account for all reference sites, and understand the symbol's origin.

---

## 15. Integration with the TUI

> **Status:** The LSP data layer is complete. TUI integration is planned but not yet wired.

Planned integration points:

| TUI location | Data source | Description |
|---|---|---|
| Status bar | `WorkspaceDiagnostics::total_diagnostics()` | Show error/warning count (e.g. `✗ 3 errors  ⚠ 1 warning`) |
| Diagnostics panel | `WorkspaceDiagnostics::files` | List errors and warnings per file, navigate to line |
| Context sidebar | `LspContextEnrichment` | Show definitions and references for the symbol at cursor |
| Inline annotations | `FileDiagnostics::diagnostics` | Render underlines or gutter markers at error positions |

The `collect_workspace_diagnostics()` call is cheap (snapshot of an in-memory map) and can be called on every render tick.

---

## 16. Adding a New Language Server

Follow these steps to add support for a new language (e.g. Go with `gopls`):

**Step 1: Install the server binary**

```sh
go install golang.org/x/tools/gopls@latest
```

**Step 2: Create the `LspServerConfig`**

```rust
use std::collections::BTreeMap;
use std::path::PathBuf;
use lsp::LspServerConfig;

let gopls = LspServerConfig {
    name: "gopls".to_string(),
    command: "gopls".to_string(),
    args: vec!["serve".to_string()],
    env: BTreeMap::new(),
    workspace_root: PathBuf::from("/workspace/my-go-project"),
    initialization_options: None,
    extension_to_language: BTreeMap::from([
        (".go".to_string(), "go".to_string()),
    ]),
};
```

**Step 3: Register it with `LspManager`**

```rust
let manager = LspManager::new(vec![
    rust_analyzer,  // existing
    gopls,          // new
])?;
```

**Step 4: Verify extension uniqueness**

`LspManager::new` returns `LspError::DuplicateExtension` at construction time if `.go` is already claimed by another server. Check your other configs.

**Step 5: Test with the mock server (optional)**

For unit testing without the real binary, use the Python mock described in Section 17:

```rust
let gopls_mock = LspServerConfig {
    name: "gopls".to_string(),
    command: "python3".to_string(),
    args: vec![mock_script_path.to_string_lossy().to_string()],
    env: BTreeMap::new(),
    workspace_root: temp_workspace.clone(),
    initialization_options: None,
    extension_to_language: BTreeMap::from([
        (".go".to_string(), "go".to_string()),
    ]),
};
```

**Step 6: Confirm `supports_path` and document lifecycle work**

```rust
assert!(manager.supports_path(Path::new("/workspace/main.go")));
manager.open_document(Path::new("/workspace/main.go"), &source_text).await?;
```

---

## 17. Testing

### Test infrastructure

The test suite lives in `apps/mammoth/crates/lsp/src/lib.rs` (the `#[cfg(test)] mod tests` block). It uses a Python mock LSP server rather than a real language server, so tests run on any machine with Python 3 installed and without any language toolchain.

### Python mock server (`mock_lsp_server.py`)

The mock server is written inline as a string and written to a temp file at test setup time. It implements the following LSP methods:

| Method | Mock behaviour |
|---|---|
| `initialize` | Responds with `definitionProvider: true`, `referencesProvider: true`, `textDocumentSync: 1` |
| `initialized` | Ignored (no response required) |
| `textDocument/didOpen` | Immediately pushes one `publishDiagnostics` notification with a single error at line 0, character 0–3 |
| `textDocument/didChange` | Ignored |
| `textDocument/didSave` | Ignored |
| `textDocument/definition` | Returns one location at line 0:0–0:3 in the same file |
| `textDocument/references` | Returns two locations: line 0:0–0:3 and line 1:4–1:7 in the same file |
| `shutdown` | Responds with `null` |
| `exit` | Terminates the process |

### Integration test 1: `collects_diagnostics_and_symbol_navigation_from_mock_server`

1. Creates a temp workspace directory with a `src/main.rs` file.
2. Writes the mock server script to the workspace root.
3. Builds an `LspManager` pointing to the mock server, registered for `.rs`.
4. Opens `src/main.rs`.
5. Polls diagnostics until one diagnostic arrives (2-second timeout).
6. Calls `collect_workspace_diagnostics()`, `go_to_definition()`, and `find_references()`.
7. Asserts:
   - One file in diagnostics, one total diagnostic, severity ERROR.
   - One definition at line 1 (1-indexed).
   - Two references.
8. Calls `shutdown()` and removes the temp directory.

### Integration test 2: `renders_runtime_context_enrichment_for_prompt_usage`

1. Same setup as test 1 with `src/lib.rs`.
2. Calls `context_enrichment()` and then `render_prompt_section()`.
3. Asserts the rendered string contains:
   - `"# LSP context"`
   - `"Workspace diagnostics: 1 across 1 file(s)"`
   - `"Definitions:"`
   - `"References:"`
   - `"mock error"`

### Running the tests

```sh
# From the workspace root:
cargo test -p lsp

# From the crate directory:
cd apps/mammoth/crates/lsp
cargo test

# Verbose output:
cargo test -p lsp -- --nocapture
```

Tests are annotated with `#[tokio::test(flavor = "current_thread")]`. The `python3_path()` helper checks `"python3"` and `"/usr/bin/python3"` — if neither is found, the test returns early (skips). Tests create temporary directories under `std::env::temp_dir()` and clean up on completion.

---

## 18. Error Handling Patterns

### Graceful degradation for unsupported files

Always guard with `supports_path()` before calling any async method to avoid returning `UnsupportedDocument` errors during normal operation:

```rust
if manager.supports_path(&path) {
    manager.open_document(&path, &text).await?;
}
```

### Treating LSP as non-fatal

For AI prompt enrichment, LSP failures should never block the request. Treat all LSP errors as non-fatal and fall back to an empty prompt section:

```rust
let lsp_section = match manager.context_enrichment(&path, position).await {
    Ok(enrichment) => enrichment.render_prompt_section(),
    Err(err) => {
        tracing::warn!("LSP enrichment skipped: {err}");
        String::new()
    }
};
```

### Handling `DuplicateExtension` at startup

This error only occurs at `LspManager::new` time. Validate your configs in your server startup code and surface it to the operator immediately — do not silently swallow it:

```rust
let manager = LspManager::new(configs).unwrap_or_else(|err| {
    eprintln!("LSP configuration error: {err}");
    std::process::exit(1);
});
```

### Shutdown on process exit

Always call `manager.shutdown().await` before the Mammoth process exits to ensure the server processes receive a clean `shutdown` + `exit` sequence:

```rust
// In the main loop teardown:
if let Err(err) = lsp_manager.shutdown().await {
    tracing::error!("LSP shutdown error: {err}");
}
```

---

## 19. Implementation Status

| Feature | Status | Notes |
|---|---|---|
| LSP JSON-RPC framing (read/write) | ✅ Built | `Content-Length` header framing over pipes |
| Process lifecycle (spawn/kill) | ✅ Built | Tokio async process, clean shutdown |
| Initialize handshake | ✅ Built | Capabilities declared as documented |
| `textDocument/didOpen` | ✅ Built | Sends language ID and initial text |
| `textDocument/didChange` | ✅ Built | Full-text sync, version tracking |
| `textDocument/didSave` | ✅ Built | |
| `textDocument/didClose` | ✅ Built | |
| `textDocument/publishDiagnostics` | ✅ Built | Background task, in-memory map |
| `textDocument/definition` | ✅ Built | Scalar, array, and LocationLink responses |
| `textDocument/references` | ✅ Built | |
| Lazy client connection | ✅ Built | Per-server, on first file access |
| Deduplication of nav results | ✅ Built | BTreeSet keyed on full range |
| Context enrichment + prompt rendering | ✅ Built | Render limits: 12 diagnostics, 12 locations |
| Multi-server support | ✅ Built | One client per server name |
| TUI diagnostics panel | ⬜ Planned | Wire `WorkspaceDiagnostics` to TUI render loop |
| TUI inline error annotations | ⬜ Planned | Gutter markers / underlines |
| TUI context sidebar | ⬜ Planned | Definitions + references panel |
| Hover (`textDocument/hover`) | ⬜ Planned | Not declared in capabilities yet |
| Completion (`textDocument/completion`) | ⬜ Planned | Not declared in capabilities yet |
| Workspace symbols | ⬜ Planned | Not declared in capabilities yet |
| Config file auto-discovery | ⬜ Planned | Currently requires explicit `LspServerConfig` |

---

## 20. File Locations

| Path | Contents |
|---|---|
| `apps/mammoth/crates/lsp/Cargo.toml` | Crate manifest and dependencies |
| `apps/mammoth/crates/lsp/src/lib.rs` | Public re-exports and integration tests |
| `apps/mammoth/crates/lsp/src/types.rs` | `LspServerConfig`, `FileDiagnostics`, `WorkspaceDiagnostics`, `SymbolLocation`, `LspContextEnrichment` |
| `apps/mammoth/crates/lsp/src/error.rs` | `LspError` enum |
| `apps/mammoth/crates/lsp/src/manager.rs` | `LspManager` — public API, lazy client pool, deduplication |
| `apps/mammoth/crates/lsp/src/client.rs` | `LspClient` — process management, JSON-RPC I/O, background reader |
