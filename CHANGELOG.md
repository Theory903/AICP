# Changelog

All notable changes to AICP are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.10] — 2026-04-06 — SDKs, Platforms & Integrations

### Added

- **Python SDK** (`sdks/python/src/aicp_sdk/`) — Full client with all APIs
  - `AicpClient` class with `list_capabilities()`, `execute()`, `list_policies()`, `list_workflows()`, `list_approvals()`, `approve()`, `deny()`, `health()`
  - Dataclasses: `Capability`, `ExecutionResult`, `Policy`

- **TypeScript SDK** — Core + Runtime + Client packages
  - `@aicp/runtime` — `AicpRuntime` class with execution APIs
  - `@aicp/client` — High-level client with all operations

- **VS Code Extension** (`apps/mammoth/vscode-extension/`)
  - `MammothClient` — SSE connection to AICP
  - `MammothPanel` — Webview panel for chat
  - `GhostTextProvider` — Inline completion provider
  - `ApprovalForwarder` — VS Code notifications for approvals

- **macOS Menu Bar** (`apps/mammoth/macos-menu-bar/`)
  - `MammothMenuBar.swift` — SwiftUI menu bar app
  - `AicpClient` for API calls
  - Popover UI for prompts and approvals

- **Mobile App** (`apps/mammoth/mobile/`)
  - Flutter app with `AicpClient`
  - Capabilities, Approvals, Settings pages

- **Integration Plugins**
  - `plugins/integrations/github.py` — Issues, PRs, commits
  - `plugins/integrations/linear.py` — Issues, teams
  - `plugins/integrations/gmail.py` — Read/send email

- **New Core Systems**
  - `channels/` — Multi-channel messaging (26+ platforms)
  - `webhooks/` — Webhook registry, routing, signature verification
  - `cost_tracking/` — Token counting, budget management
  - `providers/` — Multi-LLM routing, fallback chains

- **New Schemas**
  - `plugin.schema.json` — Plugin definition
  - `plugin-manifest.schema.json` — Plugin manifest with signing

### Changed

- **Tests:** 1224 total (1038 Python + 186 Rust)
- **Version:** Bumped to 0.9.10

---

## [0.9.9] — 2026-04-05 — Production Features

### Added

- **SSRF Protection** — Block private IPs, DNS rebinding protection
- **OpenAI-Compatible API** — `/v1/chat/completions`, `/v1/models`, `/v1/embeddings`
- **DEK Encryption** — Data Encryption Key for credentials
- **4-Canonical MCP Tools** — setup, list_ops, get_schema, run

### Changed

- **Tests:** 941 Python tests

---

## [0.3.0] — 2026-04-03 — Orchestration

### Added

- Parallel step execution
- Event-driven flows
- Loop support (for-each, while, do-while)
- Subflow invocation
- Workflow DSL

### Changed

- **Tests:** 692

---

## [0.1.1-alpha] — 2025 — Foundation

### Added

- Capability registry
- Session management
- Basic policy engine

---

*More details in [ROADMAP.md](ROADMAP.md)*