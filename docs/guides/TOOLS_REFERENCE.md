# Mammoth Tools Reference

All built-in tools available to the agent during a Mammoth session. Tools are defined in
`apps/mammoth/crates/tools/src/lib.rs` (`mvp_tool_specs()`) and dispatched through
`execute_tool()`. Plugin tools registered at startup extend the same registry.

---

## Permission Tiers

Every tool carries a `required_permission` that is checked against the session's active
`PermissionPolicy` before execution.

| Tier | Constant | Meaning |
|------|----------|---------|
| `read-only` | `PermissionMode::ReadOnly` | Reads only; no filesystem writes, no side effects |
| `workspace-write` | `PermissionMode::WorkspaceWrite` | May write files inside the workspace |
| `danger-full-access` | `PermissionMode::DangerFullAccess` | Full OS access, network, subprocess |
| `prompt` | `PermissionMode::Prompt` | Always surface approval dialog regardless of mode |
| `allow` | `PermissionMode::Allow` | Unconditionally allowed (CLI `--allowAll`) |

Escalation rules (`apps/mammoth/crates/runtime/src/permissions.rs:89`):

- `workspace-write` session + `danger-full-access` tool → triggers approval prompt.
- `read-only` session + any write tool → hard deny, no prompt.
- `allow` session → all tools permitted, no prompts.

---

## Tool Aliases

The registry accepts these short-form aliases in `--allowedTools`:

| Alias | Canonical |
|-------|-----------|
| `read` | `read_file` |
| `write` | `write_file` |
| `edit` | `edit_file` |
| `glob` | `glob_search` |
| `grep` | `grep_search` |

---

## Built-in Tool Catalog

### `bash`

Execute a shell command in the current workspace.

**Permission:** `danger-full-access`

**Input schema:**

```json
{
  "command": "string (required) — shell command to run",
  "timeout": "integer (optional) — seconds before SIGTERM",
  "description": "string (optional) — human-readable label shown in TUI",
  "run_in_background": "boolean (optional) — detach from approval flow",
  "dangerouslyDisableSandbox": "boolean (optional) — bypass seccomp sandbox"
}
```

**Output schema:**

```json
{
  "stdout": "string",
  "stderr": "string",
  "exit_code": "integer",
  "duration_ms": "number"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/bash.rs` — `execute_bash()`

**Notes:**
- Default timeout: 120 seconds.
- Background commands write stdout/stderr to a temp file; the tool returns immediately with
  the temp file path.
- The Bash classifier (`apps/mammoth/crates/runtime/src/bash.rs`) scores risk and may
  auto-escalate the permission prompt.

---

### `read_file`

Read a text file from the workspace.

**Permission:** `read-only`

**Input schema:**

```json
{
  "path": "string (required) — absolute or workspace-relative path",
  "offset": "integer (optional, ≥ 0) — 1-indexed line number to start from",
  "limit": "integer (optional, ≥ 1) — maximum lines to return"
}
```

**Output schema:**

```json
{
  "content": "string — file text, prefixed with line numbers",
  "lines": "integer — total lines in file",
  "truncated": "boolean"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/file_ops.rs` — `read_file()`

**Notes:**
- Returns up to 2 000 lines by default.
- Line numbers are prepended as `<N>: <content>` to support precise `edit_file` targeting.

---

### `write_file`

Write a text file in the workspace (create or overwrite).

**Permission:** `workspace-write`

**Input schema:**

```json
{
  "path": "string (required)",
  "content": "string (required)"
}
```

**Output schema:**

```json
{
  "path": "string — resolved absolute path",
  "bytes_written": "integer"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/file_ops.rs` — `write_file()`

---

### `edit_file`

Replace an exact string in a workspace file.

**Permission:** `workspace-write`

**Input schema:**

```json
{
  "path": "string (required)",
  "old_string": "string (required) — exact text to find",
  "new_string": "string (required) — replacement text",
  "replace_all": "boolean (optional, default false) — replace every occurrence"
}
```

**Output schema:**

```json
{
  "path": "string",
  "replacements": "integer — number of substitutions made",
  "diff": "string — unified diff of the change"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/file_ops.rs` — `edit_file()`

**Notes:**
- Fails with an error if `old_string` is not found (exact match required).
- When `replace_all = false` and there are multiple matches, fails to prevent ambiguous edits.

---

### `glob_search`

Find files by glob pattern, sorted by modification time.

**Permission:** `read-only`

**Input schema:**

```json
{
  "pattern": "string (required) — glob e.g. \"**/*.rs\"",
  "path": "string (optional) — root directory, defaults to workspace root"
}
```

**Output schema:**

```json
{
  "files": ["string"],
  "count": "integer"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/file_ops.rs` — `glob_search()`

---

### `grep_search`

Search file contents with a regex pattern using `ripgrep`.

**Permission:** `read-only`

**Input schema:**

```json
{
  "pattern": "string (required) — regex",
  "path": "string (optional) — root directory",
  "glob": "string (optional) — file glob filter e.g. \"*.ts\"",
  "output_mode": "string (optional) — \"files_with_matches\" | \"count\" | \"matches\" (default)",
  "-B": "integer (optional) — lines before match",
  "-A": "integer (optional) — lines after match",
  "-C": "integer (optional) — context lines (shorthand for -B and -A)",
  "context": "integer (optional) — alias for -C",
  "-n": "boolean (optional) — include line numbers",
  "-i": "boolean (optional) — case-insensitive",
  "type": "string (optional) — language type filter e.g. \"rust\"",
  "head_limit": "integer (optional, ≥ 1) — max results to return",
  "offset": "integer (optional, ≥ 0) — skip first N results",
  "multiline": "boolean (optional) — enable multiline mode"
}
```

**Output schema:**

```json
{
  "matches": [
    {
      "file": "string",
      "line": "integer",
      "content": "string"
    }
  ],
  "truncated": "boolean",
  "total": "integer"
}
```

**Implementation:** `apps/mammoth/crates/runtime/src/file_ops.rs` — `grep_search()`

---

### `WebFetch`

Fetch a URL, convert it into readable text, and answer a prompt about it.

**Permission:** `read-only`

**Input schema:**

```json
{
  "url": "string (required, format: uri) — HTTP upgrades to HTTPS for non-localhost",
  "prompt": "string (required) — question about the fetched content"
}
```

**Output schema:**

```json
{
  "bytes": "integer",
  "code": "integer — HTTP status",
  "codeText": "string",
  "result": "string — answer to the prompt",
  "durationMs": "number",
  "url": "string — final URL after redirects"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_web_fetch()`

**Notes:**
- HTTP URLs (except localhost) are automatically upgraded to HTTPS.
- Follows up to 10 redirects.
- 20-second timeout.
- HTML is stripped to plain text before summarization.

---

### `WebSearch`

Search the web for current information and return cited results.

**Permission:** `read-only`

**Input schema:**

```json
{
  "query": "string (required, minLength: 2)",
  "allowed_domains": ["string"] ,
  "blocked_domains": ["string"]
}
```

**Output schema:**

```json
{
  "query": "string",
  "results": [
    {
      "title": "string",
      "url": "string"
    }
  ],
  "durationSeconds": "number"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_web_search()`

**Notes:**
- Uses DuckDuckGo HTML endpoint by default.
- Custom search backend: set `MAMMOTH_WEB_SEARCH_BASE_URL`.
- Returns at most 8 deduplicated results.

---

### `TodoWrite`

Update the structured task list for the current session.

**Permission:** `workspace-write`

**Input schema:**

```json
{
  "todos": [
    {
      "content": "string (required)",
      "activeForm": "string (required) — display label",
      "status": "\"pending\" | \"in_progress\" | \"completed\""
    }
  ]
}
```

**Output schema:**

```json
{
  "oldTodos": [...],
  "newTodos": [...],
  "verificationNudgeNeeded": "boolean | null"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_todo_write()`

**Notes:**
- Persisted to `.mammoth-todos.json` in the current workspace, or `$MAMMOTH_TODO_STORE`.
- If all todos are marked `completed`, the file is cleared.
- `verificationNudgeNeeded` is set when all 3+ todos complete but none mention "verif".
- Multiple `in_progress` items are allowed (parallel workflows).

---

### `Skill`

Load a local skill definition and its instructions.

**Permission:** `read-only`

**Input schema:**

```json
{
  "skill": "string (required) — skill name or path",
  "args": "string (optional)"
}
```

**Output schema:**

```json
{
  "skill": "string",
  "path": "string — resolved SKILL.md path",
  "args": "string | null",
  "description": "string | null",
  "prompt": "string — full SKILL.md content"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_skill()`

**Skill search order:**

1. `$CODEX_HOME/skills/<name>/SKILL.md`
2. `~/.agents/skills/<name>/SKILL.md`
3. `~/.config/opencode/skills/<name>/SKILL.md`
4. `~/.codex/skills/<name>/SKILL.md`

---

### `Agent`

Launch a specialized agent task and persist its handoff metadata.

**Permission:** `danger-full-access`

**Input schema:**

```json
{
  "description": "string (required)",
  "prompt": "string (required)",
  "subagent_type": "string (optional) — named agent type (e.g. \"researcher\", \"test-runner\")",
  "name": "string (optional) — slug for this agent instance",
  "model": "string (optional) — model override"
}
```

**Output schema:**

```json
{
  "agentId": "string",
  "name": "string",
  "description": "string",
  "subagentType": "string | null",
  "model": "string | null",
  "status": "\"running\" | \"completed\" | \"failed\"",
  "outputFile": "string — path to agent output .md",
  "manifestFile": "string — path to agent manifest .json",
  "createdAt": "string (ISO 8601)",
  "startedAt": "string | null",
  "completedAt": "string | null",
  "error": "string | null"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_agent()`

**Notes:**
- Default model: `claude-opus-4-6`.
- Default max iterations: 32.
- Agent store: `$MAMMOTH_AGENT_STORE` or `.mammoth-agents/` in workspace.
- Sub-agent system prompt and allowed tools are derived from `subagent_type`.
- Returns immediately; agent runs asynchronously; poll manifest file for completion.

---

### `ToolSearch`

Search for deferred or specialized tools by exact name or keywords.

**Permission:** `read-only`

**Input schema:**

```json
{
  "query": "string (required)",
  "max_results": "integer (optional, ≥ 1, default 10)"
}
```

**Output schema:**

```json
{
  "matches": ["string"],
  "query": "string",
  "normalized_query": "string",
  "total_deferred_tools": "integer",
  "pending_mcp_servers": ["string"] | null
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_tool_search()`

**Notes:**
- Searches the deferred/lazy tool registry (MCP tools not yet loaded, plugin tools).
- Returns tool names that match the query by prefix or keyword.
- Useful when the agent needs a tool that is not in the initial context window.

---

### `NotebookEdit`

Replace, insert, or delete a cell in a Jupyter notebook.

**Permission:** `workspace-write`

**Input schema:**

```json
{
  "notebook_path": "string (required) — path to .ipynb",
  "cell_id": "string (optional) — target cell ID",
  "new_source": "string (optional) — replacement source",
  "cell_type": "\"code\" | \"markdown\"",
  "edit_mode": "\"replace\" | \"insert\" | \"delete\""
}
```

**Output schema:**

```json
{
  "new_source": "string",
  "cell_id": "string | null",
  "cell_type": "string | null",
  "language": "string",
  "edit_mode": "string",
  "error": "string | null",
  "notebook_path": "string",
  "original_file": "string — original notebook JSON",
  "updated_file": "string — updated notebook JSON"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_notebook_edit()`

---

### `Sleep`

Wait for a specified duration without holding a shell process.

**Permission:** `read-only`

**Input schema:**

```json
{
  "duration_ms": "integer (required, ≥ 0)"
}
```

**Output schema:**

```json
{
  "duration_ms": "integer",
  "message": "string"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_sleep()`

**Notes:**
- Useful in polling loops (e.g., wait for a background agent to finish).
- Cap at a reasonable maximum (e.g., 60 000 ms) in production to prevent runaway loops.

---

### `SendUserMessage` (alias: `Brief`)

Send a message to the user — either a normal response or a proactive notification.

**Permission:** `read-only`

**Input schema:**

```json
{
  "message": "string (required)",
  "attachments": ["string"] ,
  "status": "\"normal\" | \"proactive\""
}
```

**Output schema:**

```json
{
  "message": "string",
  "attachments": [
    {
      "path": "string",
      "size": "integer",
      "isImage": "boolean"
    }
  ] | null,
  "sentAt": "string (ISO 8601)"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_brief()`

**Notes:**
- `proactive` status is used for agent-initiated notifications (e.g., background task done).
- Attachments are resolved to absolute paths; images are flagged for inline display.

---

### `Config`

Get or set Mammoth Code settings.

**Permission:** `workspace-write`

**Input schema:**

```json
{
  "setting": "string (required) — dot-notation key e.g. \"model.default\"",
  "value": "string | boolean | number (optional) — omit to read"
}
```

**Output schema:**

```json
{
  "success": "boolean",
  "operation": "\"read\" | \"write\" | null",
  "setting": "string | null",
  "value": "any | null",
  "previousValue": "any | null",
  "newValue": "any | null",
  "error": "string | null"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_config()`

---

### `StructuredOutput`

Return structured output in the requested format.

**Permission:** `read-only`

**Input schema:**

```json
{
  "additionalProperties": true
}
```

**Output schema:**

```json
{
  "data": "string",
  "structured_output": { "...": "any" }
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_structured_output()`

**Notes:**
- Intended for workflows that need machine-readable output at the end of a task.
- The full input object is echoed back as `structured_output`.

---

### `REPL`

Execute code in a language-specific REPL subprocess.

**Permission:** `danger-full-access`

**Input schema:**

```json
{
  "code": "string (required)",
  "language": "string (required) — e.g. \"python\", \"javascript\", \"ruby\"",
  "timeout_ms": "integer (optional, ≥ 1)"
}
```

**Output schema:**

```json
{
  "language": "string",
  "stdout": "string",
  "stderr": "string",
  "exitCode": "integer",
  "durationMs": "number"
}
```

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_repl()`

**Notes:**
- Starts a fresh subprocess per call (not a persistent REPL state).
- Suitable for quick script execution, data transformation, plotting.

---

### `PowerShell`

Execute a PowerShell command (Windows / cross-platform via `pwsh`).

**Permission:** `danger-full-access`

**Input schema:**

```json
{
  "command": "string (required)",
  "timeout": "integer (optional, ≥ 1) — seconds",
  "description": "string (optional)",
  "run_in_background": "boolean (optional)"
}
```

**Output schema:** Same as `bash`.

**Implementation:** `apps/mammoth/crates/tools/src/lib.rs` — `execute_powershell()`

---

## Planned / Deferred Tools

These tools exist in the reference codebase (`apps/claw-code-ref/src/tools/`) and are
slated for Mammoth port. They are surfaced by `ToolSearch` once their MCP or plugin
implementations are registered.

| Tool | Source Path | Category | Status |
|------|------------|----------|--------|
| `EnterPlanMode` | `EnterPlanModeTool/` | Planning | Planned (v0.4.0) |
| `ExitPlanMode` | `ExitPlanModeTool/` | Planning | Planned |
| `EnterWorktree` | `EnterWorktreeTool/` | Worktree | Planned |
| `ExitWorktree` | `ExitWorktreeTool/` | Worktree | Planned |
| `TeamCreate` | `TeamCreateTool/` | Multi-agent | Planned |
| `TeamDelete` | `TeamDeleteTool/` | Multi-agent | Planned |
| `SendMessage` | `SendMessageTool/` | Multi-agent | Planned |
| `TaskCreate` | `TaskCreateTool/` | Task mgmt | Planned |
| `TaskGet` | `TaskGetTool/` | Task mgmt | Planned |
| `TaskList` | `TaskListTool/` | Task mgmt | Planned |
| `TaskUpdate` | `TaskUpdateTool/` | Task mgmt | Planned |
| `TaskStop` | `TaskStopTool/` | Task mgmt | Planned |
| `TaskOutput` | `TaskOutputTool/` | Task mgmt | Planned |
| `LSP` | `LSPTool/` | LSP | Planned |
| `ListMcpResources` | `ListMcpResourcesTool/` | MCP | Planned |
| `ReadMcpResource` | `ReadMcpResourcesTool/` | MCP | Planned |
| `McpAuth` | `McpAuthTool/` | MCP | Planned |
| `RemoteTrigger` | `RemoteTriggerTool/` | Remote | Planned |
| `ScheduleCron` | `ScheduleCronTool/` | Automation | Planned |
| `AskUserQuestion` | `AskUserQuestionTool/` | UX | Planned |
| `WebSearch` (extended) | — | Web | v0.3.0 ✓ |

---

## Plugin Tools

Third-party tools are registered at startup via the `PluginTool` interface
(`apps/mammoth/crates/plugins/src/`). Constraints:

- Name must not conflict with any built-in tool.
- Must declare one of `"read-only"`, `"workspace-write"`, `"danger-full-access"` as
  `required_permission`.
- Must implement `execute(input: &Value) -> Result<String, PluginError>`.

Example registration (`Cargo.toml` dependency on a plugin crate):

```toml
# apps/mammoth/Cargo.toml
mammoth-plugin-github = { path = "../plugins/github" }
```

```rust
// apps/mammoth/src/main.rs
let plugin_tools = vec![
    mammoth_plugin_github::create_tool(),
];
let registry = GlobalToolRegistry::with_plugin_tools(plugin_tools)?;
```

---

## Implementing a New Built-in Tool

1. Add a `ToolSpec` entry to `mvp_tool_specs()` in
   `apps/mammoth/crates/tools/src/lib.rs`.
2. Add a `match` arm in `execute_tool()`.
3. Define input/output `struct`s with `#[derive(Deserialize)]` / `#[derive(Serialize)]`.
4. Implement `fn run_<name>(input: MyInput) -> Result<String, String>`.
5. Call `to_pretty_json()` on the output struct to produce the JSON string result.
6. Add tests in the `#[cfg(test)]` block.
