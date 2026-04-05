# Multi-Agent System — Mammoth Nano-Bot Guide

**Status:** Planned (v0.4.0 — Phase 3)
**Target crates:** `apps/mammoth/crates/runtime/`, `apps/mammoth/crates/tools/`
**Reference source:** `apps/claw-code-ref/src/tools/` (TypeScript), `apps/claw-code-ref/src/tasks/`

---

## Overview

Mammoth's multi-agent system (internally called the **nano-bot swarm**) allows a single session to
coordinate a fleet of autonomous sub-agents in-process. The leader agent (the main session) creates
teams, assigns tasks, routes messages, monitors progress, and disbands the team when work is done.

This system maps to **Plane 7 (Multi-Agent)** in the AICP 11-plane architecture and is the primary
implementation target for modules 14 (Multi-Agent Hierarchy) and 15 (Agent Communication Bus).

### Key design principles

- **In-process isolation**: Sub-agents run as Tokio tasks sharing the same process. No separate
  processes or containers. Each agent gets its own conversation context, permission mode, and
  tool sandbox.
- **Mailbox communication**: Agents communicate by writing to each other's mailbox files on disk.
  There is no shared mutable state between the leader and teammates at runtime.
- **Memory cap**: The AppState UI mirror for each teammate is capped at 50 messages
  (`TEAMMATE_MESSAGES_UI_CAP`). The full conversation lives in the agent's on-disk transcript.
- **One team per leader**: A leader can manage exactly one team at a time. Use `team_delete` before
  creating a second team.
- **Coordinator mode**: The leader orchestrates but does not do direct work. Sub-agents
  ("specialists") do the actual file edits, searches, and command runs.

---

## Architecture

```
Leader session (main REPL)
│
├── TeamCreateTool → creates team file + task directory
│
├── AgentTool (×N) → spawns InProcessTeammateTask per worker
│   ├── Teammate A (researcher)     ← separate conversation context
│   ├── Teammate B (test-runner)    ← separate permission mode
│   └── Teammate C (implementer)
│
├── SendMessageTool → writes to teammate mailbox
│
├── TaskCreateTool / TaskUpdateTool / TaskGetTool → tracks subtasks
│
└── TeamDeleteTool → cleanup when swarm is done
```

---

## Task Type System

The runtime tracks all concurrent work through a `TaskState` union. Each variant is a distinct
execution model with its own lifecycle.

### TaskState union

```rust
// apps/mammoth/crates/runtime/src/tasks/mod.rs (to implement)
pub enum TaskState {
    LocalShell(LocalShellTaskState),
    LocalAgent(LocalAgentTaskState),
    RemoteAgent(RemoteAgentTaskState),
    InProcessTeammate(InProcessTeammateTaskState),
    LocalWorkflow(LocalWorkflowTaskState),
    MonitorMcp(MonitorMcpTaskState),
    Dream(DreamTaskState),
}
```

Reference: `apps/claw-code-ref/src/tasks/types.ts`

| Variant | Description | Background-capable |
|---------|-------------|-------------------|
| `LocalShell` | A single bash/shell command run in foreground or background | Yes |
| `LocalAgent` | A full sub-agent session running locally in a separate task | Yes |
| `RemoteAgent` | An agent session delegated to a remote AICP runtime | Yes |
| `InProcessTeammate` | An in-process teammate sharing this process's memory space | Yes |
| `LocalWorkflow` | A multi-step AICP workflow running inside this session | Yes |
| `MonitorMcp` | A background task watching an MCP server for events | Yes |
| `Dream` | Speculative/background planning task (no tool use) | Yes |

### Background task rule

A task counts as a "background task" (shown in the background indicator) if:
1. Status is `running` or `pending`, AND
2. `is_backgrounded` is `true` (foreground tasks with `is_backgrounded = false` are not counted)

---

## InProcessTeammateTask

The core in-process sub-agent. Each teammate is a full conversation loop sharing the host process.

### Identity

```rust
// apps/mammoth/crates/runtime/src/tasks/teammate.rs (to implement)
pub struct TeammateIdentity {
    /// Unique agent ID, e.g. "researcher@my-team"
    pub agent_id: String,
    /// Short name, e.g. "researcher"
    pub agent_name: String,
    /// Team name this identity belongs to
    pub team_name: String,
    /// Terminal color for TUI rendering (assigned by teammateLayoutManager)
    pub color: Option<String>,
    /// If true, the teammate must enter plan mode before any side-effecting tools
    pub plan_mode_required: bool,
    /// Session ID of the leader (for parent-level audit linkage)
    pub parent_session_id: String,
}
```

Reference: `apps/claw-code-ref/src/tasks/InProcessTeammateTask/types.ts:TeammateIdentity`

### State

```rust
pub struct InProcessTeammateTaskState {
    // Base task fields (shared by all task types)
    pub id: String,
    pub status: TaskStatus,          // pending | running | idle | done | error
    pub created_at: u64,             // Unix ms

    // Identity
    pub identity: TeammateIdentity,

    // Execution
    pub prompt: String,
    pub model: Option<String>,       // Model override (falls back to session model)
    pub selected_agent: Option<AgentDefinition>,

    // Plan mode
    pub awaiting_plan_approval: bool,

    // Permission mode for this teammate (cycled independently with Shift+Tab)
    pub permission_mode: PermissionMode,

    // State
    pub error: Option<String>,
    pub result: Option<AgentToolResult>,
    pub progress: Option<AgentProgress>,

    // Conversation history mirror for TUI zoom view
    // Full history is in the agent's on-disk transcript
    pub messages: Option<Vec<Message>>,   // CAPPED at TEAMMATE_MESSAGES_UI_CAP = 50

    // Tool use IDs currently executing (for spinner animation)
    pub in_progress_tool_use_ids: HashSet<String>,

    // Messages queued by the user while viewing the teammate transcript
    pub pending_user_messages: Vec<String>,

    // UI rendering
    pub spinner_verb: Option<String>,
    pub past_tense_verb: Option<String>,

    // Lifecycle
    pub is_idle: bool,
    pub shutdown_requested: bool,

    // Progress tracking for delta notifications
    pub last_reported_tool_count: u32,
    pub last_reported_token_count: u32,
}
```

### Memory cap

```rust
// apps/mammoth/crates/runtime/src/tasks/teammate.rs
/// Cap on the UI mirror of teammate messages.
///
/// BQ analysis (2026-03-20) showed ~20MB RSS per agent at 500+ turn sessions
/// and ~125MB per concurrent agent in swarm bursts. A whale session launched 292
/// agents in 2 minutes and hit 36.8GB. The dominant cost was the second full copy
/// of every message in AppState. This cap limits that to the 50 most recent turns.
pub const TEAMMATE_MESSAGES_UI_CAP: usize = 50;

pub fn append_capped_message(messages: &mut Vec<Message>, msg: Message) {
    if messages.len() >= TEAMMATE_MESSAGES_UI_CAP {
        let drop_count = messages.len() - (TEAMMATE_MESSAGES_UI_CAP - 1);
        messages.drain(..drop_count);
    }
    messages.push(msg);
}
```

Reference: `apps/claw-code-ref/src/tasks/InProcessTeammateTask/types.ts:TEAMMATE_MESSAGES_UI_CAP`

---

## Team Tools

### `team_create` — Create a new swarm team

**Crate:** `apps/mammoth/crates/tools/src/lib.rs` (planned)
**Reference:** `apps/claw-code-ref/src/tools/TeamCreateTool/TeamCreateTool.ts`

#### Input schema

```json
{
  "type": "object",
  "properties": {
    "team_name": {
      "type": "string",
      "description": "Name for the new team to create."
    },
    "description": {
      "type": "string",
      "description": "Team description/purpose."
    },
    "agent_type": {
      "type": "string",
      "description": "Type/role of the team lead (e.g. 'researcher', 'test-runner'). Used for team file and inter-agent coordination."
    }
  },
  "required": ["team_name"]
}
```

#### Output schema

```json
{
  "type": "object",
  "properties": {
    "team_name": { "type": "string" },
    "team_file_path": { "type": "string" },
    "lead_agent_id": { "type": "string" }
  },
  "required": ["team_name", "team_file_path", "lead_agent_id"]
}
```

#### Rust implementation target

```rust
// apps/mammoth/crates/tools/src/team_create.rs
pub async fn call_team_create(
    input: TeamCreateInput,
    ctx: &mut ToolContext,
) -> Result<TeamCreateOutput, ToolError> {
    // 1. Reject if leader already leads a team
    if ctx.app_state.team_context.is_some() {
        return Err(ToolError::conflict("already leading a team; use team_delete first"));
    }

    // 2. Generate unique team name (slug-collision avoidance)
    let final_name = generate_unique_team_name(&input.team_name)?;

    // 3. Build lead agent ID: "{TEAM_LEAD_NAME}@{team_name}"
    let lead_id = format!("{}@{}", TEAM_LEAD_NAME, final_name);

    // 4. Write team file to ~/.mammoth/teams/{team_name}.json
    let team_file = TeamFile {
        name: final_name.clone(),
        description: input.description,
        created_at: unix_ms(),
        lead_agent_id: lead_id.clone(),
        lead_session_id: ctx.session_id.clone(),
        members: vec![TeamMember { name: TEAM_LEAD_NAME.into(), agent_id: lead_id.clone(), .. }],
    };
    write_team_file(&final_name, &team_file).await?;

    // 5. Register for session-end cleanup
    register_team_for_cleanup(&final_name);

    // 6. Reset task list directory for fresh task numbering
    reset_task_list(&sanitize_name(&final_name)).await?;

    // 7. Update AppState.team_context
    ctx.set_team_context(TeamContext {
        team_name: final_name.clone(),
        lead_agent_id: lead_id.clone(),
        teammates: HashMap::new(),
    });

    Ok(TeamCreateOutput { team_name: final_name, team_file_path: ..., lead_agent_id: lead_id })
}
```

#### Behavior notes

- If `team_name` already exists as a team file, a new word slug is generated automatically.
- A leader can only manage one team at a time. Attempting to create a second team fails.
- Task list directory is reset so subtask numbering starts at 1 per team.
- The leader is registered as the first member but is NOT marked as a "teammate" (`isTeammate()` returns false for them). This prevents inbox polling loops.

---

### `team_delete` — Disband the current team

**Reference:** `apps/claw-code-ref/src/tools/TeamDeleteTool/TeamDeleteTool.ts`

#### Input schema

```json
{ "type": "object", "properties": {} }
```

#### Output schema

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "message": { "type": "string" },
    "team_name": { "type": "string" }
  },
  "required": ["success", "message"]
}
```

#### Behavior notes

- Reads team file. If non-lead members with `is_active != false` remain, returns `success: false`
  with an error listing active members. Caller must send `shutdown_request` messages first.
- Calls `cleanup_team_directories(team_name)` to remove team file, task list, and mailbox files.
- Clears AppState `team_context` and `inbox.messages`.
- Clears teammate color assignments so new teams start fresh.
- Unregisters the team from session-cleanup (prevents double cleanup).

---

### `agent` — Spawn or resume a sub-agent

**Reference:** `apps/claw-code-ref/src/tools/AgentTool/AgentTool.ts`

This is the primary tool the leader uses to spin up a teammate. It creates an
`InProcessTeammateTaskState`, registers it in AppState, and starts the sub-agent's main loop
as a Tokio task.

#### Input schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Unique teammate name within this team (e.g. 'researcher', 'test-runner')."
    },
    "prompt": {
      "type": "string",
      "description": "Initial system prompt / task description for this agent."
    },
    "model": {
      "type": "string",
      "description": "Optional model override for this agent. Defaults to session model."
    },
    "permission_mode": {
      "type": "string",
      "enum": ["read-only", "workspace-write", "danger-full-access", "prompt", "allow"],
      "description": "Permission level for this agent's tool calls."
    },
    "plan_mode_required": {
      "type": "boolean",
      "default": false,
      "description": "If true, the agent must submit a plan and receive leader approval before executing any side-effecting tools."
    }
  },
  "required": ["name", "prompt"]
}
```

#### Output schema

```json
{
  "type": "object",
  "properties": {
    "agent_id": { "type": "string" },
    "status": { "type": "string" },
    "result": { "type": ["string", "null"] },
    "error": { "type": ["string", "null"] }
  },
  "required": ["agent_id", "status"]
}
```

#### Rust implementation target

```rust
// apps/mammoth/crates/tools/src/agent.rs
pub async fn call_agent(
    input: AgentInput,
    ctx: &mut ToolContext,
) -> Result<AgentOutput, ToolError> {
    let team_name = ctx.app_state.team_context.as_ref()
        .map(|tc| tc.team_name.clone())
        .ok_or_else(|| ToolError::precondition("no active team; use team_create first"))?;

    let agent_id = format!("{}@{}", &input.name, &team_name);
    let identity = TeammateIdentity {
        agent_id: agent_id.clone(),
        agent_name: input.name.clone(),
        team_name: team_name.clone(),
        color: assign_teammate_color(&agent_id),
        plan_mode_required: input.plan_mode_required.unwrap_or(false),
        parent_session_id: ctx.session_id.clone(),
    };

    let task_state = InProcessTeammateTaskState {
        id: generate_task_id(),
        status: TaskStatus::Pending,
        identity,
        prompt: input.prompt.clone(),
        model: input.model,
        permission_mode: input.permission_mode.unwrap_or(PermissionMode::WorkspaceWrite),
        messages: None,
        in_progress_tool_use_ids: HashSet::new(),
        pending_user_messages: Vec::new(),
        is_idle: false,
        shutdown_requested: false,
        awaiting_plan_approval: false,
        last_reported_tool_count: 0,
        last_reported_token_count: 0,
        ..Default::default()
    };

    // Register task in AppState
    ctx.register_task(task_state.clone());

    // Spawn the agent's main loop as an async task
    let handle = tokio::spawn(run_in_process_teammate(
        task_state,
        ctx.shared_state.clone(),
    ));

    // Wait for completion (or yield to leader if agent is backgrounded)
    match handle.await? {
        Ok(result) => Ok(AgentOutput { agent_id, status: "done".into(), result: Some(result), error: None }),
        Err(e) => Ok(AgentOutput { agent_id, status: "error".into(), result: None, error: Some(e.to_string()) }),
    }
}
```

---

### `send_message` — Send a message to a teammate

**Reference:** `apps/claw-code-ref/src/tools/SendMessageTool/SendMessageTool.ts`

#### Input schema

```json
{
  "type": "object",
  "properties": {
    "to": {
      "type": "string",
      "description": "Recipient: teammate name, or '*' for broadcast to all teammates."
    },
    "message": {
      "oneOf": [
        { "type": "string", "description": "Plain text message content." },
        {
          "type": "object",
          "description": "Structured message.",
          "oneOf": [
            {
              "properties": { "type": { "const": "shutdown_request" }, "reason": { "type": "string" } },
              "required": ["type"]
            },
            {
              "properties": {
                "type": { "const": "shutdown_response" },
                "request_id": { "type": "string" },
                "approve": { "type": "boolean" },
                "reason": { "type": "string" }
              },
              "required": ["type", "request_id", "approve"]
            },
            {
              "properties": {
                "type": { "const": "plan_approval_response" },
                "request_id": { "type": "string" },
                "approve": { "type": "boolean" },
                "feedback": { "type": "string" }
              },
              "required": ["type", "request_id", "approve"]
            }
          ]
        }
      ]
    },
    "summary": {
      "type": "string",
      "description": "5-10 word summary shown in TUI message preview."
    }
  },
  "required": ["to", "message"]
}
```

#### Message routing

- Plain `to: "researcher"` → writes to `~/.mammoth/mailboxes/{team_name}/researcher.jsonl`
- `to: "*"` → broadcasts to all non-lead teammates' mailboxes
- Structured `shutdown_request` → initiates graceful termination of named teammate
- Structured `plan_approval_response` → approves or rejects a plan submitted by a teammate in plan mode

#### Mailbox file format

```json
{"from":"team-lead","text":"Please search for all usages of deprecated API X.","summary":"search deprecated API","timestamp":"2026-04-05T12:00:00.000Z","color":"#7c3aed"}
```

---

## Task Tools

These tools allow the leader and teammates to create, track, and update a shared task backlog.
Tasks are stored as JSON files in `~/.mammoth/tasks/{task_list_id}/`.

### `task_create`

```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "description": { "type": "string" },
    "assignee": { "type": "string", "description": "Agent ID to assign this task to." },
    "priority": { "type": "integer", "minimum": 0, "maximum": 3 }
  },
  "required": ["name"]
}
```

### `task_update`

```json
{
  "type": "object",
  "properties": {
    "task_id": { "type": "string" },
    "status": { "type": "string", "enum": ["pending", "in_progress", "blocked", "done", "cancelled"] },
    "result": { "type": "string" },
    "assignee": { "type": "string" }
  },
  "required": ["task_id"]
}
```

### `task_get` / `task_list`

Read a single task or the full task list for the current team.

### `task_output`

Append output lines to a task's output log.

### `task_stop`

Request cancellation of a running task (sends abort signal to the assignee's task handle).

---

## Team Presets

Presets are predefined swarm configurations the user can invoke with `/team <preset>`. They
pre-configure teammate names, roles, permission modes, and initial prompts.

| Preset | Members | Use Case |
|--------|---------|----------|
| `research` | lead + researcher + summarizer | Background research with synthesis |
| `dev` | lead + implementer + test-runner + reviewer | Full TDD feature cycle |
| `audit` | lead + security-auditor + compliance-checker | Security and policy review |
| `refactor` | lead + analyzer + refactorer + verifier | Large-scale refactoring |
| `docs` | lead + reader + writer + editor | Documentation generation |

### Preset definition (planned)

```rust
// apps/mammoth/crates/runtime/src/swarm/presets.rs
pub struct TeamPreset {
    pub name: &'static str,
    pub description: &'static str,
    pub members: Vec<PresetMember>,
}

pub struct PresetMember {
    pub name: &'static str,
    pub role_description: &'static str,
    pub permission_mode: PermissionMode,
    pub plan_mode_required: bool,
    pub model_hint: Option<&'static str>, // e.g. "fast" → haiku, "best" → sonnet
}

pub fn builtin_presets() -> Vec<TeamPreset> {
    vec![
        TeamPreset {
            name: "dev",
            description: "Full TDD feature development cycle",
            members: vec![
                PresetMember { name: "implementer", permission_mode: PermissionMode::WorkspaceWrite, plan_mode_required: true, .. },
                PresetMember { name: "test-runner", permission_mode: PermissionMode::WorkspaceWrite, plan_mode_required: false, .. },
                PresetMember { name: "reviewer", permission_mode: PermissionMode::ReadOnly, plan_mode_required: false, .. },
            ],
        },
        // ... more presets
    ]
}
```

---

## Coordinator Mode

When the user runs `/coordinator` or launches Mammoth with `--coordinator`, the session operates
in a special mode:

- The leader does **not** directly edit files or run bash commands
- The leader's tool use is restricted to: `team_create`, `agent`, `send_message`, `task_*`, `read_file`, `glob`, `grep`
- All file modifications and command runs are delegated to sub-agents
- The leader's system prompt is augmented with coordinator instructions

### Coordinator system prompt fragment (to be injected)

```
You are coordinating a team of specialized agents. Your job is:
1. Break the user's request into clear, parallelizable subtasks.
2. Spawn the right sub-agents using the `agent` tool.
3. Monitor progress via `task_list` and the agent panel.
4. Route messages and approvals using `send_message`.
5. Do NOT use bash, write_file, or edit_file yourself.
6. When all tasks are complete, synthesize results and present to the user.
```

---

## Agent Panel (TUI)

The agent panel (`Ctrl+A`) shows all active and idle teammates in the right sidebar.

```
┌─ Agents ─────────────────────┐
│ [●] researcher  reading…     │
│ [●] implementer writing…     │
│ [○] test-runner  idle        │
│                               │
│ 2 active · 1 idle · 0 error  │
└──────────────────────────────┘
```

- `[●]` = actively processing (spinner)
- `[○]` = idle (awaiting next message)
- `[!]` = error state
- Click or press Enter on a teammate to open the zoomed transcript view

### Zoomed transcript view

Shows the last `TEAMMATE_MESSAGES_UI_CAP` (50) messages for the selected teammate. Older messages
are on disk at `~/.mammoth/sessions/{team_name}/{agent_id}.jsonl`.

---

## Notification Deltas

To avoid spamming the leader with every tool call, sub-agents only send a notification when they
cross a progress threshold:

```rust
// apps/mammoth/crates/runtime/src/swarm/notifications.rs
const TOOL_DELTA_THRESHOLD: u32 = 5;   // notify after every 5 tool calls
const TOKEN_DELTA_THRESHOLD: u32 = 500; // notify after every 500 tokens

pub fn should_notify(task: &InProcessTeammateTaskState, current_tool_count: u32, current_token_count: u32) -> bool {
    current_tool_count - task.last_reported_tool_count >= TOOL_DELTA_THRESHOLD
        || current_token_count - task.last_reported_token_count >= TOKEN_DELTA_THRESHOLD
}
```

---

## File Locations

| Path | Purpose |
|------|---------|
| `~/.mammoth/teams/{name}.json` | Team file (members, lead, timestamps) |
| `~/.mammoth/tasks/{list_id}/` | Task list directory for a team |
| `~/.mammoth/mailboxes/{team}/{agent}.jsonl` | Inbox per agent |
| `~/.mammoth/sessions/{team}/{agent_id}.jsonl` | Per-agent conversation transcript |

---

## Implementation Checklist (v0.4.0)

- [ ] `apps/mammoth/crates/runtime/src/tasks/mod.rs` — TaskState enum
- [ ] `apps/mammoth/crates/runtime/src/tasks/teammate.rs` — InProcessTeammateTaskState, TeammateIdentity, TEAMMATE_MESSAGES_UI_CAP
- [ ] `apps/mammoth/crates/runtime/src/swarm/team_file.rs` — TeamFile, read/write helpers
- [ ] `apps/mammoth/crates/runtime/src/swarm/mailbox.rs` — write_to_mailbox, read_mailbox
- [ ] `apps/mammoth/crates/runtime/src/swarm/presets.rs` — TeamPreset, builtin_presets()
- [ ] `apps/mammoth/crates/runtime/src/swarm/notifications.rs` — delta thresholds
- [ ] `apps/mammoth/crates/tools/src/team_create.rs` — call_team_create()
- [ ] `apps/mammoth/crates/tools/src/team_delete.rs` — call_team_delete()
- [ ] `apps/mammoth/crates/tools/src/agent.rs` — call_agent(), run_in_process_teammate()
- [ ] `apps/mammoth/crates/tools/src/send_message.rs` — call_send_message(), broadcast support
- [ ] `apps/mammoth/crates/tools/src/task_create.rs` — task CRUD tools
- [ ] `apps/mammoth/crates/mammoth-cli/src/tui/agent_panel.rs` — agent panel widget
- [ ] `apps/mammoth/crates/mammoth-cli/src/tui/teammate_transcript.rs` — zoomed transcript
- [ ] Coordinator mode flag + system prompt injection
- [ ] Team preset definitions + `/team <preset>` slash command
