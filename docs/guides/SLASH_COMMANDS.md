# Slash Command Reference

> **Complete slash command catalog for Mammoth.**
> All built-in commands, syntax, options, and UX behaviors.

---

## Overview

Slash commands are triggered by typing `/` in the Mammoth input area. They control session behavior, memory, agent orchestration, workflow state, provider selection, MCP servers, and system configuration.

**Command registry:** `apps/mammoth/crates/commands/src/lib.rs`

```rust
pub struct CommandRegistry {
    commands: HashMap<String, Box<dyn SlashCommand>>,
}

pub trait SlashCommand: Send + Sync {
    fn name(&self) -> &str;
    fn aliases(&self) -> Vec<&str> { vec![] }
    fn description(&self) -> &str;
    fn usage(&self) -> &str;
    fn category(&self) -> CommandCategory;
    fn execute(&self, args: &[&str], ctx: &mut SessionContext) -> CommandResult;
    fn completions(&self, partial: &str) -> Vec<String>;
}
```

---

## Command Categories

| Category | Description |
|----------|-------------|
| `session` | Session management, resume, history |
| `model` | Model and provider selection |
| `memory` | Memory viewing and management |
| `context` | Files and context management |
| `agents` | Agent spawning and coordination |
| `tasks` | Background task management |
| `approval` | Approval queue and governance |
| `mcp` | MCP server management |
| `tools` | Tool management |
| `plan` | Plan mode and worktrees |
| `git` | Git operations |
| `lsp` | LSP and code intelligence |
| `bridge` | IDE bridge and editor integration |
| `config` | Configuration |
| `system` | Diagnostics and system |
| `help` | Help and documentation |

---

## Session Commands

### `/resume`
Resume a previous session.

```
/resume                     # Open session browser
/resume <session-id>        # Resume specific session
/resume --same-repo         # Resume most recent session in this repo
/resume --last              # Resume most recent session (any repo)
```

**UX:** Opens session browser overlay when called without arguments. Shows sessions grouped by project, with timestamps and last message preview.

**Implementation:** `apps/mammoth/crates/commands/src/resume.rs`, `apps/mammoth/crates/runtime/src/session.rs`

---

### `/new`
Start a new session, optionally forking from current.

```
/new                        # New empty session
/new --fork                 # Fork current session state
/new --with-memory          # New session, carry over memories
/new --model <model-id>     # New session with specific model
```

---

### `/history`
Browse conversation and audit history.

```
/history                    # Show conversation history in pager
/history --audit            # Show AICP audit log
/history --search <query>   # Search history
/history --last <n>         # Show last N turns
/history --export           # Export to markdown
```

---

### `/compact`
Compact the conversation context by summarizing earlier turns.

```
/compact                    # Auto-compact to fit context window
/compact --keep <n>         # Keep last N turns verbatim
/compact --target <k>       # Target K% context fill after compaction
```

**Note:** Uses the active model to produce the summary. Cannot be undone.

---

### `/clear`
Clear the conversation display (does not delete session).

```
/clear                      # Clear display
/clear --session            # Also reset session state
```

---

### `/cost`
Show session cost and token breakdown.

```
/cost                       # Summary
/cost --detailed            # Per-turn breakdown
/cost --export              # Export CSV
```

---

### `/status`
Show system status summary.

```
/status                     # Brief status
/status --full              # Full status including all providers and MCP
```

---

## Model Commands

### `/model`
Switch the active AI model.

```
/model                      # Open model picker overlay
/model <model-id>           # Switch to specific model
/model --list               # List all available models
/model --provider <name>    # List models from provider
/model --local              # List local (Ollama) models only
/model --reset              # Reset to default model
```

**Aliases:** `/m`

**UX:** Opens model picker overlay with grouped sections per provider. Fuzzy search. Shows pricing, context window, and capability badges.

---

### `/thinking`
Toggle extended thinking mode (Sonnet 3.7+, o3, o4-mini).

```
/thinking                   # Toggle on/off
/thinking --budget <n>      # Set thinking token budget (default: 8000)
/thinking --max             # Maximum budget
```

---

### `/temperature`
Set model temperature.

```
/temperature <value>        # e.g. /temperature 0.7
/temperature --reset        # Reset to model default
```

---

## Memory Commands

### `/memory`
View and manage memories.

```
/memory                     # List all memories
/memory --search <query>    # Semantic search memories
/memory --add "<text>"      # Manually add a memory
/memory --edit <id>         # Edit memory
/memory --delete <id>       # Delete memory
/memory --export            # Export all memories to markdown
/memory --import <file>     # Import memories from file
/memory --sync              # Sync team memories
```

**Aliases:** `/mem`

**UX:** Opens memory viewer sidebar panel.

**Implementation:** `apps/mammoth/crates/commands/src/memory.rs`, `apps/mammoth/crates/runtime/src/memdir.rs`

---

### `/forget`
Delete memories matching a pattern.

```
/forget "<pattern>"         # Delete matching memories
/forget --all               # Clear all memories (confirms)
/forget --session           # Clear session memories only
```

---

### `/learn`
Manually trigger memory extraction from recent conversation.

```
/learn                      # Extract memories from last 5 turns
/learn --turns <n>          # Extract from last N turns
/learn --all                # Extract from entire session
```

---

## Context Commands

### `/context`
Manage files and content in context.

```
/context                    # Show context sidebar
/context --list             # List files in context
/context --add <file>       # Add file to context
/context --remove <file>    # Remove file from context
/context --clear            # Clear all files from context
/context --size             # Show context token usage
```

**Aliases:** `/ctx`

---

### `/add`
Quick-add file(s) to context.

```
/add <file>                 # Add file
/add <glob>                 # Add files matching glob
/add --url <url>            # Fetch URL and add to context
/add --stdin                # Read from stdin
```

**Aliases:** `@<filename>` in input (attachment syntax)

---

### `/remove`
Remove file(s) from context.

```
/remove <file>
/remove --all
```

---

## Agent Commands

### `/agents`
Spawn and manage agent teams.

```
/agents                     # Show agent panel
/agents spawn <n>           # Spawn N worker agents
/agents spawn --role <role> # Spawn agent with specific role
/agents list                # List active agents
/agents kill <id>           # Kill specific agent
/agents kill --all          # Kill all agents
/agents message <id> <msg>  # Send message to agent
/agents log <id>            # View agent log
```

**Roles:** `worker`, `specialist`, `researcher`, `reviewer`, `planner`

**Implementation:** `apps/mammoth/crates/commands/src/agents.rs`, `apps/mammoth/crates/runtime/src/coordinator.rs`

---

### `/team`
Manage agent teams for complex multi-agent workflows.

```
/team create <name>             # Create named team
/team create --preset <preset>  # Create from preset
/team list                      # List all teams
/team status <name>             # Team status
/team dissolve <name>           # Dissolve team
/team message <name> <msg>      # Broadcast to team
```

**Presets:**
| Preset | Agents | Description |
|--------|--------|-------------|
| `swe` | coordinator + 3 workers | Software engineering team |
| `research` | coordinator + 2 researchers + 1 writer | Research and synthesis |
| `review` | coordinator + reviewer + implementer | Code review workflow |
| `full` | coordinator + 4 specialists + 2 workers | Maximum parallelism |

---

### `/coordinator`
Enter coordinator mode — you become the orchestrator of a team.

```
/coordinator                    # Enter coordinator mode
/coordinator --team <preset>    # With pre-spawned team
/coordinator exit               # Return to direct mode
```

---

## Task Commands

### `/task`
Manage background tasks.

```
/task                           # Show task panel
/task list                      # List all tasks
/task create "<description>"    # Create background task
/task status <id>               # Task status
/task cancel <id>               # Cancel task
/task output <id>               # View task output
/task wait <id>                 # Wait for task completion
```

**Implementation:** `apps/mammoth/crates/commands/src/tasks.rs`

---

## Approval Commands

### `/approval`
Manage the AICP approval queue.

```
/approval                       # Show approval queue
/approval list                  # List pending approvals
/approval show <id>             # Approval detail with blast radius
/approval approve <id>          # Approve
/approval reject <id>           # Reject
/approval delegate <id> <user>  # Delegate to another user
/approval history               # Approval history
```

**Aliases:** `/appr`

**Implementation:** `apps/mammoth/crates/commands/src/approval.rs`, `packages/cli/src/aicp_cli/commands/appr.py`

---

## MCP Commands

### `/mcp`
Manage MCP server connections.

```
/mcp                            # Show MCP status panel
/mcp list                       # List all configured servers
/mcp connect <name>             # Connect to server
/mcp disconnect <name>          # Disconnect
/mcp restart <name>             # Restart server
/mcp tools <name>               # List tools from server
/mcp resources <name>           # List resources from server
/mcp add <name> <command>       # Add new MCP server
/mcp remove <name>              # Remove server config
/mcp logs <name>                # View server logs
```

**Implementation:** `apps/mammoth/crates/commands/src/mcp.rs`, `apps/mammoth/crates/runtime/src/mcp.rs`

Full MCP guide: [MCP_GUIDE.md](./MCP_GUIDE.md)

---

## Plan Mode Commands

### `/plan`
Enter plan mode — write a plan before executing.

```
/plan                           # Enter plan mode, start planning
/plan --file <path>             # Load plan from file
/plan --goal "<text>"           # Auto-generate plan for goal
/plan show                      # Show current plan
/plan edit                      # Edit plan in $EDITOR
/plan exit                      # Exit plan mode
/plan save                      # Save plan to file
```

**Implementation:** `apps/mammoth/crates/commands/src/plan.rs`

Full plan mode guide: [PLAN_MODE.md](./PLAN_MODE.md)

---

### `/worktree`
Enter worktree isolation — work in a git worktree.

```
/worktree                       # Create worktree and enter
/worktree --branch <name>       # Worktree with specific branch name
/worktree list                  # List active worktrees
/worktree exit                  # Exit worktree (merge or discard)
/worktree discard               # Exit and discard all changes
/worktree merge                 # Exit and create PR/merge
/worktree status                # Current worktree status
```

Full worktree guide: [PLAN_MODE.md](./PLAN_MODE.md)

---

## Git Commands

### `/git`
Git operations with AI assistance.

```
/git status                     # git status summary
/git diff                       # Review uncommitted changes
/git commit                     # AI-generated commit message
/git commit --message "<msg>"   # Commit with specific message
/git branch <name>              # Create and switch branch
/git pr                         # Create pull request (uses gh CLI)
/git log                        # Show recent commits
/git blame <file>               # Annotated blame
/git review                     # Review current diff for issues
/git stash                      # Stash changes
/git restore                    # Restore stashed changes
```

---

### `/review`
Run code review on current changes.

```
/review                         # Review current git diff
/review --file <file>           # Review specific file
/review --pr <url>              # Review GitHub PR
/review --security              # Security-focused review
/review --performance           # Performance-focused review
```

---

## LSP Commands

### `/lsp`
LSP diagnostics and code intelligence.

```
/lsp                            # Show LSP status
/lsp diagnostics                # Show current diagnostics
/lsp diagnostics --file <file>  # File-specific diagnostics
/lsp start <language>           # Start language server
/lsp restart <language>         # Restart language server
/lsp symbols                    # Document symbols in current file
/lsp references <symbol>        # Find all references
/lsp definition <symbol>        # Jump to definition
```

Full LSP guide: [LSP_INTEGRATION.md](./LSP_INTEGRATION.md)

---

## Bridge Commands

### `/bridge`
IDE bridge control.

```
/bridge                         # Show bridge status
/bridge start                   # Start IDE bridge server
/bridge stop                    # Stop bridge server
/bridge status                  # Connection status
/bridge attach                  # Attach to existing IDE session
/bridge send "<msg>"            # Send message to attached IDE
```

Only available in `BRIDGE_MODE=true`. Full guide: [BRIDGE_IDE.md](./BRIDGE_IDE.md)

---

### `/desktop`
Desktop app handoff.

```
/desktop                        # Show desktop handoff options
/desktop open                   # Open Mammoth desktop app
/desktop pair                   # Pair with desktop app via QR code
```

---

## System Commands

### `/doctor`
Run comprehensive diagnostics.

```
/doctor                         # Full diagnostic report
/doctor --quick                 # Quick check (providers + config only)
/doctor --fix                   # Auto-fix fixable issues
/doctor --export                # Export diagnostic report
```

Full diagnostics guide: [DOCTOR_DIAGNOSTICS.md](./DOCTOR_DIAGNOSTICS.md)

---

### `/config`
View and edit configuration.

```
/config                         # Show current config
/config --edit                  # Open in $EDITOR
/config get <key>               # Get specific value
/config set <key> <value>       # Set value
/config reset <key>             # Reset to default
/config reset --all             # Reset everything (confirms)
/config validate                # Validate config file
```

---

### `/version`
Show version information.

```
/version                        # mammoth version + component versions
```

---

### `/help`
Show help.

```
/help                           # General help
/help <command>                 # Help for specific command
/help --all                     # List all commands
/help --category <cat>          # List commands in category
```

**Aliases:** `/?`

---

## Skills Commands

### `/skills`
Manage and invoke skills (reusable prompt workflows).

```
/skills                         # List installed skills
/skills list                    # Same
/skills show <name>             # Show skill content
/skills run <name>              # Invoke skill
/skills install <path>          # Install skill from file
/skills create <name>           # Create new skill
/skills update <name>           # Update skill
/skills delete <name>           # Delete skill
```

---

## Workflow Commands

### `/workflow`
AICP workflow management.

```
/workflow list                  # List workflows
/workflow show <id>             # Workflow detail
/workflow run <name>            # Start workflow
/workflow resume <id>           # Resume paused workflow
/workflow cancel <id>           # Cancel workflow
/workflow timeline <id>         # Show step timeline
```

---

## Onboarding Commands

### `/init`
Initialize AICP in a new project.

```
/init                           # Interactive onboarding wizard
/init --yes                     # Non-interactive with defaults
/init --force                   # Reinitialize existing project
```

---

## Plugin Commands

### `/plugins`
Manage Mammoth plugins.

```
/plugins                        # List installed plugins
/plugins install <path>         # Install plugin from directory
/plugins enable <name>          # Enable plugin
/plugins disable <name>         # Disable plugin
/plugins remove <name>          # Remove plugin
/plugins hooks                  # Show registered hooks
```

**Plugin structure:**
```
my-plugin/
├── .claw-plugin/
│   └── plugin.json           # name, version, hooks
└── hooks/
    ├── pre.sh                # Before tool execution
    └── post.sh               # After tool execution
```

---

## Command Completion

The slash command palette (`/`) provides fuzzy completion:

- Type `/` to open palette with all commands
- Continue typing to fuzzy-filter
- Tab to complete common prefix
- Arrow keys to navigate
- Enter to select
- Each command shows: name, description, category badge

---

## Adding Custom Commands

Add a file to `apps/mammoth/crates/commands/src/`:

```rust
use crate::{SlashCommand, CommandCategory, CommandResult, SessionContext};

pub struct MyCommand;

impl SlashCommand for MyCommand {
    fn name(&self) -> &str { "my-command" }
    fn aliases(&self) -> Vec<&str> { vec!["mc"] }
    fn description(&self) -> &str { "Does something useful" }
    fn usage(&self) -> &str { "/my-command [--option] <arg>" }
    fn category(&self) -> CommandCategory { CommandCategory::Custom }

    fn execute(&self, args: &[&str], ctx: &mut SessionContext) -> CommandResult {
        // implementation
        CommandResult::success("Done!")
    }

    fn completions(&self, partial: &str) -> Vec<String> {
        vec!["--option".to_string(), "arg1".to_string()]
    }
}
```

Register in `apps/mammoth/crates/commands/src/lib.rs`:
```rust
registry.register(Box::new(MyCommand));
```

---

## See Also

- [TUI_REFERENCE.md](./TUI_REFERENCE.md) — Command palette UI
- [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) — Tool reference
- [MULTI_AGENT.md](./MULTI_AGENT.md) — `/agents` and `/team` deep dive
- [PLAN_MODE.md](./PLAN_MODE.md) — `/plan` and `/worktree` deep dive
- [MCP_GUIDE.md](./MCP_GUIDE.md) — `/mcp` deep dive
- [MEMORY_SESSIONS.md](./MEMORY_SESSIONS.md) — `/memory` and `/resume` deep dive
