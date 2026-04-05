# Plan Mode and Worktree Isolation Reference

**Mammoth v0.3.0 — Phase 3 implementation target**

This document is the authoritative reference for Mammoth's plan mode and worktree isolation system. It covers the full lifecycle of `EnterPlanMode`, `ExitPlanMode`, `EnterWorktree`, and `ExitWorktree` — including input/output schemas, plan file paths, CWD switching, session state mutations, and fail-closed safety behavior. An engineer with zero codebase context should be able to implement from this document.

---

## Table of Contents

1. [Overview](#overview)
2. [Plan Mode Lifecycle](#plan-mode-lifecycle)
3. [EnterPlanMode Tool](#enterplanmode-tool)
4. [ExitPlanMode Tool (V2)](#exitplanmode-tool-v2)
5. [Plan File Paths](#plan-file-paths)
6. [Worktree Isolation Overview](#worktree-isolation-overview)
7. [EnterWorktree Tool](#enterworktree-tool)
8. [ExitWorktree Tool](#exitworktree-tool)
9. [Worktree Safety: Fail-Closed Logic](#worktree-safety-fail-closed-logic)
10. [Session State Mutations](#session-state-mutations)
11. [Multi-Agent Plan Approval](#multi-agent-plan-approval)
12. [Channel Mode Restrictions](#channel-mode-restrictions)
13. [Implementation Targets](#implementation-targets)
14. [Implementation Status](#implementation-status)

---

## Overview

**Plan mode** is a read-only exploration phase that forces `PermissionMode::ReadOnly` for the duration of design. The model cannot write files, run bash, or cause side effects. When exploration is complete, `ExitPlanMode` presents the plan to the user for approval before restoring the prior permission mode.

**Worktree isolation** creates a git worktree — an independent working tree branched from the current HEAD — and switches the session's CWD into it. This isolates experimental work from the main branch without leaving the session. `ExitWorktree` returns to the original directory, with an option to keep or remove the worktree.

Both systems share a session state pattern: they record the prior state before transitioning, and restore it on exit. Both are fail-closed: if state cannot be determined (e.g. git command fails), the destructive path is blocked.

---

## Plan Mode Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SESSION START                               │
│   active_mode = config.permissionMode (default: WorkspaceWrite)    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
            [Model decides to plan]
                     │
                     ▼
         EnterPlanMode.call()
           - store prePlanMode = active_mode
           - active_mode = ReadOnly
           - emit system prompt: "DO NOT write files"
                     │
                     ▼
         [Model explores codebase in ReadOnly mode]
           - read_file ✓
           - grep ✓
           - glob ✓
           - web_search ✓
           - write_file ✗ (hard deny)
           - bash ✗ (hard deny)
                     │
                     ▼
         Model writes plan to disk at planFilePath
         (using write_file while in ReadOnly mode — blocked!)
         ┌─────────────────────────────────────────────────────┐
         │ Note: The plan is written by ExitPlanMode, not by   │
         │ the model directly. The model passes plan content   │
         │ in the ExitPlanMode input (via normalizeToolInput).  │
         └─────────────────────────────────────────────────────┘
                     │
                     ▼
         ExitPlanMode.call(allowedPrompts)
           - read plan from disk (getPlan(agentId))
           - if non-teammate: show approval dialog to user
           - if teammate: send plan_approval_request to leader mailbox
                     │
              ┌──────┴──────┐
              │             │
           Approved       Denied
              │             │
              ▼             ▼
         restore         model stays
         active_mode     in plan mode
         = prePlanMode
         setHasExitedPlanMode(true)
                     │
                     ▼
         [Model implements plan in restored mode]
```

---

## EnterPlanMode Tool

**Tool name:** `EnterPlanMode` (constant: `ENTER_PLAN_MODE_TOOL_NAME`)

**Reference:** `apps/claw-code-ref/src/tools/EnterPlanModeTool/EnterPlanModeTool.ts`

**Mammoth implementation target:** `apps/mammoth/crates/tools/src/plan_mode.rs` (new file)

### Input Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

No parameters. The tool takes no input.

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "message": {
      "type": "string",
      "description": "Confirmation that plan mode was entered"
    }
  },
  "required": ["message"]
}
```

### Behavior

1. **Guard:** If called from within an agent context (`agentId` is set), throw an error: `"EnterPlanMode tool cannot be used in agent contexts"`.
2. **State transition:** Set `active_mode = ReadOnly`; store `prePlanMode = prior_active_mode`.
3. **Return:** `{ message: "Entered plan mode. You should now focus on exploring the codebase and designing an implementation approach." }`
4. **System prompt injection:** The tool result is mapped to a `tool_result` block with full plan mode instructions (see below).

### Tool Result → System Prompt Attachment

The `mapToolResultToToolResultBlockParam` produces the instructions sent back to the model as part of the `tool_result` content:

```
Entered plan mode. You should now focus on exploring the codebase and
designing an implementation approach.

In plan mode, you should:
1. Thoroughly explore the codebase to understand existing patterns
2. Identify similar features and architectural approaches
3. Consider multiple approaches and their trade-offs
4. Use AskUserQuestion if you need to clarify the approach
5. Design a concrete implementation strategy
6. When ready, use ExitPlanMode to present your plan for approval

Remember: DO NOT write or edit any files yet. This is a read-only
exploration and planning phase.
```

### Properties

| Property | Value |
|----------|-------|
| `shouldDefer` | `true` — shown in the deferred tool list |
| `isReadOnly` | `true` |
| `isConcurrencySafe` | `true` |
| `isEnabled()` | `false` when `--channels` is active (see [Channel Mode Restrictions](#channel-mode-restrictions)) |

### Rust Implementation

```rust
// apps/mammoth/crates/tools/src/plan_mode.rs (new)

pub struct EnterPlanModeTool;

impl Tool for EnterPlanModeTool {
    fn name(&self) -> &'static str { "EnterPlanMode" }

    fn is_read_only(&self) -> bool { true }

    fn call(&self, _input: JsonValue, ctx: &mut ToolContext) -> ToolResult {
        // Guard: no agent contexts
        if ctx.agent_id.is_some() {
            return Err(ToolError::InvalidInput(
                "EnterPlanMode tool cannot be used in agent contexts".into()
            ));
        }

        // Transition: store prior mode, force ReadOnly
        let prior_mode = ctx.session.permission_mode();
        ctx.session.set_pre_plan_mode(prior_mode);
        ctx.session.set_permission_mode(PermissionMode::ReadOnly);

        Ok(json!({
            "message": "Entered plan mode. You should now focus on exploring the \
                        codebase and designing an implementation approach."
        }))
    }
}
```

---

## ExitPlanMode Tool (V2)

**Tool name:** `ExitPlanModeV2` (constant: `EXIT_PLAN_MODE_V2_TOOL_NAME`)

**Reference:** `apps/claw-code-ref/src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`

**Mammoth implementation target:** `apps/mammoth/crates/tools/src/plan_mode.rs` (new file)

### Input Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "allowedPrompts": {
      "type": "array",
      "description": "Prompt-based permissions needed to implement the plan.",
      "items": {
        "type": "object",
        "properties": {
          "tool": {
            "type": "string",
            "enum": ["Bash"],
            "description": "The tool this prompt applies to"
          },
          "prompt": {
            "type": "string",
            "description": "Semantic description, e.g. 'run tests', 'install dependencies'"
          }
        },
        "required": ["tool", "prompt"]
      }
    }
  },
  "additionalProperties": true
}
```

The schema uses `passthrough()` — additional fields (e.g. `plan`, `planFilePath` injected by the SDK) are accepted without error.

**Internal SDK fields (injected by normalizeToolInput, not set by the model):**

| Field | Type | Description |
|-------|------|-------------|
| `plan` | string (optional) | Plan content injected from disk read |
| `planFilePath` | string (optional) | Path to the plan file on disk |

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "plan": {
      "type": ["string", "null"],
      "description": "The plan that was presented to the user"
    },
    "isAgent": { "type": "boolean" },
    "filePath": {
      "type": "string",
      "description": "The file path where the plan was saved"
    },
    "hasTaskTool": {
      "type": "boolean",
      "description": "Whether the Agent tool is available"
    },
    "planWasEdited": {
      "type": "boolean",
      "description": "True if user edited the plan before approving"
    },
    "awaitingLeaderApproval": {
      "type": "boolean",
      "description": "True when teammate sent approval request to team leader"
    },
    "requestId": {
      "type": "string",
      "description": "Unique identifier for the plan approval request"
    }
  },
  "required": ["plan", "isAgent"]
}
```

### Behavior

1. **Validation:** If not in plan mode (`active_mode != ReadOnly`), return error `"You are not in plan mode."`.
2. **Teammate path:** If the caller is a teammate with `isPlanModeRequired()`:
   - Read plan from disk via `getPlanFilePath(agentId)`.
   - Generate `requestId` (format: `plan_approval_{agentName}_{teamName}_{timestamp}`).
   - Write `plan_approval_request` message to leader mailbox.
   - Set agent task state to `awaitingPlanApproval = true`.
   - Return `{ plan, isAgent: true, filePath, awaitingLeaderApproval: true, requestId }`.
3. **User path (non-teammate):**
   - Show approval dialog to user (TUI: inline widget; Web: modal; Extension: popup).
   - If user edits plan in dialog: persist edited plan to `filePath` on disk.
   - If approved: restore `active_mode = prePlanMode`; set `hasExitedPlanMode = true`.
   - Return `{ plan, isAgent: false, filePath, planWasEdited }`.

### Properties

| Property | Value |
|----------|-------|
| `shouldDefer` | `true` |
| `isReadOnly` | `false` (writes plan to disk) |
| `isConcurrencySafe` | `true` |
| `requiresUserInteraction` | `true` for non-teammates |
| `isEnabled()` | `false` when `--channels` active |

### Tool Result Content

**Normal approval (non-agent):**
```
User has approved your plan. You can now start coding.

Your plan has been saved to: ~/.mammoth/sessions/<session_id>/plans/<slug>.md
You can refer back to it if needed during implementation.

[If hasTaskTool]: If this plan can be broken down into multiple independent tasks,
consider using the team_create tool to create a team and parallelize the work.

## Approved Plan [or "Approved Plan (edited by user)"]:
<plan content>
```

**Teammate awaiting approval:**
```
Your plan has been submitted to the team lead for approval.

Plan file: <filePath>

What happens next:
1. Wait for the team lead to review your plan
2. You will receive a message in your inbox with approval/rejection
3. If approved, you can proceed with implementation
4. If rejected, refine your plan based on the feedback

Important: Do NOT proceed until you receive approval.

Request ID: <requestId>
```

---

## Plan File Paths

Plans are stored as Markdown files on disk. The path structure is:

```
~/.mammoth/sessions/<session_id>/plans/<slug>.md
```

### Path Resolution Logic

```rust
// Rust implementation target:
fn get_plan_file_path(session_id: &str, agent_id: Option<&str>) -> PathBuf {
    let base = PathBuf::from(env::var("HOME").unwrap_or_default())
        .join(".mammoth")
        .join("sessions")
        .join(session_id)
        .join("plans");

    let slug = get_plan_slug(agent_id);  // derived from session context
    base.join(format!("{slug}.md"))
}
```

### Plan Slug

The slug is derived from:
1. The agent name (for sub-agent plans)
2. The plan name passed to `ExitPlanMode` (if provided)
3. A sanitized version of the session context

Slug validation rules (from `validateWorktreeSlug`):
- Each `/`-separated segment: letters, digits, `.`, `_`, `-` only
- Max 64 characters total

### Plan File Format

The plan file is plain Markdown. There is no required schema for the content — the model writes whatever plan it devised during the exploration phase. The file is read back by `ExitPlanMode` and shown to the user for approval.

Example:

```markdown
# Refactor: Extract authentication middleware

## Approach
Replace inline auth checks with a middleware layer that runs before route handlers.

## Steps
1. Create `src/middleware/auth.ts`
2. Move JWT validation from `src/routes/api.ts:45-72`
3. Register middleware in `src/app.ts`
4. Update tests in `src/__tests__/routes/api.test.ts`

## Risks
- Breaking change for any route that currently bypasses auth check
- Need to verify `express.Router` middleware ordering

## Allowed shell commands
- `npm test` (run test suite)
- `npm run lint` (check code style)
```

---

## Worktree Isolation Overview

Worktrees let the model work in an isolated branch without leaving the session. The original directory is preserved in session state and restored when the worktree is exited.

**Key invariant:** `ExitWorktree` only operates on worktrees created by `EnterWorktree` in the *current session*. It will not touch worktrees from previous sessions or manually created with `git worktree add`.

---

## EnterWorktree Tool

**Tool name:** `EnterWorktree` (constant: `ENTER_WORKTREE_TOOL_NAME`)

**Reference:** `apps/claw-code-ref/src/tools/EnterWorktreeTool/EnterWorktreeTool.ts`

**Mammoth implementation target:** `apps/mammoth/crates/tools/src/worktree.rs` (new file)

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Optional name for the worktree. Segments separated by '/' may contain only letters, digits, '.', '_', '-'. Max 64 chars total. Random name generated if not provided."
    }
  },
  "additionalProperties": false
}
```

### Slug Validation Rules

```
- Max total length: 64 characters
- Allowed chars per segment: [a-zA-Z0-9._-]
- Segments separated by "/"
- No empty segments
- No leading/trailing "/"
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "worktreePath": { "type": "string" },
    "worktreeBranch": { "type": "string" },
    "message": { "type": "string" }
  },
  "required": ["worktreePath", "message"]
}
```

### Behavior

1. **Guard:** If already in a worktree session (`getCurrentWorktreeSession() != null`), throw `"Already in a worktree session"`.
2. **Resolve main repo root:** If CWD is inside a worktree, `chdir` to main repo root before creating a new worktree.
3. **Generate slug:** Use `input.name` if provided, else derive from the current plan slug.
4. **Create worktree:** Call `createWorktreeForSession(session_id, slug)`. This runs:
   ```bash
   git worktree add -b mammoth/<slug> ../<repo>-worktrees/<slug>
   ```
5. **Switch CWD:** `process.chdir(worktreePath)` and update session `cwd`.
6. **Save state:** Persist `worktreeSession` to session storage (includes `originalCwd`, `worktreePath`, `worktreeBranch`, `originalHeadCommit`).
7. **Clear caches:** Clear system prompt sections and memory file caches (they depend on CWD).

### Session State After EnterWorktree

```rust
pub struct WorktreeSession {
    pub original_cwd:          PathBuf,
    pub worktree_path:         PathBuf,
    pub worktree_branch:       Option<String>,
    pub original_head_commit:  Option<String>,   // baseline for commit counting
    pub tmux_session_name:     Option<String>,   // if tmux isolation used
}
```

### Tool Result Content

```
Created worktree at /Users/me/project-worktrees/my-feature on branch mammoth/my-feature.
The session is now working in the worktree. Use ExitWorktree to leave mid-session,
or exit the session to be prompted.
```

### Rust Implementation Sketch

```rust
// apps/mammoth/crates/tools/src/worktree.rs (new)
pub struct EnterWorktreeTool;

impl Tool for EnterWorktreeTool {
    fn name(&self) -> &'static str { "EnterWorktree" }

    fn call(&self, input: JsonValue, ctx: &mut ToolContext) -> ToolResult {
        // Guard: no nested worktrees
        if ctx.session.current_worktree().is_some() {
            return Err(ToolError::InvalidInput("Already in a worktree session".into()));
        }

        let slug = input["name"].as_str()
            .map(|s| s.to_string())
            .unwrap_or_else(|| ctx.session.plan_slug());

        validate_worktree_slug(&slug)?;

        // Resolve main repo root
        let main_root = find_canonical_git_root(&ctx.session.cwd());
        if main_root != ctx.session.cwd() {
            ctx.session.set_cwd(main_root.clone());
        }

        // Create the worktree
        let worktree_session = create_worktree_for_session(
            ctx.session.id(),
            &slug,
            &main_root,
        )?;

        // Switch CWD
        ctx.session.set_cwd(worktree_session.worktree_path.clone());
        ctx.session.save_worktree_state(worktree_session.clone());
        ctx.session.clear_system_prompt_sections();
        ctx.session.clear_memory_file_caches();

        let branch_info = worktree_session.worktree_branch
            .as_deref()
            .map(|b| format!(" on branch {b}"))
            .unwrap_or_default();

        Ok(json!({
            "worktreePath": worktree_session.worktree_path,
            "worktreeBranch": worktree_session.worktree_branch,
            "message": format!(
                "Created worktree at {}{branch_info}. The session is now working in \
                 the worktree. Use ExitWorktree to leave mid-session, or exit the session \
                 to be prompted.",
                worktree_session.worktree_path.display()
            )
        }))
    }
}
```

---

## ExitWorktree Tool

**Tool name:** `ExitWorktree` (constant: `EXIT_WORKTREE_TOOL_NAME`)

**Reference:** `apps/claw-code-ref/src/tools/ExitWorktreeTool/ExitWorktreeTool.ts`

**Mammoth implementation target:** `apps/mammoth/crates/tools/src/worktree.rs`

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["keep", "remove"],
      "description": "'keep' leaves the worktree and branch on disk; 'remove' deletes both."
    },
    "discard_changes": {
      "type": "boolean",
      "description": "Required true when action is 'remove' and the worktree has uncommitted files or unmerged commits. Tool refuses otherwise."
    }
  },
  "required": ["action"],
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "action":          { "type": "string", "enum": ["keep", "remove"] },
    "originalCwd":     { "type": "string" },
    "worktreePath":    { "type": "string" },
    "worktreeBranch":  { "type": "string" },
    "tmuxSessionName": { "type": "string" },
    "discardedFiles":  { "type": "integer" },
    "discardedCommits":{ "type": "integer" },
    "message":         { "type": "string" }
  },
  "required": ["action", "originalCwd", "worktreePath", "message"]
}
```

### Behavior

#### Validation phase (before execution)

1. **Session guard:** `getCurrentWorktreeSession()` must be non-null. Error message: `"No-op: there is no active EnterWorktree session to exit."` (error code 1)

2. **Remove safety check:** If `action == "remove"` and `discard_changes != true`:
   - Run `git -C <worktreePath> status --porcelain` → count non-empty lines as `changedFiles`
   - Run `git -C <worktreePath> rev-list --count <originalHeadCommit>..HEAD` → count as `commits`
   - If either command fails (`exit != 0`) or `originalHeadCommit` is not set: return error (error code 3):
     ```
     Could not verify worktree state at <path>. Refusing to remove without explicit
     confirmation. Re-invoke with discard_changes: true — or use action: "keep".
     ```
   - If `changedFiles > 0` or `commits > 0`: return error (error code 2):
     ```
     Worktree has N uncommitted files and M commits on <branch>.
     Removing will discard this work permanently. Confirm with the user,
     then re-invoke with discard_changes: true — or use action: "keep".
     ```

#### Execution phase

**`action == "keep"`:**
1. Call `keepWorktree()` — nulls out `currentWorktreeSession` but leaves disk intact.
2. Call `restoreSessionToOriginalCwd(originalCwd, projectRootIsWorktree)`.
3. Return with message: `"Exited worktree. Your work is preserved at <path> on branch <branch>. Session is now back in <originalCwd>."`

**`action == "remove"`:**
1. If tmux session exists: kill it.
2. Call `cleanupWorktree()` — removes git worktree and branch, nulls session state.
3. Call `restoreSessionToOriginalCwd(originalCwd, projectRootIsWorktree)`.
4. Return with message including discard summary.

### restoreSessionToOriginalCwd Logic

```rust
fn restore_session_to_original_cwd(
    session: &mut Session,
    original_cwd: &Path,
    project_root_is_worktree: bool,
) {
    session.set_cwd(original_cwd.to_path_buf());
    session.set_original_cwd(original_cwd.to_path_buf());

    // Only restore projectRoot if --worktree startup had changed it.
    // Mid-session EnterWorktree does NOT change projectRoot.
    if project_root_is_worktree {
        session.set_project_root(original_cwd.to_path_buf());
        session.update_hooks_config_snapshot();  // re-read hooks from restored dir
    }

    session.save_worktree_state(None);
    session.clear_system_prompt_sections();
    session.clear_memory_file_caches();
    session.plans_directory_cache_clear();
}
```

---

## Worktree Safety: Fail-Closed Logic

The fail-closed contract for `ExitWorktree` with `action: "remove"` is:

```
countWorktreeChanges(path, originalHeadCommit) -> Option<ChangeSummary>

Returns None when:
  1. `git status` exits non-zero (lock file, corrupt index, bad ref)
  2. `git rev-list` exits non-zero
  3. `originalHeadCommit` is None but `git status` succeeded
     → git repo confirmed, but no baseline → cannot count commits → fail-closed

Returns Some({changedFiles, commits}) when:
  - Both commands succeed
  - originalHeadCommit is set

Safety rule: if None → refuse to remove without discard_changes: true
```

This is explicitly designed so that a hook-based worktree (where `originalHeadCommit` is never set) cannot be silently destroyed.

---

## Session State Mutations

Summary of all session state changes made by the four tools:

### EnterPlanMode

| State field | Before | After |
|-------------|--------|-------|
| `active_permission_mode` | `WorkspaceWrite` (or config value) | `ReadOnly` |
| `pre_plan_mode` | `None` | `Some(prior_mode)` |

### ExitPlanMode (approved)

| State field | Before | After |
|-------------|--------|-------|
| `active_permission_mode` | `ReadOnly` | `pre_plan_mode` value |
| `pre_plan_mode` | `Some(prior_mode)` | `None` |
| `has_exited_plan_mode` | `false` | `true` |
| plan file | may not exist | written to `planFilePath` |

### EnterWorktree

| State field | Before | After |
|-------------|--------|-------|
| `cwd` | `/path/to/project` | `/path/to/project-worktrees/<slug>` |
| `original_cwd` | `/path/to/project` | `/path/to/project-worktrees/<slug>` |
| `current_worktree_session` | `None` | `Some(WorktreeSession{...})` |
| system prompt sections cache | populated | cleared |
| memory file caches | populated | cleared |
| plans directory cache | populated | cleared |

### ExitWorktree

| State field | Before | After |
|-------------|--------|-------|
| `cwd` | worktree path | `originalCwd` |
| `original_cwd` | worktree path | `originalCwd` |
| `project_root` | (worktree if `--worktree` startup) | `originalCwd` (if projectRootIsWorktree) |
| `current_worktree_session` | `Some(...)` | `None` |
| system prompt sections cache | populated | cleared |
| memory file caches | populated | cleared |
| plans directory cache | populated | cleared |

---

## Multi-Agent Plan Approval

When a teammate agent (spawned via `team_create`) exits plan mode, the approval goes through the team leader rather than the TUI.

### Approval Request Format

```json
{
  "type": "plan_approval_request",
  "from": "<agent_name>",
  "timestamp": "2026-04-05T12:34:56.000Z",
  "planFilePath": "~/.mammoth/sessions/<session_id>/plans/<slug>.md",
  "planContent": "<full plan markdown text>",
  "requestId": "plan_approval_<agentName>_<teamName>_<timestamp>"
}
```

This JSON is written to the team leader's mailbox:

```
~/.mammoth/teams/<teamName>/mailbox/team-lead.json
```

### Leader Approval Flow

1. Leader reads `plan_approval_request` from mailbox.
2. Leader renders plan in TUI approval panel (planned: `apps/mammoth/crates/mammoth-cli/src/agent_panel.rs`).
3. Leader approves or rejects.
4. Leader writes `plan_approval_response` to agent's mailbox:
   ```json
   {
     "type": "plan_approval_response",
     "approved": true,
     "feedback": null,
     "requestId": "<original request id>"
   }
   ```
5. Agent polls mailbox, reads response, exits plan mode if approved.

### Task State: awaitingPlanApproval

When a teammate sends a plan approval request, its `InProcessTeammateTaskState` transitions to include `awaitingPlanApproval: true`. The agent panel in the TUI displays this state as a waiting indicator:

```
┌─ agent: feature-builder ───────────────────────────────────────────────────┐
│ Status: Awaiting plan approval from team leader                             │
│ Plan:   ~/.mammoth/sessions/.../plans/refactor-auth.md                     │
│ Request ID: plan_approval_feature-builder_default_1743834896               │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Channel Mode Restrictions

When `--channels` is active (Telegram, Discord, Slack integrations):

- `EnterPlanMode` is **disabled** (`isEnabled()` returns `false`)
- `ExitPlanMode` is **disabled** (`isEnabled()` returns `false`)

**Rationale:** The plan approval dialog requires terminal interaction (TUI rendering of the approval widget or web modal). In channel mode, the user is interacting via a chat interface that cannot host the approval dialog. Disabling both ensures the model cannot enter a plan mode it can never exit.

**Future work (Phase 4+):** Route plan approval through the channel interface (inline keyboard buttons for Telegram, interactive components for Slack, etc.).

---

## Implementation Targets

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/mammoth/crates/tools/src/plan_mode.rs` | `EnterPlanModeTool`, `ExitPlanModeTool` Rust implementations |
| `apps/mammoth/crates/tools/src/worktree.rs` | `EnterWorktreeTool`, `ExitWorktreeTool` Rust implementations |
| `apps/mammoth/crates/runtime/src/plan.rs` | Plan file path resolution, plan read/write, slug generation |
| `apps/mammoth/crates/runtime/src/worktree.rs` | Git worktree creation, `WorktreeSession`, `countWorktreeChanges` |

### Existing Files to Modify

| File | Change |
|------|--------|
| `apps/mammoth/crates/tools/src/lib.rs` | Register `EnterPlanMode`, `ExitPlanMode`, `EnterWorktree`, `ExitWorktree` in `mvp_tool_specs()` |
| `apps/mammoth/crates/runtime/src/session.rs` | Add `pre_plan_mode: Option<PermissionMode>`, `current_worktree_session: Option<WorktreeSession>`, `has_exited_plan_mode: bool` |
| `apps/mammoth/crates/mammoth-cli/src/app.rs` | Wire TUI approval dialog for `ExitPlanMode` |
| `apps/mammoth/crates/server/src/lib.rs` | Wire WebSocket approval handler for web UI |

### Session Struct Additions

```rust
// apps/mammoth/crates/runtime/src/session.rs — additions:
pub struct Session {
    // ... existing fields ...

    /// Permission mode stored before entering plan mode; restored on exit.
    pub pre_plan_mode: Option<PermissionMode>,

    /// True once ExitPlanMode has been successfully called in this session.
    pub has_exited_plan_mode: bool,

    /// Active worktree created by EnterWorktree in this session.
    /// None if not in a worktree, or if worktree was created outside this session.
    pub current_worktree_session: Option<WorktreeSession>,
}
```

---

## Implementation Status

| Component | Status | Target File |
|-----------|--------|------------|
| `EnterPlanModeTool` Rust struct | **Not started** | `tools/src/plan_mode.rs` |
| `ExitPlanModeTool` Rust struct | **Not started** | `tools/src/plan_mode.rs` |
| `EnterWorktreeTool` Rust struct | **Not started** | `tools/src/worktree.rs` |
| `ExitWorktreeTool` Rust struct | **Not started** | `tools/src/worktree.rs` |
| Plan file path resolution | **Not started** | `runtime/src/plan.rs` |
| Slug validation | **Not started** | `runtime/src/plan.rs` |
| Git worktree creation | **Not started** | `runtime/src/worktree.rs` |
| `WorktreeSession` struct | **Not started** | `runtime/src/worktree.rs` |
| `countWorktreeChanges` | **Not started** | `runtime/src/worktree.rs` |
| Session fields: `pre_plan_mode` etc. | **Not started** | `runtime/src/session.rs` |
| TUI approval dialog | **Not started** | `mammoth-cli/src/approval.rs` |
| Web approval WebSocket event | **Not started** | `server/src/lib.rs` |
| Channel mode `isEnabled()` gate | **Not started** | `tools/src/plan_mode.rs` |
| Multi-agent mailbox integration | **Not started** | `runtime/src/teammate_mailbox.rs` |
| Tool registration in `mvp_tool_specs()` | **Not started** | `tools/src/lib.rs` |

---

*Reference implementations: `apps/claw-code-ref/src/tools/EnterPlanModeTool/`, `ExitPlanModeTool/`, `EnterWorktreeTool/`, `ExitWorktreeTool/`*

*Source types: `apps/mammoth/crates/runtime/src/permissions.rs`, `apps/mammoth/crates/runtime/src/session.rs`*
