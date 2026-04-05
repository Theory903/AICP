# Doctor Diagnostics

> **Implementation guide for the Mammoth `doctor` diagnostic system.**
> Covers the `DoctorChecker` runtime module, TUI overlay, CLI command, plugin interface, and full implementation roadmap.
>
> **Status:** Planned — not yet implemented. All Rust structs and trait definitions below are implementation targets.

---

## Overview

`doctor` is Mammoth's health-check system. It runs a battery of checks against the local environment — API credentials, model accessibility, MCP server connectivity, LSP availability, file permissions, network reachability, config validity, session storage, and extension bridge state — and reports pass/warn/fail results with actionable fix suggestions.

Three entry points:

| Surface | Trigger | Output |
|---------|---------|--------|
| TUI overlay | `Ctrl+D` or `/doctor` in Mammoth | Interactive panel inside TUI |
| CLI command | `mammoth doctor` | Terminal output, colorized |
| CI / scripted | `mammoth doctor --json` | Machine-readable JSON, exit code |

---

## Check Categories

Nine check categories run in order. Checks within a category run in parallel.

| # | Category | What it checks |
|---|----------|----------------|
| 1 | **API Credentials** | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` presence and format |
| 2 | **Model Accessibility** | Reachability of active provider base URL (HEAD/GET) |
| 3 | **MCP Server Connectivity** | Each configured `McpServerConfig` variant can be contacted |
| 4 | **LSP Server Availability** | Each configured language server binary is on `$PATH` |
| 5 | **File Permissions** | Config dir, session storage dir, and workspace root are readable/writable |
| 6 | **Network Connectivity** | HTTPS reachability to `api.anthropic.com`, `api.openai.com`, and configured AICP URL |
| 7 | **Config Schema Validity** | All loaded config files parse without errors; no unknown keys |
| 8 | **Session Storage Health** | Session DB (SQLite or file) opens and responds to a probe query |
| 9 | **Extension Bridge Status** | IDE bridge socket or port responds (only checked when `BRIDGE_MODE=true`) |

---

## Core Types

New file: `apps/mammoth/crates/runtime/src/doctor.rs`

```rust
// ── Implementation target ────────────────────────────────────────────────────
// File: apps/mammoth/crates/runtime/src/doctor.rs

use std::time::Duration;

/// Result of a single diagnostic check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckResult {
    /// Short identifier, e.g. `"anthropic_api_key"`.
    pub id: &'static str,
    /// Human-readable label shown in the TUI and CLI output.
    pub label: &'static str,
    /// Pass / Warn / Fail.
    pub status: CheckStatus,
    /// One-line explanation of the result.
    pub message: String,
    /// Suggested fix command or action. `None` when no fix is available.
    pub fix_hint: Option<String>,
    /// How long this check took.
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Warn,
    Fail,
}

impl CheckStatus {
    /// Returns `true` if the check blocks normal operation.
    pub fn is_blocking(&self) -> bool {
        matches!(self, CheckStatus::Fail)
    }

    /// ANSI color code for terminal rendering.
    pub fn color_code(&self) -> &'static str {
        match self {
            CheckStatus::Pass => "\x1b[32m", // green
            CheckStatus::Warn => "\x1b[33m", // yellow
            CheckStatus::Fail => "\x1b[31m", // red
        }
    }

    /// Symbol for TUI and CLI output.
    pub fn symbol(&self) -> &'static str {
        match self {
            CheckStatus::Pass => "✓",
            CheckStatus::Warn => "⚠",
            CheckStatus::Fail => "✗",
        }
    }
}

/// Trait implemented by each check category.
///
/// Implementors MUST be `Send + Sync` so checks can run in parallel via
/// `tokio::spawn`.
pub trait DoctorChecker: Send + Sync {
    /// Unique category identifier, e.g. `"api_credentials"`.
    fn category(&self) -> &'static str;

    /// Human-readable name shown in section headers.
    fn display_name(&self) -> &'static str;

    /// Run all checks in this category and return results.
    ///
    /// Implementations SHOULD time-box each individual check with a
    /// `tokio::time::timeout` of at most 5 seconds. Long-running checks
    /// that exceed the timeout MUST return a `CheckStatus::Warn` result
    /// (not panic or block forever).
    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult>;
}

/// Shared context passed to every `DoctorChecker::run` call.
///
/// Built once by `DoctorRunner::run_all` from the active `RuntimeConfig`.
pub struct DoctorContext {
    /// Resolved runtime configuration for the current session.
    pub config: crate::config::RuntimeConfig,
    /// Maximum time allowed per individual check.
    pub timeout: Duration,
    /// When `true`, emit verbose diagnostic messages.
    pub verbose: bool,
}

/// Orchestrates all registered checkers and collects results.
pub struct DoctorRunner {
    checkers: Vec<Box<dyn DoctorChecker>>,
}

impl DoctorRunner {
    /// Build a `DoctorRunner` with all built-in checkers registered.
    pub fn default_runner() -> Self {
        Self {
            checkers: vec![
                Box::new(ApiCredentialsChecker),
                Box::new(ModelAccessChecker),
                Box::new(McpConnectivityChecker),
                Box::new(LspAvailabilityChecker),
                Box::new(FilePermissionsChecker),
                Box::new(NetworkConnectivityChecker),
                Box::new(ConfigSchemaChecker),
                Box::new(SessionStorageChecker),
                Box::new(ExtensionBridgeChecker),
            ],
        }
    }

    /// Register an additional checker (for `DoctorPlugin` extensions).
    pub fn register(&mut self, checker: Box<dyn DoctorChecker>) {
        self.checkers.push(checker);
    }

    /// Run all categories and return a flat list of results.
    ///
    /// Categories run sequentially in declaration order. Checks within a
    /// category run in parallel via `tokio::task::JoinSet`.
    pub async fn run_all(&self, ctx: DoctorContext) -> DoctorReport {
        let mut categories: Vec<CategoryReport> = Vec::new();
        for checker in &self.checkers {
            let results = checker.run(&ctx);
            categories.push(CategoryReport {
                id: checker.category(),
                display_name: checker.display_name(),
                results,
            });
        }
        DoctorReport::new(categories)
    }
}

/// All results from a single run of `DoctorRunner`.
#[derive(Debug, Clone)]
pub struct DoctorReport {
    pub categories: Vec<CategoryReport>,
    pub pass_count: usize,
    pub warn_count: usize,
    pub fail_count: usize,
}

impl DoctorReport {
    fn new(categories: Vec<CategoryReport>) -> Self {
        let mut pass_count = 0;
        let mut warn_count = 0;
        let mut fail_count = 0;
        for cat in &categories {
            for r in &cat.results {
                match r.status {
                    CheckStatus::Pass => pass_count += 1,
                    CheckStatus::Warn => warn_count += 1,
                    CheckStatus::Fail => fail_count += 1,
                }
            }
        }
        Self { categories, pass_count, warn_count, fail_count }
    }

    /// Overall health: `Pass` only when zero failures and zero warnings.
    pub fn overall_status(&self) -> CheckStatus {
        if self.fail_count > 0 {
            CheckStatus::Fail
        } else if self.warn_count > 0 {
            CheckStatus::Warn
        } else {
            CheckStatus::Pass
        }
    }
}

#[derive(Debug, Clone)]
pub struct CategoryReport {
    pub id: &'static str,
    pub display_name: &'static str,
    pub results: Vec<CheckResult>,
}
```

Export the new module from `apps/mammoth/crates/runtime/src/lib.rs`:

```rust
// In apps/mammoth/crates/runtime/src/lib.rs — add:
pub mod doctor;
pub use doctor::{
    CheckResult, CheckStatus, DoctorChecker, DoctorContext,
    DoctorReport, DoctorRunner, CategoryReport,
};
```

---

## Check Implementations

### 1. API Credentials

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In apps/mammoth/crates/runtime/src/doctor.rs

pub struct ApiCredentialsChecker;

impl DoctorChecker for ApiCredentialsChecker {
    fn category(&self) -> &'static str { "api_credentials" }
    fn display_name(&self) -> &'static str { "API Credentials" }

    fn run(&self, _ctx: &DoctorContext) -> Vec<CheckResult> {
        vec![
            check_env_key(
                "anthropic_api_key",
                "Anthropic API key",
                "ANTHROPIC_API_KEY",
                "sk-ant-",
                "export ANTHROPIC_API_KEY=sk-ant-...",
            ),
            check_env_key(
                "openai_api_key",
                "OpenAI API key",
                "OPENAI_API_KEY",
                "sk-",
                "export OPENAI_API_KEY=sk-...",
            ),
            check_env_key(
                "google_api_key",
                "Google API key",
                "GOOGLE_API_KEY",
                "AIza",
                "export GOOGLE_API_KEY=AIza...",
            ),
        ]
    }
}

/// Generic helper: checks that an env var is set and starts with `prefix`.
fn check_env_key(
    id: &'static str,
    label: &'static str,
    env_var: &str,
    prefix: &str,
    fix_hint: &str,
) -> CheckResult {
    let start = std::time::Instant::now();
    let (status, message, fix) = match std::env::var(env_var) {
        Err(_) => (
            CheckStatus::Fail,
            format!("{env_var} is not set"),
            Some(fix_hint.to_string()),
        ),
        Ok(v) if v.trim().is_empty() => (
            CheckStatus::Fail,
            format!("{env_var} is empty"),
            Some(fix_hint.to_string()),
        ),
        Ok(v) if !v.starts_with(prefix) => (
            CheckStatus::Warn,
            format!("{env_var} set but does not match expected prefix \"{prefix}\""),
            None,
        ),
        Ok(_) => (
            CheckStatus::Pass,
            format!("{env_var} is set and looks valid"),
            None,
        ),
    };
    CheckResult {
        id,
        label,
        status,
        message,
        fix_hint: fix,
        duration_ms: start.elapsed().as_millis() as u64,
    }
}
```

**Logic summary:**

| Condition | Status | Message |
|-----------|--------|---------|
| Var not set | Fail | `ANTHROPIC_API_KEY is not set` |
| Var empty | Fail | `ANTHROPIC_API_KEY is empty` |
| Wrong prefix | Warn | `…does not match expected prefix "sk-ant-"` |
| OK | Pass | `ANTHROPIC_API_KEY is set and looks valid` |

---

### 2. Model Accessibility

Reads `mammoth_provider.rs`'s `DEFAULT_BASE_URL` (`https://api.anthropic.com`) and any override via `ANTHROPIC_BASE_URL`. Issues an HTTP HEAD to `/v1/models` with a 3-second timeout.

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct ModelAccessChecker;

impl DoctorChecker for ModelAccessChecker {
    fn category(&self) -> &'static str { "model_access" }
    fn display_name(&self) -> &'static str { "Model Accessibility" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // Reads ANTHROPIC_BASE_URL, falls back to DEFAULT_BASE_URL.
        // See: apps/mammoth/crates/api/src/providers/mammoth_provider.rs
        let base_url = std::env::var("ANTHROPIC_BASE_URL")
            .unwrap_or_else(|_| "https://api.anthropic.com".to_string());

        vec![probe_url(
            "anthropic_base_url",
            "Anthropic API reachable",
            &format!("{base_url}/v1/models"),
            ctx.timeout,
        )]
    }
}

/// Synchronous HTTP probe. Implementations should use reqwest::blocking or
/// run inside a tokio task. Returns Pass on 200/401/403 (server reached),
/// Warn on 429 (rate limit), Fail on connection error or timeout.
fn probe_url(
    id: &'static str,
    label: &'static str,
    url: &str,
    timeout: Duration,
) -> CheckResult {
    // Implementation detail: use reqwest::blocking::Client::new()
    //   .head(url)
    //   .timeout(timeout)
    //   .send()
    // Status codes 200, 401, 403 → Pass (server is reachable)
    // Status code 429 → Warn (rate limited but reachable)
    // Connection error, timeout → Fail
    todo!("HTTP probe to {url}")
}
```

---

### 3. MCP Server Connectivity

Reads `McpConfigCollection` from `RuntimeConfig`. Each `McpServerConfig` variant has a different probe strategy:

| Variant | Probe |
|---------|-------|
| `Stdio { command, … }` | Check `command` binary exists on `$PATH` |
| `Sse { url, … }` | HTTP GET to `url` with 3s timeout |
| `Http { url, … }` | HTTP GET to `url` with 3s timeout |
| `Ws { url, … }` | TCP connect to host+port derived from `url` |
| `Sdk { module, … }` | Check Node.js / Python binary exists on `$PATH` |
| `ManagedProxy { … }` | Check proxy socket or port is open |

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct McpConnectivityChecker;

impl DoctorChecker for McpConnectivityChecker {
    fn category(&self) -> &'static str { "mcp_connectivity" }
    fn display_name(&self) -> &'static str { "MCP Server Connectivity" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // ctx.config.feature_config.mcp → McpConfigCollection
        // Iterate over each McpServerConfig and probe based on variant.
        // See: apps/mammoth/crates/runtime/src/config.rs McpServerConfig enum
        todo!("iterate ctx.config MCP servers and probe each")
    }
}
```

Config source: `apps/mammoth/crates/runtime/src/config.rs` — `McpServerConfig` enum with 6 variants.

---

### 4. LSP Server Availability

Reads `LspManager` configuration. For each configured language server, checks that the server binary is accessible on `$PATH` using `which`/`where`.

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct LspAvailabilityChecker;

impl DoctorChecker for LspAvailabilityChecker {
    fn category(&self) -> &'static str { "lsp_availability" }
    fn display_name(&self) -> &'static str { "LSP Server Availability" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // Iterate LspServerConfig entries from ctx.config
        // For each: which::which(server.command) → Pass/Fail
        // See: apps/mammoth/crates/runtime/src/lib.rs — LspServerConfig export
        todo!("check each LSP binary on $PATH")
    }
}
```

Common binaries to check: `rust-analyzer`, `typescript-language-server`, `pyright`, `clangd`, `gopls`.

---

### 5. File Permissions

Checks three paths from `ConfigLoader`'s five search locations plus the session storage path.

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct FilePermissionsChecker;

impl DoctorChecker for FilePermissionsChecker {
    fn category(&self) -> &'static str { "file_permissions" }
    fn display_name(&self) -> &'static str { "File Permissions" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // Paths to check (from ConfigLoader logic in config.rs):
        //   ~/.config/mammoth/             — readable
        //   ./.mammoth/                    — readable/writable
        //   ~/.local/share/mammoth/        — writable (session storage)
        // Use std::fs::metadata() + permissions().readonly()
        todo!("check read/write permissions on config and storage dirs")
    }
}
```

Config file locations (from `ConfigLoader` in `config.rs`):

1. `~/.config/mammoth/config.json` (User)
2. `<project>/.mammoth/config.json` (Project)
3. `<project>/.mammoth/config.local.json` (Local)
4. `<project>/mammoth.config.json` (Project root)
5. `<project>/mammoth.config.local.json` (Project root, local)

---

### 6. Network Connectivity

Issues HTTPS probes to key endpoints. Uses the AICP URL from `AicpConfig` (default: `http://localhost:10003`).

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct NetworkConnectivityChecker;

impl DoctorChecker for NetworkConnectivityChecker {
    fn category(&self) -> &'static str { "network_connectivity" }
    fn display_name(&self) -> &'static str { "Network Connectivity" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        let aicp_url = ctx.config
            .feature_config()           // getter to be added
            .aicp
            .as_ref()
            .map(|a| a.url.clone())
            .unwrap_or_else(|| "http://localhost:10003".to_string());

        vec![
            probe_url("net_anthropic", "api.anthropic.com reachable",
                      "https://api.anthropic.com", ctx.timeout),
            probe_url("net_openai", "api.openai.com reachable",
                      "https://api.openai.com", ctx.timeout),
            probe_url("net_aicp", "AICP runtime reachable",
                      &format!("{aicp_url}/.well-known/aicp"), ctx.timeout),
        ]
    }
}
```

The AICP probe hits `/.well-known/aicp` — the discovery endpoint that all compliant AICP runtimes expose (per the `discovery.schema.json` spec).

---

### 7. Config Schema Validity

Parses all located config files against the expected schema and reports unknown keys, type mismatches, or parse failures.

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct ConfigSchemaChecker;

impl DoctorChecker for ConfigSchemaChecker {
    fn category(&self) -> &'static str { "config_schema" }
    fn display_name(&self) -> &'static str { "Config Schema Validity" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // Use ctx.config.loaded_entries() (getter to be added) to iterate
        // over each ConfigEntry { source, path }.
        // For each: parse JSON, validate against MAMMOTH_SETTINGS_SCHEMA_NAME
        // (the constant defined in config.rs).
        todo!("validate each loaded config entry against schema")
    }
}
```

Schema name constant is already defined in `config.rs`:

```rust
pub const MAMMOTH_SETTINGS_SCHEMA_NAME: &str = "SettingsSchema";
```

---

### 8. Session Storage Health

Opens the session storage backend and runs a no-op probe query (e.g., `SELECT 1` for SQLite, read-then-discard for file storage).

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct SessionStorageChecker;

impl DoctorChecker for SessionStorageChecker {
    fn category(&self) -> &'static str { "session_storage" }
    fn display_name(&self) -> &'static str { "Session Storage Health" }

    fn run(&self, ctx: &DoctorContext) -> Vec<CheckResult> {
        // Determine storage path from config (same logic as Session init).
        // Try opening the storage backend and running a probe query.
        // See: apps/mammoth/crates/runtime/src/lib.rs — Session export
        todo!("probe session storage backend")
    }
}
```

---

### 9. Extension Bridge Status

Only runs when `BRIDGE_MODE=true` is set in the environment. Probes the bridge socket.

```rust
// ── Implementation target ────────────────────────────────────────────────────
pub struct ExtensionBridgeChecker;

impl DoctorChecker for ExtensionBridgeChecker {
    fn category(&self) -> &'static str { "extension_bridge" }
    fn display_name(&self) -> &'static str { "Extension Bridge" }

    fn run(&self, _ctx: &DoctorContext) -> Vec<CheckResult> {
        let bridge_active = std::env::var("BRIDGE_MODE")
            .map(|v| v == "true" || v == "1")
            .unwrap_or(false);

        if !bridge_active {
            return vec![CheckResult {
                id: "bridge_mode",
                label: "Extension bridge",
                status: CheckStatus::Pass,
                message: "BRIDGE_MODE not enabled — skipped".to_string(),
                fix_hint: None,
                duration_ms: 0,
            }];
        }

        // Probe bridge socket. Default port: read from config or 9876.
        todo!("TCP probe bridge socket")
    }
}
```

---

## TUI Overlay

### Spec (from master plan section 3.1.8)

The doctor overlay is a full-width floating panel rendered above the conversation pane. It activates via `Ctrl+D` or by executing the `/doctor` slash command.

New struct in `apps/mammoth/crates/mammoth-cli/src/tui.rs`:

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In apps/mammoth/crates/mammoth-cli/src/tui.rs

use mammoth_runtime::doctor::{DoctorReport, CheckStatus};

/// State for the doctor diagnostics overlay.
#[derive(Debug, Clone)]
pub struct DoctorOverlay {
    /// Whether the overlay is currently visible.
    pub visible: bool,
    /// Results from the most recent `DoctorRunner::run_all()` call.
    pub report: Option<DoctorReport>,
    /// `true` while checks are in flight.
    pub loading: bool,
    /// Scroll offset (lines from top).
    pub scroll: usize,
}

impl Default for DoctorOverlay {
    fn default() -> Self {
        Self {
            visible: false,
            report: None,
            loading: false,
            scroll: 0,
        }
    }
}
```

Add `doctor: DoctorOverlay` to `MammothTui`:

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In apps/mammoth/crates/mammoth-cli/src/tui.rs — extend MammothTui

pub struct MammothTui {
    // … existing fields …
    pub doctor: DoctorOverlay,  // ← add this
}
```

### Rendering

Use `centered_rect()` (already defined in `tui.rs`) to produce an 80×40 floating panel. The render function signature:

```rust
// ── Implementation target ────────────────────────────────────────────────────
fn render_doctor_overlay(
    frame: &mut ratatui::Frame,
    overlay: &DoctorOverlay,
    area: ratatui::layout::Rect,
) {
    // 1. centered_rect(80, 40, area) → overlay_area
    // 2. frame.render_widget(Clear, overlay_area)  ← clear background
    // 3. Outer Block with title "  Doctor Diagnostics  " and borders
    // 4. For each CategoryReport:
    //      Section header: bold white category name
    //      For each CheckResult:
    //        symbol (colored) + label + "  " + message
    //        if fix_hint is Some: indent "  → fix: <hint>" in dim style
    // 5. Footer: [↑↓] scroll  [Esc] close  [R] rerun  [E] export
    // 6. Loading spinner when overlay.loading == true
}
```

### Keybindings

Add to the TUI event loop in `tui.rs`:

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In the key event handler in tui.rs:

KeyCode::Char('d') if key.modifiers == KeyModifiers::CONTROL => {
    app.tui.doctor.visible = !app.tui.doctor.visible;
    if app.tui.doctor.visible && app.tui.doctor.report.is_none() {
        // Trigger async doctor run and set loading = true
        trigger_doctor_run(&mut app).await;
    }
}
KeyCode::Esc if app.tui.doctor.visible => {
    app.tui.doctor.visible = false;
}
KeyCode::Char('r') if app.tui.doctor.visible => {
    trigger_doctor_run(&mut app).await;
}
KeyCode::Up if app.tui.doctor.visible => {
    app.tui.doctor.scroll = app.tui.doctor.scroll.saturating_sub(1);
}
KeyCode::Down if app.tui.doctor.visible => {
    app.tui.doctor.scroll += 1;  // clamp in render fn
}
```

### Status Bar Warning Badge

When `DoctorReport` contains failures, the status bar shows a pulsing badge:

```
● 2 issues   [Ctrl+D] to view
```

The badge pulses by toggling between bright red and dim red every 500ms via the existing TUI tick timer. Store `last_doctor_fail_count: usize` on `AppState` to track this.

---

## Slash Command

Add `Doctor` to the `SlashCommand` enum in `apps/mammoth/crates/mammoth-cli/src/app.rs`:

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In apps/mammoth/crates/mammoth-cli/src/app.rs

pub enum SlashCommand {
    Help,
    Status,
    Compact,
    Doctor,       // ← add
    Unknown(String),
}
```

Add a `doctor.rs` command handler in `apps/mammoth/crates/commands/src/`:

```rust
// ── Implementation target ────────────────────────────────────────────────────
// New file: apps/mammoth/crates/commands/src/doctor.rs

use crate::{CommandCategory, CommandResult, SessionContext, SlashCommand};

pub struct DoctorCommand;

impl SlashCommand for DoctorCommand {
    fn name(&self) -> &str { "doctor" }
    fn aliases(&self) -> Vec<&str> { vec!["diag", "diagnostics"] }
    fn description(&self) -> &str { "Run comprehensive environment diagnostics" }
    fn usage(&self) -> &str { "/doctor [--quick] [--fix] [--export] [--json]" }
    fn category(&self) -> CommandCategory { CommandCategory::System }

    fn execute(&self, args: &[&str], ctx: &mut SessionContext) -> CommandResult {
        // Parse flags from args:
        //   --quick  → skip LSP, bridge, session checks
        //   --fix    → apply auto-fixable remediations after report
        //   --export → write report to ~/.local/share/mammoth/doctor-<timestamp>.json
        //   --json   → emit raw JSON to stdout
        // Then open the DoctorOverlay in the TUI, or print to terminal if
        // called from mammoth-cli non-interactively.
        todo!("execute doctor command")
    }

    fn completions(&self, _partial: &str) -> Vec<String> {
        vec![
            "--quick".to_string(),
            "--fix".to_string(),
            "--export".to_string(),
            "--json".to_string(),
        ]
    }
}
```

Register in `apps/mammoth/crates/commands/src/lib.rs`:

```rust
// In register_all_commands(registry: &mut CommandRegistry):
registry.register(Box::new(DoctorCommand));
```

---

## CLI Command

`mammoth doctor` exposes diagnostics without the TUI.

### Usage

```
mammoth doctor [OPTIONS]

OPTIONS:
    --quick           Skip LSP, bridge, and session storage checks
    --fix             Auto-apply fixable remediations after report
    --export          Write full JSON report to a file
    --json            Output machine-readable JSON to stdout
    --timeout <secs>  Per-check timeout in seconds (default: 5)
    --verbose         Include timing and debug detail

EXAMPLES:
    mammoth doctor
    mammoth doctor --quick
    mammoth doctor --json | jq '.categories[] | select(.results[] | .status == "Fail")'
    mammoth doctor --fix
    mammoth doctor --export
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed (zero failures, zero warnings) |
| `1` | At least one warning (no failures) |
| `2` | At least one failure |

### JSON Output (`--json`)

```json
{
  "version": "1",
  "timestamp": "2026-04-05T14:23:00Z",
  "overall": "Fail",
  "pass_count": 7,
  "warn_count": 1,
  "fail_count": 2,
  "categories": [
    {
      "id": "api_credentials",
      "display_name": "API Credentials",
      "results": [
        {
          "id": "anthropic_api_key",
          "label": "Anthropic API key",
          "status": "Pass",
          "message": "ANTHROPIC_API_KEY is set and looks valid",
          "fix_hint": null,
          "duration_ms": 0
        },
        {
          "id": "openai_api_key",
          "label": "OpenAI API key",
          "status": "Fail",
          "message": "OPENAI_API_KEY is not set",
          "fix_hint": "export OPENAI_API_KEY=sk-...",
          "duration_ms": 0
        }
      ]
    }
  ]
}
```

### Terminal Output (colorized)

```
Mammoth Doctor Diagnostics
══════════════════════════

API Credentials
  ✓  Anthropic API key         ANTHROPIC_API_KEY is set and looks valid
  ✗  OpenAI API key            OPENAI_API_KEY is not set
     → fix: export OPENAI_API_KEY=sk-...
  ⚠  Google API key            GOOGLE_API_KEY set but does not match expected prefix "AIza"

Model Accessibility
  ✓  Anthropic API reachable   200 OK in 243ms

MCP Server Connectivity
  ✓  postgres                  TCP connect OK (127.0.0.1:5432)
  ✗  filesystem                Command "mcp-filesystem" not found on $PATH
     → fix: npm install -g @modelcontextprotocol/server-filesystem

…

──────────────────────────────────────
 7 passed  ·  1 warning  ·  2 failed
 Exit code: 2
```

---

## `DoctorPlugin` — Custom Checks

Third-party tools can add custom checks by implementing `DoctorChecker` and registering it before `DoctorRunner::run_all()`.

```rust
// Example: a custom plugin check
// apps/mammoth/crates/runtime/src/doctor.rs  ← DoctorChecker trait (already defined above)

// In your plugin crate:
use mammoth_runtime::doctor::{DoctorChecker, DoctorContext, CheckResult, CheckStatus};

pub struct MyServiceChecker;

impl DoctorChecker for MyServiceChecker {
    fn category(&self) -> &'static str { "my_service" }
    fn display_name(&self) -> &'static str { "My Service" }

    fn run(&self, _ctx: &DoctorContext) -> Vec<CheckResult> {
        let start = std::time::Instant::now();
        // … your check logic …
        vec![CheckResult {
            id: "my_service_up",
            label: "My Service running",
            status: CheckStatus::Pass,
            message: "Service responded to health check".to_string(),
            fix_hint: None,
            duration_ms: start.elapsed().as_millis() as u64,
        }]
    }
}

// Registration point (in plugin init):
pub fn register_doctor_checks(runner: &mut DoctorRunner) {
    runner.register(Box::new(MyServiceChecker));
}
```

The `DoctorPlugin` registration hook is called by Mammoth's plugin loader at startup when `BRIDGE_MODE` or a plugin config entry enables the plugin.

---

## Auto-Fix (`--fix`)

Some failures have known remediations. When `--fix` is passed, Mammoth attempts to apply them after printing the report.

| Check ID | Auto-fixable | Remediation |
|----------|-------------|-------------|
| `anthropic_api_key` | No | User must set env var |
| `openai_api_key` | No | User must set env var |
| `google_api_key` | No | User must set env var |
| `config_schema_*` | No | User must edit config |
| `mcp_stdio_*` | Prompt only | Print install command, ask to run |
| `lsp_*` | Prompt only | Print install command, ask to run |
| `file_permissions_*` | Yes | `chmod` the affected path |
| `session_storage_*` | Yes | Re-create storage directory |
| `extension_bridge` | No | User must start bridge server |

Auto-fix actions that require `chmod` or directory creation MUST prompt for confirmation before executing, even with `--fix`. Never silently mutate the filesystem.

---

## Error Message Reference

| Check ID | Status | Message | Fix hint |
|----------|--------|---------|---------|
| `anthropic_api_key` | Fail | `ANTHROPIC_API_KEY is not set` | `export ANTHROPIC_API_KEY=sk-ant-...` |
| `anthropic_api_key` | Warn | `ANTHROPIC_API_KEY set but does not match expected prefix "sk-ant-"` | — |
| `openai_api_key` | Fail | `OPENAI_API_KEY is not set` | `export OPENAI_API_KEY=sk-...` |
| `google_api_key` | Fail | `GOOGLE_API_KEY is not set` | `export GOOGLE_API_KEY=AIza...` |
| `anthropic_base_url` | Fail | `api.anthropic.com unreachable (timeout after 3s)` | Check network / VPN |
| `anthropic_base_url` | Warn | `api.anthropic.com returned 429 (rate limited)` | — |
| `net_aicp` | Fail | `AICP runtime unreachable at http://localhost:10003` | `aicp dev` or set `AICP_URL` |
| `net_aicp` | Warn | `AICP runtime at http://localhost:10003 returned non-200` | Check AICP server logs |
| `mcp_stdio_<name>` | Fail | `MCP server "<name>": command "<cmd>" not found on $PATH` | Install command |
| `mcp_sse_<name>` | Fail | `MCP server "<name>": GET <url> failed (connection refused)` | Start MCP server |
| `lsp_<lang>` | Warn | `LSP server for <lang> not found: "<binary>" not on $PATH` | Install binary |
| `file_permissions_config` | Fail | `~/.config/mammoth/ is not readable` | `chmod 700 ~/.config/mammoth` |
| `file_permissions_storage` | Fail | `Session storage dir is not writable` | `chmod 755 <path>` |
| `config_schema_<file>` | Fail | `Config file <path> failed to parse: <error>` | Edit config to fix JSON |
| `config_schema_<file>` | Warn | `Config file <path> has unknown keys: [<keys>]` | Remove unknown keys |
| `session_storage_probe` | Fail | `Session storage probe failed: <error>` | Delete and re-init storage |
| `extension_bridge` | Fail | `BRIDGE_MODE=true but bridge socket not responding` | Start IDE bridge |

---

## AppState Integration

Add to `AppState` (in `apps/mammoth/crates/mammoth-cli/src/app.rs`):

```rust
// ── Implementation target ────────────────────────────────────────────────────
// In apps/mammoth/crates/mammoth-cli/src/app.rs — extend AppState / SessionState

pub struct SessionState {
    // … existing fields …
    /// Most recent doctor report. `None` until first run.
    pub doctor_report: Option<mammoth_runtime::doctor::DoctorReport>,
    /// `true` while a doctor run is in flight.
    pub doctor_running: bool,
}
```

`doctor_report` is checked by the status bar renderer to show the warning badge.

---

## Implementation Roadmap

| Step | Task | File | Depends on |
|------|------|------|------------|
| 1 | Create `doctor.rs` with core types and `DoctorRunner` | `runtime/src/doctor.rs` | — |
| 2 | Implement `ApiCredentialsChecker` | `doctor.rs` | Step 1 |
| 3 | Implement `NetworkConnectivityChecker` | `doctor.rs` | Step 1 |
| 4 | Implement `ModelAccessChecker` | `doctor.rs` | Step 3 |
| 5 | Implement `ConfigSchemaChecker` | `doctor.rs` | Step 1, `ConfigLoader` |
| 6 | Implement `FilePermissionsChecker` | `doctor.rs` | Step 1 |
| 7 | Implement `McpConnectivityChecker` | `doctor.rs` | Steps 3, 4 |
| 8 | Implement `LspAvailabilityChecker` | `doctor.rs` | Step 1 |
| 9 | Implement `SessionStorageChecker` | `doctor.rs` | Step 1 |
| 10 | Implement `ExtensionBridgeChecker` | `doctor.rs` | Step 3 |
| 11 | Export module from `runtime/src/lib.rs` | `lib.rs` | Steps 1–10 |
| 12 | Add `DoctorOverlay` struct to `tui.rs` | `tui.rs` | Step 11 |
| 13 | Add `Ctrl+D` keybinding and overlay renderer | `tui.rs` | Step 12 |
| 14 | Add status bar warning badge | `tui.rs` | Step 12 |
| 15 | Add `SlashCommand::Doctor` variant | `app.rs` | Step 12 |
| 16 | Create `commands/src/doctor.rs` and register | `commands/src/doctor.rs` | Step 15 |
| 17 | Wire `mammoth doctor` CLI subcommand | `mammoth-cli/src/` | Step 16 |
| 18 | Implement `--json` serialization for `DoctorReport` | `doctor.rs` | Steps 1–10 |
| 19 | Implement `--fix` auto-remediation prompts | `commands/src/doctor.rs` | Step 16 |
| 20 | Write unit tests for each checker | `runtime/tests/` | Steps 2–10 |

**Estimated scope:** ~800–1000 lines of Rust across `doctor.rs`, `tui.rs`, `app.rs`, and the new command file.

---

## Testing

### Unit tests (no network)

```rust
// apps/mammoth/crates/runtime/tests/doctor_tests.rs

#[cfg(test)]
mod tests {
    use mammoth_runtime::doctor::*;
    use std::time::Duration;

    fn test_ctx() -> DoctorContext {
        DoctorContext {
            config: Default::default(),
            timeout: Duration::from_secs(1),
            verbose: false,
        }
    }

    #[test]
    fn api_key_missing_is_fail() {
        std::env::remove_var("ANTHROPIC_API_KEY");
        let results = ApiCredentialsChecker.run(&test_ctx());
        let r = results.iter().find(|r| r.id == "anthropic_api_key").unwrap();
        assert_eq!(r.status, CheckStatus::Fail);
    }

    #[test]
    fn api_key_present_is_pass() {
        std::env::set_var("ANTHROPIC_API_KEY", "sk-ant-test1234");
        let results = ApiCredentialsChecker.run(&test_ctx());
        let r = results.iter().find(|r| r.id == "anthropic_api_key").unwrap();
        assert_eq!(r.status, CheckStatus::Pass);
        std::env::remove_var("ANTHROPIC_API_KEY");
    }

    #[test]
    fn api_key_wrong_prefix_is_warn() {
        std::env::set_var("ANTHROPIC_API_KEY", "wrong-prefix-key");
        let results = ApiCredentialsChecker.run(&test_ctx());
        let r = results.iter().find(|r| r.id == "anthropic_api_key").unwrap();
        assert_eq!(r.status, CheckStatus::Warn);
        std::env::remove_var("ANTHROPIC_API_KEY");
    }

    #[test]
    fn overall_status_reflects_failures() {
        let report = DoctorReport::new(vec![
            CategoryReport {
                id: "test",
                display_name: "Test",
                results: vec![
                    CheckResult {
                        id: "x", label: "X",
                        status: CheckStatus::Fail,
                        message: "failed".into(),
                        fix_hint: None,
                        duration_ms: 0,
                    }
                ],
            }
        ]);
        assert_eq!(report.overall_status(), CheckStatus::Fail);
        assert_eq!(report.fail_count, 1);
    }

    #[test]
    fn bridge_checker_skipped_when_bridge_mode_off() {
        std::env::remove_var("BRIDGE_MODE");
        let results = ExtensionBridgeChecker.run(&test_ctx());
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].status, CheckStatus::Pass);
        assert!(results[0].message.contains("skipped"));
    }
}
```

### Integration tests (with mock server)

For `NetworkConnectivityChecker` and `McpConnectivityChecker`, use a `wiremock` or `axum::Router` test server to avoid real network calls.

---

## See Also

- [SLASH_COMMANDS.md](./SLASH_COMMANDS.md) — `/doctor` entry in the slash command catalog
- [TUI_REFERENCE.md](./TUI_REFERENCE.md) — TUI overlay rendering and keybindings reference
- [MCP_GUIDE.md](./MCP_GUIDE.md) — MCP server configuration (`McpServerConfig` variants)
- [LSP_INTEGRATION.md](./LSP_INTEGRATION.md) — LSP server configuration
- [PROVIDER_GUIDE.md](./PROVIDER_GUIDE.md) — Provider base URLs and auth sources
- `apps/mammoth/crates/runtime/src/config.rs` — `RuntimeConfig`, `AicpConfig`, `McpConfigCollection`
- `apps/mammoth/crates/api/src/providers/mammoth_provider.rs` — `AuthSource`, `DEFAULT_BASE_URL`
- `docs/plans/2026-04-05-mammoth-peak-tui.md` — Master plan section 3.1.8 (DoctorOverlay spec)
