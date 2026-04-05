# Memory and Sessions — Mammoth Runtime Guide

**Status:** Implemented (core) / Planned (extensions)
**Source:** `apps/mammoth/crates/runtime/src/session.rs`
**Also see:** `apps/mammoth/crates/runtime/src/compact.rs`, `apps/mammoth/crates/runtime/src/conversation.rs`

---

## Overview

Mammoth sessions are **resumable conversation contexts** stored as JSON on disk. Every message
exchange — user input, assistant output, tool calls, and tool results — is recorded in the session
file. Sessions survive process restarts, can be resumed by ID, and are the unit of audit lineage.

Sessions are also the persistence layer for the multi-agent swarm: each teammate in a team has its
own session transcript at `~/.mammoth/sessions/{team_name}/{agent_id}.jsonl`.

---

## Core Data Model

All types are in `apps/mammoth/crates/runtime/src/session.rs`.

### `Session`

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Session {
    /// Schema version. Currently always 1.
    pub version: u32,
    /// Ordered list of conversation turns.
    pub messages: Vec<ConversationMessage>,
}
```

**Disk format:** JSON object serialized with `JsonValue` (the project's zero-dependency JSON type,
not `serde_json`).

```json
{
  "version": 1,
  "messages": [ ... ]
}
```

**Key methods:**

| Method | Signature | Purpose |
|--------|-----------|---------|
| `Session::new()` | `() -> Self` | Empty session with version=1 |
| `save_to_path` | `(&self, path: impl AsRef<Path>) -> Result<(), SessionError>` | Write JSON to file |
| `load_from_path` | `(path: impl AsRef<Path>) -> Result<Self, SessionError>` | Read + parse from file |
| `to_json` | `(&self) -> JsonValue` | Serialize to `JsonValue` (for embedding in larger objects) |
| `from_json` | `(value: &JsonValue) -> Result<Self, SessionError>` | Deserialize |

---

### `MessageRole`

```rust
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MessageRole {
    System,
    User,
    Assistant,
    Tool,
}
```

- `System` — injected at conversation start (system prompt, tool definitions)
- `User` — input from the human or from a sub-agent's parent
- `Assistant` — model output (may contain text + tool use blocks)
- `Tool` — tool result (one message per tool call that completed)

---

### `ConversationMessage`

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ConversationMessage {
    pub role: MessageRole,
    pub blocks: Vec<ContentBlock>,
    pub usage: Option<TokenUsage>,
}
```

**Constructors:**

```rust
// User text message
ConversationMessage::user_text("Please refactor the parser.")

// Assistant response (with usage tracking)
ConversationMessage::assistant_with_usage(
    vec![
        ContentBlock::Text { text: "I'll start by reading the file.".into() },
        ContentBlock::ToolUse { id: "tu_001".into(), name: "read_file".into(), input: r#"{"path":"src/parser.rs"}"# .into() },
    ],
    Some(usage),
)

// Tool result
ConversationMessage::tool_result("tu_001", "read_file", "<file contents>", false)
```

---

### `ContentBlock`

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentBlock {
    /// Plain text output from the assistant
    Text { text: String },

    /// The assistant requested a tool call
    ToolUse {
        id: String,        // Unique tool use ID (e.g. "toolu_abc123")
        name: String,      // Tool name (e.g. "bash", "read_file")
        input: String,     // JSON-encoded input (stored as string, not nested object)
    },

    /// Result of a completed tool call
    ToolResult {
        tool_use_id: String,  // Must match a ToolUse.id in a prior message
        tool_name: String,    // Copied from the ToolUse for audit clarity
        output: String,       // Tool output (may be JSON, text, or error message)
        is_error: bool,       // True if the tool execution failed
    },
}
```

**Important:** `ToolUse.input` is stored as a **JSON string**, not as a nested object. This avoids
double-parsing and allows the session to round-trip arbitrary tool inputs without schema knowledge.

---

### `TokenUsage`

```rust
// apps/mammoth/crates/runtime/src/usage.rs
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct TokenUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cache_creation_input_tokens: u32,
    pub cache_read_input_tokens: u32,
}

impl TokenUsage {
    pub fn total_tokens(&self) -> u32 {
        self.input_tokens + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
    }
}
```

Usage is attached to assistant messages only. Tool messages do not carry usage because the provider
does not bill for tool result tokens in the same way.

---

### `SessionError`

```rust
pub enum SessionError {
    Io(std::io::Error),      // File read/write failure
    Json(JsonError),          // Parse failure
    Format(String),           // Schema mismatch (e.g. wrong version, missing field)
}
```

---

## Save and Load

### Default paths

| Context | Path |
|---------|------|
| Main session | `~/.mammoth/sessions/{session_id}.json` |
| Teammate transcript | `~/.mammoth/sessions/{team_name}/{agent_id}.json` |
| Worktree session | `~/.mammoth/worktrees/{slug}/session.json` |
| Compacted session | `~/.mammoth/sessions/{session_id}.compacted.json` |

Session IDs are generated as URL-safe random slugs: `sess_<8-char hex>`.

### Save

```rust
let session = Session { version: 1, messages: vec![ /* ... */ ] };
session.save_to_path("/home/user/.mammoth/sessions/sess_a1b2c3d4.json")?;
```

The write is atomic: data is written to a temp file in the same directory, then renamed. This
prevents partial writes leaving a corrupt session file.

### Load

```rust
let session = Session::load_from_path("/home/user/.mammoth/sessions/sess_a1b2c3d4.json")?;
```

Fails with `SessionError::Format` if `version` is missing or unrecognized.

---

## Resume Flows

### Simple resume (`--resume <id>`)

```
mammoth --resume sess_a1b2c3d4
```

1. Locate `~/.mammoth/sessions/sess_a1b2c3d4.json`
2. Load and deserialize the `Session`
3. Inject into the conversation context as the initial message history
4. Continue the main loop from where it left off

The model never sees the session file directly — the messages are fed as conversation history in
the first API request.

### Auto-resume (most recent session)

```
mammoth --resume
```

Lists sessions sorted by modification time, selects the most recent.

### Plan recovery resume

If a session ended mid-plan (the session file contains a `ToolUse` for `enter_plan_mode` with no
matching `exit_plan_mode`), Mammoth recognizes the dangling plan and offers to resume it:

```
Session sess_a1b2c3d4 has an unfinished plan. Resume plan? [Y/n]
```

On confirmation, the session is loaded and the plan mode state is restored.

### Worktree-aware resume

If a session was running inside a git worktree (`enter_worktree` was called), the worktree path
is stored in the session's metadata. On resume:
1. Mammoth checks if the worktree still exists
2. If yes, resumes inside the worktree's working directory
3. If no, warns the user and resumes in the original project directory

### Cross-project sessions

Sessions are tied to the working directory at creation time. Resuming a session from a different
project directory emits a warning but proceeds. The session's internal paths remain relative to
the original project root.

---

## Session Browser (TUI)

Accessible via `Ctrl+R` in the TUI. Displays a scrollable list of recent sessions:

```
┌─ Sessions ──────────────────────────────────────────────────┐
│ 2026-04-05 14:23  sess_a1b2c3d4  "Refactor the parser"     │
│ 2026-04-05 11:07  sess_b2c3d4e5  "Add OAuth flow"          │
│ 2026-04-04 19:55  sess_c3d4e5f6  "Fix test flakiness"      │
│                                                              │
│ Press Enter to resume · Del to delete · Esc to close        │
└──────────────────────────────────────────────────────────────┘
```

Each entry shows:
- Timestamp (last modified)
- Session ID
- First user message (truncated to 50 chars)
- Token count badge if > 10k tokens

---

## Conversation Compaction

Long sessions grow indefinitely. Compaction condenses the conversation to a summary + recent turns
while preserving the audit lineage.

**Source:** `apps/mammoth/crates/runtime/src/compact.rs` (planned)

### Compaction strategy

1. Keep the system message
2. Summarize all messages before the last N turns into a single `User` message:
   ```
   [Conversation summary: The session was working on refactoring the parser module.
   Key decisions: extracted TokenIterator trait, moved error types to errors.rs.
   Files modified: src/parser.rs, src/errors.rs, src/lib.rs.]
   ```
3. Keep the last N=20 turns verbatim
4. Save both the original session (`*.json`) and the compacted form (`*.compacted.json`)
5. Use the compacted form for new API requests; preserve the original for audit/replay

### Compaction trigger

Compaction is triggered automatically when:
- Input token count exceeds 80% of the model's context window, OR
- The user runs `/compact`

### Manual compaction

```
/compact              → compact now with default settings
/compact keep=30      → keep last 30 turns verbatim
/compact --export     → save summary to a markdown file in the project
```

---

## Memory System (Planned — v0.4.0)

Beyond session persistence, Mammoth will support a structured **memory system** that extracts
and indexes key facts across sessions.

### Memory types

| Type | Storage | Scope | Lifetime |
|------|---------|-------|----------|
| Session memory | `session.json` | Single session | Session duration |
| Project memory | `.mammoth/memory.md` | Project | Project lifetime |
| User memory | `~/.mammoth/user-memory.md` | Global | User lifetime |
| Team memory | `~/.mammoth/teams/{name}/memory.md` | Team | Team lifetime |

### Auto-extraction (planned)

At session end or on `/save-memory`, Mammoth invokes a fast extraction pass over the session:
1. Find all `ContentBlock::Text` blocks from assistant messages
2. Extract facts matching patterns: "I've decided...", "Note:", "Key insight:", "TODO:", etc.
3. Deduplicate against existing memory file
4. Append new facts to the appropriate memory file

### Memory injection (planned)

At session start, relevant memory is injected into the system prompt:
```
[Memory from previous sessions]
- Parser uses recursive descent, not PEG. TokenIterator trait is in src/lexer.rs.
- Tests are in tests/integration/ and run with `cargo test --test integration`.
```

### Team memory sync (planned)

When a team is active, all teammates share read access to the team memory file. Only the leader
can write to it via `send_message` with a structured `memory_update` payload.

---

## Conversation Context Building

The `conversation.rs` module (planned) assembles the message array sent to the model API:

```rust
// apps/mammoth/crates/runtime/src/conversation.rs
pub struct ConversationContext {
    pub system_prompt: String,
    pub messages: Vec<ApiMessage>,        // Converted from ConversationMessage
    pub tool_definitions: Vec<ToolDef>,
    pub token_budget: Option<u32>,        // If set, context is truncated to fit
}

impl ConversationContext {
    pub fn from_session(
        session: &Session,
        config: &ConversationConfig,
        tools: &[ToolDef],
    ) -> Self { ... }
}
```

The conversion maps `ContentBlock` variants to the provider's API format:
- `ContentBlock::Text` → `{"type": "text", "text": "..."}`
- `ContentBlock::ToolUse` → `{"type": "tool_use", "id": "...", "name": "...", "input": {...}}`
  (note: input is parsed from the stored string back into an object for the API call)
- `ContentBlock::ToolResult` → placed in the next `user` message as tool_result blocks

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| `Session` struct + save/load | **Done** | `runtime/src/session.rs` |
| `ConversationMessage` + `ContentBlock` | **Done** | `runtime/src/session.rs` |
| `TokenUsage` | **Done** | `runtime/src/usage.rs` |
| Session ID generation | **Done** | `runtime/src/bootstrap.rs` |
| Session browser TUI widget | Planned | `mammoth-cli/src/tui/session_browser.rs` |
| Conversation compaction | Planned | `runtime/src/compact.rs` |
| Memory extraction | Planned | `runtime/src/memory.rs` |
| Memory injection | Planned | `runtime/src/prompt.rs` |
| Team memory sync | Planned | `runtime/src/swarm/memory.rs` |
| Worktree-aware resume | Planned | `runtime/src/bootstrap.rs` |
