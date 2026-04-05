# Permissions Reference

**Mammoth v0.3.0 — Phase 3 implementation target**

This document is the authoritative reference for Mammoth's permission system. It covers the five permission modes, policy evaluation logic, config-file mapping, hook integration, AICP governance bridge, and the Rust implementation targets. An engineer with zero codebase context should be able to implement from this document.

---

## Table of Contents

1. [Overview](#overview)
2. [PermissionMode Enum](#permissionmode-enum)
3. [PermissionPolicy](#permissionpolicy)
4. [PermissionRequest and PermissionOutcome](#permissionrequest-and-permissionoutcome)
5. [PermissionPrompter Trait](#permissionprompter-trait)
6. [Authorization Logic](#authorization-logic)
7. [ResolvedPermissionMode and Config Mapping](#resolvedpermissionmode-and-config-mapping)
8. [Config File Keys](#config-file-keys)
9. [Per-Tool Permission Requirements](#per-tool-permission-requirements)
10. [Hook-Based Permission Override](#hook-based-permission-override)
11. [AICP Governance Integration](#aicp-governance-integration)
12. [Trust Tiers](#trust-tiers)
13. [Plan Mode Permission Lifecycle](#plan-mode-permission-lifecycle)
14. [Channel Permission Restrictions](#channel-permission-restrictions)
15. [Permission Decision Flow Diagram](#permission-decision-flow-diagram)
16. [Implementation Status](#implementation-status)

---

## Overview

Mammoth uses a **five-level permission ladder** to control which tools an agent or user can invoke. Permission evaluation occurs at the point of tool dispatch, before any side effects run. The system is fail-closed: any ambiguity denies.

The core types live at:

```
apps/mammoth/crates/runtime/src/permissions.rs
```

The config parsing that maps JSON settings to permission mode lives at:

```
apps/mammoth/crates/runtime/src/config.rs  (parse_optional_permission_mode, line 658)
```

---

## PermissionMode Enum

```rust
// apps/mammoth/crates/runtime/src/permissions.rs:4-10
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum PermissionMode {
    ReadOnly,
    WorkspaceWrite,
    DangerFullAccess,
    Prompt,
    Allow,
}
```

The enum derives `PartialOrd` and `Ord`. The ordering is:

```
ReadOnly < WorkspaceWrite < DangerFullAccess < Prompt < Allow
```

This ordering is used by the authorization check: `current_mode >= required_mode` grants access.

### Mode Meanings

| Mode | String | Meaning |
|------|--------|---------|
| `ReadOnly` | `"read-only"` | Only read tools are permitted. Write tools, bash, and side-effect tools are blocked. This is the mode used during plan mode exploration. |
| `WorkspaceWrite` | `"workspace-write"` | File reads and writes within the workspace are permitted. Bash and other `DangerFullAccess` tools still require escalation via the prompter. |
| `DangerFullAccess` | `"danger-full-access"` | All tools permitted without interruption. Bash, shell commands, and destructive operations run without approval prompts. |
| `Prompt` | `"prompt"` | Any tool that requires higher than current mode will trigger the `PermissionPrompter`. Nothing is silently denied or silently allowed. |
| `Allow` | `"allow"` | Unconditional allow — used by `--dangerously-skip-permissions` flag and bypassPermissions internal test mode. No check is ever performed. |

### as_str()

```rust
impl PermissionMode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ReadOnly       => "read-only",
            Self::WorkspaceWrite => "workspace-write",
            Self::DangerFullAccess => "danger-full-access",
            Self::Prompt         => "prompt",
            Self::Allow          => "allow",
        }
    }
}
```

---

## PermissionPolicy

`PermissionPolicy` binds an active mode to a per-tool requirement map. It is the primary runtime policy object passed to tool dispatch.

```rust
// apps/mammoth/crates/runtime/src/permissions.rs:49-53
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionPolicy {
    active_mode: PermissionMode,
    tool_requirements: BTreeMap<String, PermissionMode>,
}
```

### Construction

```rust
// Build a policy with WorkspaceWrite as the active mode:
let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
    .with_tool_requirement("read_file",   PermissionMode::ReadOnly)
    .with_tool_requirement("write_file",  PermissionMode::WorkspaceWrite)
    .with_tool_requirement("bash",        PermissionMode::DangerFullAccess)
    .with_tool_requirement("web_fetch",   PermissionMode::WorkspaceWrite);
```

### Default Requirement

If a tool name is not in `tool_requirements`, `required_mode_for()` returns `DangerFullAccess`:

```rust
// permissions.rs:81-86
pub fn required_mode_for(&self, tool_name: &str) -> PermissionMode {
    self.tool_requirements
        .get(tool_name)
        .copied()
        .unwrap_or(PermissionMode::DangerFullAccess)
}
```

**Implication:** any tool not explicitly registered defaults to requiring `DangerFullAccess`. This is fail-secure: unknown tools cannot slip through a permissive default.

---

## PermissionRequest and PermissionOutcome

These are the data types that flow through authorization:

```rust
// permissions.rs:26-31
pub struct PermissionRequest {
    pub tool_name:    String,
    pub input:        String,        // raw JSON input string
    pub current_mode: PermissionMode,
    pub required_mode: PermissionMode,
}

// permissions.rs:44-47
pub enum PermissionOutcome {
    Allow,
    Deny { reason: String },
}
```

`PermissionPromptDecision` is the decision returned by a prompter:

```rust
pub enum PermissionPromptDecision {
    Allow,
    Deny { reason: String },
}
```

---

## PermissionPrompter Trait

The `PermissionPrompter` trait is the extension point for TUI, web, and channel approval UIs. The runtime calls `decide()` when the policy determines a prompt is needed.

```rust
// permissions.rs:39-41
pub trait PermissionPrompter {
    fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision;
}
```

### Implementation Targets

| Context | Implementation | Location (planned) |
|---------|---------------|-------------------|
| TUI interactive | `TuiPrompter` — renders inline approval widget in the message pane | `apps/mammoth/crates/mammoth-cli/src/approval.rs` |
| Web UI | `WebPrompter` — sends `permission_request` event over WebSocket, awaits response | `apps/mammoth/crates/server/src/approval.rs` |
| Chrome extension | `ExtensionPrompter` — sends approval request to extension content script | `apps/mammoth/extension/src/approval.ts` |
| AICP approval | `AicpPrompter` — submits approval request to AICP governance API, polls | `apps/mammoth/crates/runtime/src/aicp_approval.rs` |
| Headless / CI | `HeadlessPrompter` — always denies; logs the request | `apps/mammoth/crates/runtime/src/permissions.rs` |
| Test | `RecordingPrompter` — records decisions, configurable allow/deny | `apps/mammoth/crates/runtime/src/permissions.rs` (tests) |

### TUI Prompter Behavior

The TUI prompter will render inside the message pane:

```
┌─ Permission Request ─────────────────────────────────────────────────────────┐
│ Tool:    bash                                                                  │
│ Mode:    workspace-write → danger-full-access (escalation required)            │
│                                                                                │
│ Input:   {"command": "npm run build && git push origin main"}                  │
│                                                                                │
│  [y] Allow    [n] Deny    [a] Allow all (session)    [e] Edit before running  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Authorization Logic

The `authorize()` method is the single decision point. It must be called before every tool execution.

```rust
// permissions.rs:88-134
pub fn authorize(
    &self,
    tool_name: &str,
    input: &str,
    mut prompter: Option<&mut dyn PermissionPrompter>,
) -> PermissionOutcome {
    let current_mode = self.active_mode();
    let required_mode = self.required_mode_for(tool_name);

    // Fast path: Allow mode bypasses all checks
    // Fast path: current mode meets or exceeds required mode
    if current_mode == PermissionMode::Allow || current_mode >= required_mode {
        return PermissionOutcome::Allow;
    }

    let request = PermissionRequest { tool_name, input, current_mode, required_mode };

    // Prompt path #1: explicit Prompt mode
    // Prompt path #2: WorkspaceWrite trying to use DangerFullAccess tool
    if current_mode == PermissionMode::Prompt
    || (current_mode == PermissionMode::WorkspaceWrite
        && required_mode == PermissionMode::DangerFullAccess)
    {
        return match prompter.as_mut() {
            Some(p) => match p.decide(&request) {
                PermissionPromptDecision::Allow        => PermissionOutcome::Allow,
                PermissionPromptDecision::Deny {reason}=> PermissionOutcome::Deny {reason},
            },
            None => PermissionOutcome::Deny {
                reason: format!(
                    "tool '{}' requires approval to escalate from {} to {}",
                    tool_name, current_mode.as_str(), required_mode.as_str()
                ),
            },
        };
    }

    // Hard deny: mode does not meet requirement and no prompt path applies
    PermissionOutcome::Deny {
        reason: format!(
            "tool '{}' requires {} permission; current mode is {}",
            tool_name, required_mode.as_str(), current_mode.as_str()
        ),
    }
}
```

### Decision Table

| Active Mode | Required Mode | Prompter? | Outcome |
|-------------|---------------|-----------|---------|
| `Allow` | any | any | Allow |
| `ReadOnly` | `ReadOnly` | any | Allow |
| `WorkspaceWrite` | `ReadOnly` | any | Allow |
| `WorkspaceWrite` | `WorkspaceWrite` | any | Allow |
| `DangerFullAccess` | `DangerFullAccess` | any | Allow |
| `Prompt` | any | present | Prompter decides |
| `Prompt` | any | absent | Deny |
| `WorkspaceWrite` | `DangerFullAccess` | present | Prompter decides |
| `WorkspaceWrite` | `DangerFullAccess` | absent | Deny |
| `ReadOnly` | `WorkspaceWrite` | any | Deny (hard) |
| `ReadOnly` | `DangerFullAccess` | any | Deny (hard) |

**Key rule:** `ReadOnly` cannot escalate to `WorkspaceWrite` or above via the prompter. This is intentional: plan mode uses `ReadOnly` and the lock must be absolute.

---

## ResolvedPermissionMode and Config Mapping

Config files use a 3-value `ResolvedPermissionMode` (no `Prompt` or `Allow`). These are the user-visible modes:

```rust
// config.rs:19-23
pub enum ResolvedPermissionMode {
    ReadOnly,
    WorkspaceWrite,
    DangerFullAccess,
}
```

`Prompt` and `Allow` are session-level overrides set by CLI flags, not by config files.

### Config Key Aliases

`parse_permission_mode_label()` maps all accepted strings to the three resolved modes:

```rust
// config.rs:682-690
match mode {
    "default" | "plan" | "read-only"        => Ok(ResolvedPermissionMode::ReadOnly),
    "acceptEdits" | "auto" | "workspace-write" => Ok(ResolvedPermissionMode::WorkspaceWrite),
    "dontAsk" | "danger-full-access"         => Ok(ResolvedPermissionMode::DangerFullAccess),
    other => Err(ConfigError::Parse(...))
}
```

| Config value | Maps to |
|---|---|
| `"default"` | `ReadOnly` |
| `"plan"` | `ReadOnly` |
| `"read-only"` | `ReadOnly` |
| `"acceptEdits"` | `WorkspaceWrite` |
| `"auto"` | `WorkspaceWrite` |
| `"workspace-write"` | `WorkspaceWrite` |
| `"dontAsk"` | `DangerFullAccess` |
| `"danger-full-access"` | `DangerFullAccess` |

### Config Lookup Paths

Two config keys are checked, in this order:

1. `permissionMode` (top-level key, string)
2. `permissions.defaultMode` (nested key, string)

```json
// Option 1: top-level
{ "permissionMode": "acceptEdits" }

// Option 2: nested
{ "permissions": { "defaultMode": "workspace-write" } }
```

Both map to the same resolved mode. The top-level key takes precedence.

---

## Config File Keys

Full reference for all permission-related config keys:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `permissionMode` | string | `"default"` (ReadOnly) | Session-wide default permission mode |
| `permissions.defaultMode` | string | `"default"` | Alternate path for the same setting |
| `aicp.enabled` | bool | `false` | If true, route approval decisions through AICP governance |
| `aicp.trustTier` | string | `"2"` | Trust tier string passed to AICP policy engine |
| `aicp.url` | string | `"http://localhost:10003"` | AICP runtime base URL (overridden by `AICP_URL` env var) |
| `aicp.sessionId` | string | null | Bind to an existing AICP session for resumable governance |

### Environment Variable Override

```bash
# Override AICP URL without editing config files
AICP_URL=https://aicp.internal:10003 mammoth
```

---

## Per-Tool Permission Requirements

These are the canonical tool requirement assignments. They must be registered into `PermissionPolicy` at session startup.

### Built-in Tool Requirements

| Tool Name | Required Mode | Rationale |
|-----------|--------------|-----------|
| `read_file` | `ReadOnly` | Pure read, no side effects |
| `list_directory` | `ReadOnly` | Pure read |
| `glob` | `ReadOnly` | Pure read |
| `grep` | `ReadOnly` | Pure read |
| `web_search` | `ReadOnly` | Network read, no write |
| `web_fetch` | `WorkspaceWrite` | May follow redirects, some side effects |
| `write_file` | `WorkspaceWrite` | Filesystem write |
| `edit_file` | `WorkspaceWrite` | Filesystem write |
| `create_directory` | `WorkspaceWrite` | Filesystem mutation |
| `move_file` | `WorkspaceWrite` | Filesystem mutation |
| `delete_file` | `DangerFullAccess` | Irreversible |
| `bash` | `DangerFullAccess` | Arbitrary command execution |
| `task` | `WorkspaceWrite` | Sub-agent spawn (inherits parent mode) |
| `memory_read` | `ReadOnly` | Read only |
| `memory_write` | `WorkspaceWrite` | State mutation |
| `mcp_*` | `WorkspaceWrite` | Delegated; individual tools may escalate |
| `enter_plan_mode` | `ReadOnly` | Sets ReadOnly mode |
| `exit_plan_mode` | none (deferred) | Handled by plan mode lifecycle |
| `enter_worktree` | `WorkspaceWrite` | Creates git worktree |
| `exit_worktree` | `WorkspaceWrite` | Modifies git state |

### MCP Tool Requirements

MCP tools are registered at runtime. If no explicit requirement is set for an MCP tool, the default applies (`DangerFullAccess`). To set a custom requirement:

```rust
// At MCP tool registration time:
policy = policy.with_tool_requirement(
    format!("mcp_{server_name}__{tool_name}"),
    PermissionMode::WorkspaceWrite,
);
```

---

## Hook-Based Permission Override

Hooks can **deny** tool execution before the permission system sees it, and can **warn** without blocking. Hooks run before policy evaluation in the permission gate pipeline.

See full hook documentation at: `docs/guides/SLASH_COMMANDS.md` → hooks section, and the hooks source at `apps/mammoth/crates/runtime/src/hooks.rs`.

### Hook Exit Code Semantics

| Exit code | Outcome | Use case |
|-----------|---------|----------|
| `0` | Allow (hook message shown if stdout non-empty) | Normal approval |
| `2` | **Deny** — tool execution blocked | Policy enforcement |
| any other | Warn — tool still runs; message logged | Audit logging |
| signal | Warn — tool still runs | Process crash |

### Hook Payload (stdin JSON)

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name":       "bash",
  "tool_input":      { "command": "rm -rf /tmp/test" },
  "tool_input_json": "{\"command\":\"rm -rf /tmp/test\"}",
  "tool_output":     null,
  "tool_result_is_error": false
}
```

### Hook Environment Variables

| Variable | Value |
|----------|-------|
| `HOOK_EVENT` | `"PreToolUse"` or `"PostToolUse"` |
| `HOOK_TOOL_NAME` | Tool name string |
| `HOOK_TOOL_INPUT` | Raw JSON input string |
| `HOOK_TOOL_IS_ERROR` | `"1"` if tool returned error, `"0"` otherwise |
| `HOOK_TOOL_OUTPUT` | Tool output string (PostToolUse only) |

### Example: Hook that blocks `git push` in CI

```bash
#!/usr/bin/env bash
# .mammoth/hooks/pre-tool.sh
if [ "$HOOK_TOOL_NAME" = "bash" ]; then
  if echo "$HOOK_TOOL_INPUT" | grep -q '"git push"'; then
    echo "git push blocked: must use PR workflow"
    exit 2
  fi
fi
exit 0
```

Config registration:

```json
{
  "hooks": {
    "PreToolUse": [".mammoth/hooks/pre-tool.sh"]
  }
}
```

### Interaction with PermissionPolicy

The full gate pipeline at tool dispatch time is:

```
1. HookRunner.run_pre_tool_use()    → if denied, abort immediately
2. PermissionPolicy.authorize()     → if denied, surface error to model
3. Tool.call()                      → execute
4. HookRunner.run_post_tool_use()   → record/audit (non-blocking by default)
```

This means hooks can enforce stricter rules than the current `PermissionMode`. A hook can block `bash` even when the session is in `DangerFullAccess` mode.

---

## AICP Governance Integration

When `aicp.enabled = true`, the `AicpPrompter` replaces the default `TuiPrompter` for decisions that reach the prompt path. The AICP control plane handles risk scoring, approval workflows, and audit.

### AicpConfig

```rust
// config.rs:61-70
pub struct AicpConfig {
    pub url:        String,        // base URL, default "http://localhost:10003"
    pub enabled:    bool,          // must be true to activate
    pub trust_tier: String,        // "0"-"4", passed to policy engine
    pub session_id: Option<String>, // resume existing AICP session
}
```

### Trust Tiers

| Tier | Name | Behavior |
|------|------|----------|
| `"0"` | Anonymous | All non-read capabilities require approval |
| `"1"` | Authenticated | Workspace writes allowed; dangerous ops require approval |
| `"2"` | Verified (default) | Workspace writes + some dangerous ops allowed; high-risk requires approval |
| `"3"` | Trusted | Most ops allowed; only irreversible destructive ops require approval |
| `"4"` | Fully Autonomous | All ops allowed without approval prompts |

### AicpPrompter Flow (planned, Phase 3)

```
Tool dispatch
    → PermissionPolicy.authorize() → needs prompt
        → AicpPrompter.decide(request)
            → POST /api/capabilities/{name}/execute (policy evaluation)
                → if policy_result.effect == "allow" → PermissionOutcome::Allow
                → if policy_result.effect == "require_approval"
                    → POST /api/approvals
                    → poll GET /api/approvals/{id}
                    → if approved → PermissionOutcome::Allow
                    → if denied  → PermissionOutcome::Deny
                → if policy_result.effect == "deny" → PermissionOutcome::Deny
```

### Mapping Mammoth Modes to AICP Trust Tiers

| Mammoth Mode | Suggested AICP Trust Tier |
|---|---|
| `ReadOnly` | `"1"` |
| `WorkspaceWrite` | `"2"` |
| `DangerFullAccess` | `"3"` or `"4"` |
| `Prompt` | `"2"` (AICP decides per-request) |

### Config Example

```json
{
  "permissionMode": "workspace-write",
  "aicp": {
    "enabled": true,
    "url": "http://localhost:10003",
    "trustTier": "2",
    "sessionId": "sess_abc123"
  }
}
```

---

## Trust Tiers

Trust tiers are an AICP concept, separate from Mammoth's `PermissionMode`. They are passed to the AICP policy engine when `aicp.enabled = true`. Mammoth's built-in permission system does not interpret trust tier values; they are forwarded to AICP for policy evaluation.

### Resolving Effective Trust Tier

1. Config file `aicp.trustTier` (string `"0"` to `"4"`)
2. `AICP_TRUST_TIER` environment variable (planned)
3. Default: `"2"`

---

## Plan Mode Permission Lifecycle

Plan mode is a special session state where `PermissionMode` is forced to `ReadOnly` for the duration of exploration. The lifecycle:

```
Session start
    → active_mode = config.permission_mode OR WorkspaceWrite (default)

EnterPlanMode tool call
    → store prePlanMode = active_mode
    → active_mode = ReadOnly
    → model instructions: "DO NOT write files; exploration only"

[Agent explores codebase in ReadOnly mode]

ExitPlanMode tool call
    → user sees approval dialog (TUI) or plan sent to leader (agent)
    → if approved:
        → active_mode = prePlanMode (restored)
        → prePlanMode = None
        → setHasExitedPlanMode(true)
    → model instructions: "Plan approved. Begin implementation."
```

### ReadOnly Enforcement During Plan Mode

When `active_mode == ReadOnly`:

- `write_file` → hard deny (requires `WorkspaceWrite`)
- `edit_file` → hard deny
- `bash` → hard deny (requires `DangerFullAccess`)
- `read_file` → allow
- `grep` → allow
- `glob` → allow
- `web_search` → allow

The lock is absolute: `ReadOnly` cannot prompt-escalate. See [Decision Table](#decision-table).

---

## Channel Permission Restrictions

When `--channels` mode is active (Telegram, Discord, etc.), `EnterPlanMode` and `ExitPlanMode` are both disabled:

```typescript
// Reference: EnterPlanModeTool.ts:56-66
isEnabled() {
    if (getAllowedChannels().length > 0) {
        return false  // plan mode unavailable in channels
    }
    return true
}
```

**Rationale:** The `ExitPlanMode` approval dialog requires a terminal. Disabling entry prevents the model from entering a mode it cannot exit.

For channel-based sessions, permission prompts should be routed through the channel's message interface (future work, Phase 4+).

---

## Permission Decision Flow Diagram

```
Tool dispatch request
        │
        ▼
HookRunner.run_pre_tool_use(tool_name, input_json)
        │
        ├─ exit 2 ──► DENY (hook message to model)
        │
        ▼
PermissionPolicy.authorize(tool_name, input_json, prompter)
        │
        ├─ active_mode == Allow ──────────────────────────────► ALLOW
        │
        ├─ active_mode >= required_mode ─────────────────────► ALLOW
        │
        ├─ active_mode == Prompt ──────────────────────────────┐
        │                                                       │
        ├─ WorkspaceWrite && required == DangerFullAccess ──────┤
        │                                                       ▼
        │                                           prompter.decide(request)
        │                                                  │
        │                                    ┌─────────────┴──────────────┐
        │                                    ▼                            ▼
        │                                  Allow                        Deny
        │                                    │                            │
        │                                    ▼                            ▼
        │                                  ALLOW                        DENY
        │
        └─ (ReadOnly trying to escalate) ────────────────────► DENY (hard)

                            │ (Allow path)
                            ▼
                     Tool.call(input)
                            │
                            ▼
              HookRunner.run_post_tool_use(...)
                  (audit/warn only, non-blocking)
```

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| `PermissionMode` enum | **Done** | `runtime/src/permissions.rs:4` |
| `PermissionPolicy` struct | **Done** | `runtime/src/permissions.rs:50` |
| `PermissionRequest` | **Done** | `runtime/src/permissions.rs:26` |
| `PermissionOutcome` | **Done** | `runtime/src/permissions.rs:44` |
| `PermissionPrompter` trait | **Done** | `runtime/src/permissions.rs:39` |
| `authorize()` logic | **Done** | `runtime/src/permissions.rs:88` |
| `ResolvedPermissionMode` | **Done** | `runtime/src/config.rs:19` |
| Config key parsing | **Done** | `runtime/src/config.rs:658` |
| `AicpConfig` struct | **Done** | `runtime/src/config.rs:61` |
| Hook pipeline | **Done** | `runtime/src/hooks.rs` |
| `TuiPrompter` | **Not started** | `mammoth-cli/src/approval.rs` |
| `WebPrompter` | **Not started** | `server/src/approval.rs` |
| `ExtensionPrompter` | **Not started** | `extension/src/approval.ts` |
| `AicpPrompter` | **Not started** | `runtime/src/aicp_approval.rs` |
| Plan mode lifecycle | **Not started** | `mammoth-cli/src/app.rs` |
| Per-tool requirement registration | **Not started** | `mammoth-cli/src/app.rs` |
| Trust tier forwarding to AICP | **Not started** | `runtime/src/aicp_approval.rs` |

---

## Testing

All tests are in `apps/mammoth/crates/runtime/src/permissions.rs` under `#[cfg(test)]`. Existing tests cover:

- `allows_tools_when_active_mode_meets_requirement` — happy path for `WorkspaceWrite`
- `denies_read_only_escalations_without_prompt` — hard deny from `ReadOnly`
- `prompts_for_workspace_write_to_danger_full_access_escalation` — prompt path
- `honors_prompt_rejection_reason` — prompter denial forwarded correctly

### Tests to Add (Phase 3)

```rust
// Test: Allow mode bypasses all checks
#[test]
fn allow_mode_bypasses_all_checks() {
    let policy = PermissionPolicy::new(PermissionMode::Allow)
        .with_tool_requirement("bash", PermissionMode::DangerFullAccess);
    assert_eq!(policy.authorize("bash", "{}", None), PermissionOutcome::Allow);
}

// Test: Unknown tool defaults to DangerFullAccess requirement
#[test]
fn unknown_tool_defaults_to_danger_full_access() {
    let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite);
    assert!(matches!(
        policy.authorize("unknown_plugin_tool", "{}", None),
        PermissionOutcome::Deny { .. }
    ));
}

// Test: Prompt mode with absent prompter denies
#[test]
fn prompt_mode_without_prompter_denies() {
    let policy = PermissionPolicy::new(PermissionMode::Prompt)
        .with_tool_requirement("bash", PermissionMode::DangerFullAccess);
    assert!(matches!(
        policy.authorize("bash", "{}", None),
        PermissionOutcome::Deny { .. }
    ));
}
```

---

*Source files: `apps/mammoth/crates/runtime/src/permissions.rs`, `apps/mammoth/crates/runtime/src/config.rs`, `apps/mammoth/crates/runtime/src/hooks.rs`*
