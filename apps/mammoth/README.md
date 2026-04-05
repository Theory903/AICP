# Mammoth

Mammoth is the **primary interaction shell** for the AICP stack.

It is the operator and agent entry point for discovering capabilities, running tasks, supervising workflows, handling approvals, reviewing diffs, and driving secure organizational automation against the AICP control plane.

Product posture in this repository:

- **Mammoth** is the only primary interaction surface for now.
- **AICP** is the governed backend and protocol/runtime control plane.
- **Studio** should be treated as embedded Mammoth supervision UX over time, not as a separate front door.

The Rust workspace is therefore more than a local coding CLI. It is the shell through which users and agents interact with governed execution, policy, approvals, and audit-backed automation.

## Current status

- **Version:** `0.1.0`
- **Release stage:** initial public release, source-build distribution
- **Primary implementation:** Rust workspace in this repository
- **Platform focus:** macOS and Linux developer workstations

## Install, build, and run

### Prerequisites

- Rust stable toolchain
- Cargo
- Provider credentials for the model you want to use

### Authentication

OpenAI-compatible / Ollama-compatible models:

```bash
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://127.0.0.1:11434/v1"
```

Example local shell launch:

```bash
cargo run -q -p mammoth-cli --bin mammoth -- --model kimi-k2.5:cloud
```

Anthropic-compatible models:

```bash
export ANTHROPIC_API_KEY="..."
# Optional when using a compatible endpoint
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

Grok models:

```bash
export XAI_API_KEY="..."
# Optional when using a compatible endpoint
export XAI_BASE_URL="https://api.x.ai"
```

OAuth login is also available:

```bash
cargo run --bin mammoth -- login
```

### Install locally

```bash
cargo install --path crates/mammoth-cli --locked
```

### Build from source

```bash
cargo build --release -p mammoth-cli
```

### Run

From the workspace:

```bash
cargo run --bin mammoth -- --help
cargo run --bin mammoth --
cargo run --bin mammoth -- prompt "summarize this workspace"
cargo run --bin mammoth -- --model sonnet "review the latest changes"
```

From the release build:

```bash
./target/release/mammoth
./target/release/mammoth prompt "explain crates/runtime"
```

## Supported capabilities

- Full-screen TUI shell plus one-shot prompt execution
- Saved-session inspection and resume flows
- Built-in workspace tools for shell, file read/write/edit, search, web fetch/search, todos, and notebook updates
- Slash commands for status, compaction, config inspection, diff, export, session management, and version reporting
- Local agent and skill discovery with `mammoth agents` and `mammoth skills`
- Plugin discovery and management through the CLI and slash-command surfaces
- OAuth login/logout plus model/provider selection from the command line
- Workspace-aware instruction/config loading (`MAMMOTH.md`, config files, permissions, plugin settings)

## Current limitations

- Public distribution is **source-build only** today; this workspace is not set up for crates.io publishing
- GitHub CI verifies `cargo check`, `cargo test`, and release builds, but automated release packaging is not yet present
- Current CI targets Ubuntu and macOS; Windows release readiness is still to be established
- Some live-provider integration coverage is opt-in because it requires external credentials and network access
- The command surface may continue to evolve during the `0.x` series

## Implementation

The Rust workspace is the active product implementation. It currently includes these crates:

- `mammoth-cli` — user-facing binary
- `api` — provider clients and streaming
- `runtime` — sessions, config, permissions, prompts, and runtime loop
- `tools` — built-in tool implementations
- `commands` — slash-command registry and handlers
- `plugins` — plugin discovery, registry, and lifecycle support
- `lsp` — language-server protocol support types and process helpers
- `server` and `compat-harness` — supporting services and compatibility tooling

## Roadmap

- Make Mammoth the rock-solid shell for AICP approvals, workflows, replay, and operator supervision
- Expand TUI command palette, inspectors, review panes, and workflow/event surfaces
- Publish packaged release artifacts for public installs
- Add a repeatable release workflow and longer-lived changelog discipline
- Expand platform verification beyond the current CI matrix

## Release notes

- Draft 0.1.0 release notes: [`docs/releases/0.1.0.md`](docs/releases/0.1.0.md)

## License

See the repository root for licensing details.
