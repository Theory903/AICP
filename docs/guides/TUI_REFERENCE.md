# Mammoth TUI Reference

> **Complete terminal UI specification for Mammoth — the peak agentic shell.**
> Every interaction surface, layout region, rendering behavior, and keyboard binding.

---

## Overview

Mammoth's terminal channel is a first-class TUI built on top of a Rust rendering pipeline. It is not a simple readline REPL — it is a full-featured interactive shell with:

- Multi-pane layout (conversation, tool timeline, context sidebar)
- Real-time streaming of model output with syntax highlighting
- Inline tool call visualization with collapsible details
- Integrated approval prompts for AICP governance gates
- Slash command palette with fuzzy search
- Session browser and resume picker
- Plan mode visualization
- Agent status panel for multi-agent runs
- Live diff viewer for file edits
- LSP-powered inline diagnostics

---

## Layout Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ HEADER: model selector · session id · cost counter · status indicator   │
├──────────────────────────────────────────────────┬──────────────────────┤
│                                                  │  CONTEXT SIDEBAR     │
│  CONVERSATION PANE                               │                      │
│                                                  │  Files in context    │
│  [assistant]  Streaming response text...         │  ──────────────────  │
│               with syntax-highlighted code       │  src/main.rs  +3     │
│               blocks and inline diffs            │  Cargo.toml   +1     │
│                                                  │                      │
│  [tool]  bash: cargo build                       │  ──────────────────  │
│    └─ [expand] exit 0, 2.3s                      │  MCP SERVERS         │
│                                                  │  ● postgres (5 tools)│
│  [approval]  ● APPROVAL REQUIRED                 │  ● github   (3 tools)│
│    │  orders.place  risk: HIGH                   │  ○ filesystem offline │
│    │  [a] approve  [r] reject  [d] delegate      │                      │
│    └──────────────────────────────────────────── │  ──────────────────  │
│                                                  │  AGENTS              │
│  ────────────────────────────────────────────    │  worker-1  ● running │
│                                                  │  worker-2  ✓ done    │
│  INPUT                                           │  worker-3  ● running │
│  > _                                             │                      │
│                                                  │  ──────────────────  │
│  [tokens: 4,821] [cost: $0.032] [ctx: 67%]       │  MEMORY              │
│                                                  │  12 memories active  │
├──────────────────────────────────────────────────┴──────────────────────┤
│ STATUS BAR: mode · model · branch · working dir · keybindings           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Panes

| Pane | ID | Default | Toggle |
|------|----|---------|--------|
| Conversation | `conv` | Visible | — |
| Context Sidebar | `ctx` | Visible | `Ctrl+B` |
| Tool Timeline | `tools` | Collapsed | `Ctrl+T` |
| Agent Panel | `agents` | Auto-show on multi-agent | `Ctrl+A` |
| Diff Viewer | `diff` | Auto-show on file edits | `Ctrl+D` |
| Memory Viewer | `mem` | Hidden | `Ctrl+M` |
| Plan Viewer | `plan` | Auto-show in plan mode | `Ctrl+P` |
| Session Browser | `sessions` | Hidden | `Ctrl+R` |

---

## Header Bar

```
claude-sonnet-4-5  ·  sess_a1b2  ·  ↑ $0.032  ·  ● ready
```

### Components

| Component | Content | Interaction |
|-----------|---------|-------------|
| Model selector | Current model name | Click/`Ctrl+;` opens picker |
| Session ID | Short session hash | Click copies full ID |
| Cost counter | Cumulative session cost | Click shows cost breakdown |
| Status indicator | `● ready` / `● thinking` / `● waiting` / `⚠ approval` | — |
| Context fill | Token bar `████░░░ 67%` | Click shows token breakdown |
| Branch | `git: main` | — |

### Status States

| State | Symbol | Color | Description |
|-------|--------|-------|-------------|
| `ready` | ● | green | Idle, awaiting input |
| `thinking` | ● | yellow (pulse) | Model generating |
| `running` | ● | blue | Tool executing |
| `waiting` | ● | orange | Awaiting approval |
| `plan_mode` | ◆ | purple | In plan mode |
| `worktree` | ⬡ | cyan | In worktree isolation |
| `error` | ✖ | red | Last action failed |

---

## Conversation Pane

### Message Types

#### Assistant Message
```
[assistant]  Here is the updated Cargo.toml:

             ```toml
             [dependencies]
             tokio = { version = "1", features = ["full"] }
             ```

             This adds async runtime support.
```

#### Tool Call (Collapsed)
```
[tool]  bash: cargo build --release
  └─ ✓ exit 0  ·  4.2s  ·  [e] expand
```

#### Tool Call (Expanded)
```
[tool]  bash: cargo build --release
  │
  │  Compiling mammoth v0.3.0
  │  Compiling mammoth-cli v0.3.0
  │  Finished release [optimized] in 4.23s
  │
  └─ ✓ exit 0  ·  4.2s  ·  [c] collapse
```

#### Inline File Diff
```
[edit]  src/main.rs
  ┌─────────────────────────────┐
  │  - fn old_function() {      │  ← red
  │  + fn new_function() {      │  ← green
  │      println!("hello");     │
  │  }                          │
  └─────────────────────────────┘
  [a] apply  [r] reject  [v] view full file
```

#### Approval Prompt (inline)
```
  ╔══════════════════════════════════════════════════════╗
  ║  ⚠ APPROVAL REQUIRED                                ║
  ║                                                      ║
  ║  Capability:  orders.place                           ║
  ║  Risk:        HIGH  (financial · irreversible)       ║
  ║  Amount:      $4,200.00 to vendor-id-847            ║
  ║                                                      ║
  ║  Impact:      Creates payment record, charges card   ║
  ║  Blast radius: Single transaction, reversible <24h   ║
  ║                                                      ║
  ║  [a] Approve   [r] Reject   [d] Delegate   [?] More ║
  ╚══════════════════════════════════════════════════════╝
```

#### System Message
```
[system]  Session resumed from sess_a1b2 · 14 turns
```

#### Error Message
```
[error]  Tool execution failed: bash
         Exit code: 127 — command not found: cargo
         [retry] [fix] [skip]
```

#### Memory Extraction
```
[memory]  ✦ Saved: "User prefers concise commit messages"
```

---

## Input Area

### Modes

| Mode | Indicator | Description |
|------|-----------|-------------|
| Normal | `> ` | Standard input |
| Command | `/` | Slash command entry |
| Search | `?` | Fuzzy history search |
| Filter | `#` | Filter by tag or keyword |
| Edit | `[edit]` | Multi-line editor (opens $EDITOR) |
| Plan | `◆ ` | Input in plan mode (read-only execution) |

### Multi-line Input
- `Shift+Enter` — insert newline in input
- `Ctrl+E` — open full editor ($EDITOR or nano fallback)
- `Ctrl+V` — paste (with preview for large pastes)

### Input Attachments
- `@filename` — attach file to context (tab-completion from git-tracked files)
- `@url` — fetch URL and attach
- `@#tag` — attach all files tagged in memory
- `!command` — run shell command and attach output

### History
- `Up/Down` — navigate input history
- `Ctrl+R` — fuzzy search history
- History persisted per session in `~/.mammoth/sessions/<id>/history`

---

## Keyboard Bindings

### Global

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current action / interrupt model |
| `Ctrl+D` | Exit (prompts if session unsaved) |
| `Esc` | Close overlay / cancel input |
| `Ctrl+L` | Clear conversation display |
| `Ctrl+Z` | Undo last edit (if in worktree) |
| `Tab` | Autocomplete command/path/model |
| `F1` | Open help overlay |
| `F2` | Open slash command palette |

### Navigation

| Key | Action |
|-----|--------|
| `Ctrl+Up/Down` | Scroll conversation |
| `PgUp/PgDn` | Scroll page in conversation |
| `Ctrl+Home` | Jump to session start |
| `Ctrl+End` | Jump to latest message |
| `Ctrl+F` | Search in conversation |

### Pane Control

| Key | Action |
|-----|--------|
| `Ctrl+B` | Toggle context sidebar |
| `Ctrl+T` | Toggle tool timeline |
| `Ctrl+A` | Toggle agent panel |
| `Ctrl+M` | Toggle memory viewer |
| `Ctrl+P` | Toggle plan viewer |
| `Ctrl+R` | Open session browser |
| `Ctrl+W` | Cycle focused pane |

### Tool Actions

| Key | Action |
|-----|--------|
| `e` (on tool) | Expand tool output |
| `c` (on tool) | Collapse tool output |
| `y` (on approval) | Approve |
| `n` (on approval) | Reject |
| `d` (on approval) | Delegate |
| `a` (on diff) | Apply diff |
| `r` (on diff) | Reject diff |
| `v` (on diff) | View full file |

### Model / Session

| Key | Action |
|-----|--------|
| `Ctrl+;` | Open model picker |
| `Ctrl+N` | New session |
| `Ctrl+R` | Resume session |
| `Ctrl+S` | Save session snapshot |

---

## Slash Command Palette

Triggered by typing `/` in input. Provides fuzzy search with preview.

```
  ┌────────────────────────────────────────────────────────────┐
  │ /  Search commands...                                      │
  │                                                            │
  │  ● /doctor          Run diagnostics                        │
  │  ● /resume          Resume a previous session              │
  │  ● /model           Switch AI model                        │
  │  ● /mcp             Manage MCP servers                     │
  │  ● /memory          View and edit memories                 │
  │  ● /plan            Enter plan mode                        │
  │  ● /worktree        Enter worktree isolation               │
  │  ● /agents          Spawn agent team                       │
  │  ● /task            Manage background tasks                │
  │  ● /approval        View approval queue                    │
  │  ● /history         Browse audit log                       │
  │  ● /context         Manage context files                   │
  │  ● /git             Git operations                         │
  │  ● /bridge          IDE bridge control                     │
  │  ● /review          Run code review                        │
  │  ● /status          Show system status                     │
  │  ● /config          Edit configuration                     │
  │  ● /help            Show help                              │
  │                                                            │
  │  [↑↓] navigate  [↵] select  [Esc] close                   │
  └────────────────────────────────────────────────────────────┘
```

Full slash command documentation: [SLASH_COMMANDS.md](./SLASH_COMMANDS.md)

---

## Model Picker

Triggered by `Ctrl+;` or `/model`.

```
  ┌─────────────────────────────────────────────────────────────┐
  │ Select Model                                  [Esc] close   │
  │                                                             │
  │  ANTHROPIC                                                  │
  │  ● claude-sonnet-4-5      ◆ recommended  $3/$15 per M      │
  │    claude-opus-4-5                        $15/$75 per M     │
  │    claude-haiku-3-5                       $0.25/$1.25 per M │
  │                                                             │
  │  OPENAI                                                     │
  │    gpt-4o                                 $2.50/$10 per M   │
  │    gpt-4o-mini                            $0.15/$0.60 per M │
  │    o3                                     $10/$40 per M     │
  │    o4-mini                                $1.10/$4.40 per M │
  │                                                             │
  │  GOOGLE                                                     │
  │    gemini-2.5-pro                         $1.25/$10 per M   │
  │    gemini-2.0-flash                       $0.10/$0.40 per M │
  │                                                             │
  │  LOCAL (Ollama)                                             │
  │    llama3.3-70b                           ● running         │
  │    qwen2.5-coder-32b                      ● running         │
  │    gemma3-27b                             ○ not loaded      │
  │                                                             │
  │  CUSTOM                                                     │
  │    + Add custom endpoint...                                 │
  │                                                             │
  │  [↑↓] navigate  [↵] select  [/] search                     │
  └─────────────────────────────────────────────────────────────┘
```

---

## Session Browser

Triggered by `Ctrl+R` or `/resume`.

```
  ┌─────────────────────────────────────────────────────────────┐
  │ Sessions                                      [Esc] close   │
  │                                                             │
  │  THIS PROJECT (/CODE/AICP)                                  │
  │                                                             │
  │  ● sess_a1b2  2 mins ago   "Fix capability validation"      │
  │    sess_c3d4  1 hour ago   "Add workflow DSL support"       │
  │    sess_e5f6  Yesterday    "Update CLI reference"           │
  │                                                             │
  │  OTHER PROJECTS                                             │
  │                                                             │
  │    sess_g7h8  2 days ago   /CODE/myapp  "Setup database"    │
  │    sess_i9j0  3 days ago   /CODE/api    "Add auth endpoints" │
  │                                                             │
  │  WORKTREE SESSIONS                                          │
  │                                                             │
  │    sess_k1l2  ⬡ feat/auth  "Implement JWT flow"            │
  │                                                             │
  │  [↑↓] navigate  [↵] resume  [d] delete  [/] search         │
  └─────────────────────────────────────────────────────────────┘
```

---

## Tool Timeline

Full-width panel below conversation, toggled with `Ctrl+T`.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ TOOL TIMELINE                                            [c] close  │
  │                                                                     │
  │  #1  bash         cargo build          ✓  4.2s  │████░░░░│          │
  │  #2  read_file    src/main.rs          ✓  0.1s  │█░░░░░░░│          │
  │  #3  edit_file    src/main.rs          ✓  0.2s  │█░░░░░░░│          │
  │  #4  bash         cargo test           ✓  8.7s  │████████│          │
  │  #5  orders.place $4,200 payment       ⚠ WAIT   │░░░░░░░░│ pending  │
  │                                                                     │
  │  Total: 4 complete · 1 pending · 13.2s · $0.002 tool cost           │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## Context Sidebar

```
  ┌──────────────────────────┐
  │ CONTEXT             [×]  │
  │                          │
  │ FILES (4)                │
  │ ──────────────────────── │
  │ 📄 src/main.rs    3.2 KB │
  │ 📄 Cargo.toml     0.8 KB │
  │ 📄 src/lib.rs     8.1 KB │
  │ 📄 AGENTS.md     24.3 KB │
  │                          │
  │ [+ add file]             │
  │                          │
  │ INSTRUCTIONS             │
  │ ──────────────────────── │
  │ AGENTS.md ✓              │
  │ MAMMOTH.md ✓             │
  │                          │
  │ MCP SERVERS (2)          │
  │ ──────────────────────── │
  │ ● postgres  5 tools      │
  │ ● github    3 tools      │
  │                          │
  │ TOKEN BUDGET             │
  │ ──────────────────────── │
  │ ████████░░░░ 67%         │
  │ 67k / 100k tokens        │
  │ [manage]                 │
  │                          │
  │ MEMORIES (12)            │
  │ ──────────────────────── │
  │ ✦ Prefers concise msgs   │
  │ ✦ Uses ruff for linting  │
  │ ✦ Project: AICP v0.3     │
  │ [view all]               │
  └──────────────────────────┘
```

---

## Agent Panel

Auto-shows when multi-agent run is active. Toggle with `Ctrl+A`.

```
  ┌──────────────────────────┐
  │ AGENTS              [×]  │
  │                          │
  │ COORDINATOR              │
  │ ● orchestrator  thinking │
  │   "Decomposing task..."  │
  │                          │
  │ WORKERS                  │
  │ ──────────────────────── │
  │ ● worker-1   running     │
  │   bash: cargo build      │
  │   [last: 2.3s ago]       │
  │                          │
  │ ✓ worker-2   complete    │
  │   "Auth module done"     │
  │   3 tools · 45s          │
  │                          │
  │ ● worker-3   running     │
  │   read_file: schema.json │
  │                          │
  │ ○ worker-4   queued      │
  │   "Tests to run"         │
  │                          │
  │ MESSAGES                 │
  │ ──────────────────────── │
  │ w1→coord: "build ok"     │
  │ coord→w3: "start tests"  │
  │                          │
  │ [view log] [send message]│
  └──────────────────────────┘
```

---

## Plan Viewer

Auto-shows in plan mode. Toggle with `Ctrl+P`.

```
  ┌──────────────────────────────────────────────────────────────┐
  │ PLAN MODE ◆                                        [×] exit  │
  │                                                              │
  │ Goal: Implement JWT authentication for the API              │
  │                                                              │
  │  ✓  1. Add jsonwebtoken dependency to Cargo.toml            │
  │  ✓  2. Create auth module src/auth/mod.rs                   │
  │  ▶  3. Implement token generation function  ← CURRENT        │
  │  ○  4. Implement token validation middleware                 │
  │  ○  5. Add auth routes to router                            │
  │  ○  6. Write integration tests                              │
  │  ○  7. Update API documentation                             │
  │                                                              │
  │  Progress: 2/7 · Est. remaining: ~12 min                    │
  │                                                              │
  │  [edit plan] [add step] [mark done] [abandon]               │
  └──────────────────────────────────────────────────────────────┘
```

---

## Doctor / Diagnostics Overlay

Triggered by `/doctor`. Full-screen overlay.

```
  ┌────────────────────────────────────────────────────────────────────┐
  │ MAMMOTH DIAGNOSTICS                                   v0.3.0      │
  │                                                                    │
  │  INSTALLATION                                                      │
  │  ✓ Binary: /usr/local/bin/mammoth (0.3.0)                         │
  │  ✓ Config: ~/.mammoth.json                                        │
  │  ✓ Session store: ~/.mammoth/sessions/ (6 sessions)               │
  │  ✓ Memory store: ~/.mammoth/memory/ (24 entries)                  │
  │  ⚠ Locks: ~/.mammoth/locks/sess_old.lock (stale, [clean])        │
  │                                                                    │
  │  PROVIDERS                                                         │
  │  ✓ Anthropic API: reachable (latency: 142ms)                     │
  │  ✓ OpenAI API: reachable (latency: 89ms)                         │
  │  ○ Google AI: not configured                                      │
  │  ✓ Ollama: running (3 models loaded)                              │
  │  ✗ Custom endpoint: unreachable (timeout)                        │
  │                                                                    │
  │  TOOLS                                                             │
  │  ✓ bash: /bin/bash available                                      │
  │  ✓ git: 2.47.0                                                    │
  │  ✓ cargo: 1.84.0                                                  │
  │  ⚠ node: not in PATH (JS tools will fail)                        │
  │                                                                    │
  │  MCP SERVERS                                                       │
  │  ✓ postgres: connected (5 tools registered)                       │
  │  ✗ github: error parsing config — invalid JSON                   │
  │                                                                    │
  │  AICP RUNTIME                                                      │
  │  ✓ Runtime: http://localhost:8080 (healthy)                       │
  │  ✓ Capabilities registered: 14                                    │
  │  ✓ Active approvals: 0                                            │
  │                                                                    │
  │  LSP                                                               │
  │  ✓ rust-analyzer: running (PID 12345)                             │
  │  ○ typescript-language-server: not running                        │
  │                                                                    │
  │  SUMMARY: 2 warnings · 2 errors                                   │
  │                                                                    │
  │  [fix issues]  [copy report]  [close]                             │
  └────────────────────────────────────────────────────────────────────┘
```

---

## Status Bar

```
  ● ready   claude-sonnet-4-5   ⎇ main   ~/CODE/AICP   [?] help   [/] cmd
```

| Segment | Content | States |
|---------|---------|--------|
| Mode dot | `● ready` / `● thinking` / `◆ plan` | see Status States |
| Model | Current model short name | — |
| Branch | `⎇ branchname` | Only if git repo |
| CWD | Abbreviated working directory | — |
| Help hint | `[?] help` | — |
| Command hint | `[/] cmd` | — |

---

## Color Scheme

Mammoth uses a perceptual color scheme designed for long sessions in terminal.

| Token | Color (hex) | Usage |
|-------|-------------|-------|
| `text_primary` | `#E8E8E8` | Normal text |
| `text_secondary` | `#888888` | Timestamps, hints |
| `text_dim` | `#555555` | Collapsed previews |
| `accent_green` | `#4EC9B0` | Success, approve, running |
| `accent_yellow` | `#E5C07B` | Warning, thinking |
| `accent_red` | `#E06C75` | Error, reject, deny |
| `accent_blue` | `#61AFEF` | Info, tool calls |
| `accent_purple` | `#C678DD` | Plan mode, AI |
| `accent_cyan` | `#56B6C2` | Worktree, isolation |
| `accent_orange` | `#D19A66` | Approval, waiting |
| `diff_add` | `#3D5A3E` | Added lines in diffs |
| `diff_del` | `#5A3D3D` | Removed lines in diffs |
| `border` | `#333333` | Panel borders |
| `border_active` | `#4A4A4A` | Focused panel border |

### Theme Support

Mammoth ships three built-in themes and supports custom themes via `~/.mammoth.json`:

| Theme | ID | Description |
|-------|----|-------------|
| Default Dark | `dark` | Default, optimized for dark terminals |
| Default Light | `light` | For light terminal backgrounds |
| High Contrast | `hc` | WCAG AA accessible |
| Catppuccin Mocha | `catppuccin-mocha` | Community favorite |
| Tokyo Night | `tokyo-night` | Balanced dark theme |

---

## Configuration

`~/.mammoth.json` controls all TUI behavior:

```json
{
  "theme": "dark",
  "model": "claude-sonnet-4-5",
  "sidebar": {
    "visible": true,
    "width": 28
  },
  "tool_timeline": {
    "auto_expand_errors": true,
    "collapse_successes_after_ms": 2000
  },
  "input": {
    "history_size": 1000,
    "multiline_key": "shift+enter",
    "editor": "nano"
  },
  "conversation": {
    "timestamps": true,
    "show_token_counts": true,
    "cost_display": "session"
  },
  "approval": {
    "auto_approve_trust_tier": 0,
    "show_blast_radius": true,
    "default_delegate_to": null
  },
  "memory": {
    "auto_extract": true,
    "extraction_threshold": 5
  },
  "providers": {
    "anthropic": { "api_key_env": "ANTHROPIC_API_KEY" },
    "openai": { "api_key_env": "OPENAI_API_KEY" },
    "google": { "api_key_env": "GOOGLE_API_KEY" },
    "ollama": { "base_url": "http://localhost:11434" }
  }
}
```

---

## Rendering Pipeline

The TUI rendering pipeline in `apps/mammoth/crates/mammoth-cli/src/`:

```
User input
    │
    ▼
input.rs: InputHandler
    │  Parses keystrokes, handles special modes
    │
    ▼
app.rs: App::handle_input()
    │  Routes to command, slash command, or message
    │
    ▼
render.rs: Renderer
    │  Builds frame buffer from app state
    │  Calls into conversation_pane, sidebar, tool_timeline, etc.
    │
    ▼
tui.rs: TuiBackend
    │  Writes frame buffer to terminal via crossterm
    │
    └── Terminal output
```

### Rendering Modules

| Module | File | Responsibility |
|--------|------|---------------|
| `TuiBackend` | `tui.rs` | Terminal backend, event loop, resize handling |
| `Renderer` | `render.rs` | Frame composition, layout calculation |
| `ConversationPane` | `render.rs` | Message list, streaming, tool blocks |
| `InputArea` | `input.rs` | Input field, command mode, history |
| `ContextSidebar` | `render.rs` | File list, MCP, memory, tokens |
| `ToolTimeline` | `render.rs` | Tool execution history |
| `AgentPanel` | `render.rs` | Multi-agent status |
| `PlanViewer` | `render.rs` | Plan mode steps |
| `StatusBar` | `render.rs` | Bottom status line |
| `HeaderBar` | `render.rs` | Top model/session/cost bar |
| `Overlays` | `render.rs` | Modal overlays (doctor, picker, browser) |

---

## Implementation Targets

The current implementation state and gaps:

| Component | Status | File |
|-----------|--------|------|
| Basic REPL | ✓ Complete | `app.rs`, `input.rs` |
| Streaming render | ✓ Complete | `render.rs` |
| Tool call display | ✓ Basic | `render.rs` |
| Inline approval | ✓ Complete | `tui.rs` |
| Status bar | ✓ Basic | `render.rs` |
| Slash command palette | ○ Planned | `commands/src/lib.rs` |
| Model picker overlay | ○ Planned | `render.rs` |
| Session browser | ○ Planned | `tui.rs` |
| Context sidebar | ○ Planned | `render.rs` |
| Agent panel | ○ Planned | `render.rs` |
| Plan viewer | ○ Planned | `render.rs` |
| Tool timeline | ○ Planned | `render.rs` |
| Diff viewer | ○ Planned | `render.rs` |
| Doctor overlay | ○ Planned | `render.rs` |
| Theme system | ○ Planned | `tui.rs` |
| Memory viewer | ○ Planned | `render.rs` |
| LSP diagnostics | ○ Planned | `lsp/src/` |

---

## Web UI (Studio / Mammoth Web)

Started via `mammoth serve`. Accessible at `http://localhost:3000`.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MAMMOTH STUDIO              Sessions · Approvals · Audit · Config       │
├──────────────────┬──────────────────────────────────────────────────────┤
│                  │                                                       │
│  SESSIONS        │  CONVERSATION                                         │
│  ─────────────── │                                                       │
│  ● sess_a1b2     │  [assistant]  Here is the updated code...            │
│    2 mins ago    │                                                       │
│                  │  [tool]  edit_file · src/main.rs                     │
│  sess_c3d4       │                                                       │
│    1 hour ago    │  ──────────────────────────────────────────          │
│                  │                                                       │
│  APPROVALS (1)   │  ⚠ PENDING APPROVAL                                  │
│  ─────────────── │  orders.place  risk: HIGH                            │
│  ⚠ orders.place  │  [approve] [reject] [view]                           │
│    HIGH · $4,200 │                                                       │
│                  │  ──────────────────────────────────────────          │
│  AGENTS          │                                                       │
│  ─────────────── │  > _____________________________ [send]              │
│  ● worker-1      │                                                       │
│  ● worker-3      ├──────────────────────────────────────────────────────┤
│                  │  AUDIT LOG                                            │
│                  │  13:42:07  orders.place  approved by human            │
│                  │  13:41:55  bash  exit 0  3.2s                        │
│                  │  13:41:30  Session created  sess_a1b2                 │
└──────────────────┴──────────────────────────────────────────────────────┘
```

### Web API

All described in `apps/mammoth/crates/server/src/`. Full API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | `GET` | Studio HTML |
| `/sessions` | `GET` | List sessions |
| `/sessions` | `POST` | Create session |
| `/sessions/{id}` | `GET` | Session details |
| `/sessions/{id}/events` | `GET` | SSE stream |
| `/sessions/{id}/message` | `POST` | Send message |
| `/sessions/{id}/approve` | `POST` | Submit approval decision |
| `/ext/events` | `GET` | Extension SSE bridge |
| `/ext/message` | `POST` | Extension message receive |
| `/health` | `GET` | Health check |

---

## Chrome Extension

See [EXTENSION_GUIDE.md](./EXTENSION_GUIDE.md) for full details.

Extension files at `apps/mammoth/extension/`:

```
extension/
├── manifest.json       # MV3, permissions: activeTab, storage, scripting
├── background.js       # Service worker, SSE connection to Mammoth Web
├── content.js          # Page context capture (a11y, URL, selection)
├── popup.html          # Minimal conversational overlay UI
└── popup.js            # Popup logic, message routing
```

---

## See Also

- [SLASH_COMMANDS.md](./SLASH_COMMANDS.md) — Full slash command reference
- [PROVIDER_GUIDE.md](./PROVIDER_GUIDE.md) — All model providers
- [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) — All tools
- [MULTI_AGENT.md](./MULTI_AGENT.md) — Nano-bot agentic system
- [MEMORY_SESSIONS.md](./MEMORY_SESSIONS.md) — Memory and session management
- [PLAN_MODE.md](./PLAN_MODE.md) — Plan mode and worktrees
- [PERMISSIONS.md](./PERMISSIONS.md) — Permissions and approvals
- [MCP_GUIDE.md](./MCP_GUIDE.md) — MCP client and server
- [DOCTOR_DIAGNOSTICS.md](./DOCTOR_DIAGNOSTICS.md) — Diagnostics
- [BRIDGE_IDE.md](./BRIDGE_IDE.md) — IDE bridge
- [EXTENSION_GUIDE.md](./EXTENSION_GUIDE.md) — Chrome extension
