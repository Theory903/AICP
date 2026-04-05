# Comparison

> How Mammoth and AICP relate to existing protocols, frameworks, agent tooling, and developer terminals — and what this stack adds that nothing else provides.

---

## Feature Matrix: AICP Execution Layer

| Capability | Raw APIs | OpenAPI | MCP | Tool Calling | LangChain | AICP |
|-----------|----------|---------|-----|-------------|-----------|------|
| Discoverability | No | Partial | Yes | Partial | Yes | Yes |
| Typed I/O schemas | Partial | Yes | Partial | Partial | Partial | Yes |
| Policy evaluation | No | No | No | No | No | Yes |
| Trust tiers | No | No | No | No | No | Yes |
| Risk scoring | No | No | No | No | No | Yes |
| Workflow state | No | No | No | No | Partial | Yes |
| Resumable execution | No | No | No | No | No | Yes |
| HITL approval checkpoints | No | No | No | No | No | Yes |
| Immutable audit trail | No | No | No | No | No | Yes |
| Continuation guidance | No | No | No | No | No | Yes |
| Side-effect classification | No | No | No | No | No | Yes |
| Compensation (rollback) | No | No | No | No | No | Yes |
| Determinism classification | No | No | No | No | No | Yes |
| Execution envelope | No | No | No | No | No | Yes |
| Multi-agent hierarchy | No | No | No | No | Partial | Yes |
| Federation | No | No | No | No | No | Yes |
| Perception layer | No | No | No | No | No | Yes |
| Signal processing | No | No | No | No | No | Yes |

---

## Feature Matrix: Mammoth Interaction Layer

| Capability | Claude Code | OpenCode | Cursor | Windsurf | Warp | Zed AI | GitHub Copilot | Mammoth |
|-----------|-------------|----------|--------|----------|------|--------|---------------|---------|
| Terminal REPL | Yes | Yes | No | No | Partial | No | No | Yes |
| Web supervision console | No | No | No | No | No | No | No | Yes |
| Chrome extension channel | No | No | No | No | No | No | No | Yes |
| AICP governance integration | No | No | No | No | No | No | No | Yes |
| Protocol-native approval gating | No | No | No | No | No | No | No | Yes |
| Workflow-aware execution | No | No | No | No | No | No | No | Yes |
| Immutable audit trail | No | No | No | No | No | No | No | Yes |
| Stateful session persistence | No | No | No | No | No | No | No | Yes |
| Policy-before-tool-execution | No | No | No | No | No | No | No | Yes |
| Plan mode / worktree support | Yes | Yes | No | No | No | No | No | Planned (v0.4.0) |
| MCP client support | Yes | Yes | Yes | Yes | No | Yes | No | Yes |
| Multi-provider backend | Anthropic only | Multiple | Multiple | Multiple | No | Multiple | GitHub | Yes |
| Open source | Yes | Yes | No | No | No | Yes | No | Yes |

---

## Detailed Comparisons

### Mammoth vs Claude Code

Claude Code is an AI coding agent terminal built on Claude. Mammoth is an AICP-native interaction OS.

| Dimension | Claude Code | Mammoth |
|-----------|-------------|---------|
| Scope | Coding agent terminal | Omni-capable agent interaction OS |
| Execution governance | None | AICP policy engine — trust tiers, risk scoring, approval |
| Workflow state | None | Stateful workflows, resumable across restarts |
| Approval lifecycle | Ad-hoc confirmation | Protocol-native HITL checkpoints |
| Audit trail | None | Immutable journal |
| Channels | Terminal only | Terminal, web, CLI, Chrome extension |
| Backend | Anthropic only | Any provider (Anthropic, OpenAI, Gemini, Ollama, etc.) |
| Web console | No | Mammoth Web — Studio supervision console |
| Browser integration | No | Chrome MV3 extension with page context capture |
| Governance protocol | No | AICP — open protocol with compliance levels |

### Mammoth vs Cursor

Cursor is an AI-first code editor. Mammoth is a terminal-first interaction OS.

| Dimension | Cursor | Mammoth |
|-----------|--------|---------|
| Primary surface | IDE / editor | Terminal REPL + web console + extension |
| Agent governance | None | AICP policy evaluation before every tool call |
| Workflow model | Single session | Stateful, resumable, multi-step workflows |
| Human oversight | None | Protocol-native approval checkpoints |
| Audit | None | Immutable execution journal |
| Open protocol | No | Yes — AICP is an open protocol |

### Mammoth vs OpenCode

OpenCode is an open-source AI coding agent terminal (written in Go) with MCP client support, multiple model providers, plan mode, and git worktree isolation. Mammoth is an AICP-native interaction OS.

| Dimension | OpenCode | Mammoth |
|-----------|----------|---------|
| Scope | Coding agent terminal | Omni-capable agent interaction OS |
| Channels | Terminal only | Terminal, web, CLI, Chrome extension |
| Execution governance | None | AICP policy engine — trust tiers, risk scoring, approval |
| Workflow state | None (stateless) | Stateful workflows, resumable across restarts |
| Plan mode / worktrees | Yes (built-in) | Planned (v0.4.0) |
| Approval lifecycle | Ad-hoc confirmation | Protocol-native HITL checkpoints |
| Audit trail | None | Immutable journal |
| MCP support | Yes (client) | Yes (client + server) |
| Multi-provider | Yes | Yes |
| Open source | Yes | Yes |
| Backend protocol | None | AICP open protocol |

### Mammoth vs Windsurf

Windsurf (by Codeium) is an AI-first IDE with deep VS Code-style editor integration and an agentic "Cascade" mode. Mammoth is a terminal-first agent OS.

| Dimension | Windsurf | Mammoth |
|-----------|----------|---------|
| Primary surface | IDE / editor | Terminal REPL + web console + extension |
| Editor integration | Deep (VS Code-compatible) | Not applicable (terminal-native) |
| Agent governance | None | AICP policy evaluation before every tool call |
| Workflow model | Single session | Stateful, resumable, multi-step workflows |
| Human oversight | None | Protocol-native approval checkpoints |
| Audit | None | Immutable execution journal |
| Web console | No | Yes (Mammoth Web) |
| MCP support | Yes | Yes (client + server) |
| Open protocol | No (proprietary) | Yes — AICP is an open protocol |

### Mammoth vs Warp

Warp is an AI-enhanced terminal. Mammoth is a governed agent interaction OS with a terminal channel.

| Dimension | Warp | Mammoth |
|-----------|------|---------|
| Primary purpose | Terminal productivity | Agent execution with governance |
| AI integration | Command suggestions | Full conversational agent with tool execution |
| Governance | None | AICP policy, trust tiers, risk scoring |
| Approval | None | Structured HITL checkpoints |
| Web console | Warp Drive (cloud, proprietary) | Mammoth Web (local, open) |
| Extension | No | Chrome MV3 |
| Protocol | Proprietary | Open (AICP) |

### AICP vs OpenAPI

OpenAPI describes APIs for developers. AICP describes action surfaces for agents.

| Dimension | OpenAPI | AICP |
|-----------|---------|------|
| Primary consumer | Human developers | Autonomous agents |
| Schema focus | Request/response shapes | Capabilities with governance metadata |
| State management | None (stateless) | Stateful workflows, sessions, resume |
| Policy | None | First-class policy evaluation |
| Side effects | Undeclared | Classified and governed |
| Error model | HTTP status codes | Structured errors with recovery hints |
| Continuation | None | `allowed_next_actions` on every response |
| Interop | AICP has an OpenAPI adapter | Import OpenAPI specs as AICP capabilities |

### AICP vs MCP (Model Context Protocol)

MCP transports tools between AI models and servers. AICP governs how agents use those tools.

| Dimension | MCP | AICP |
|-----------|-----|------|
| Purpose | Tool transport protocol | Agent operating system |
| Scope | Individual tool calls | Multi-step workflows with state |
| Governance | None | Policy, trust, risk, approval |
| State | Stateless per call | Stateful sessions, workflows |
| Audit | None | Immutable audit trail |
| Discovery | Server-level tool listing | Semantic search, ranked discovery |
| Interop | AICP has both MCP adapter and MCP server | Consume MCP tools as capabilities; expose AICP as MCP server |

**MCP disambiguation:** AICP interacts with MCP in two directions:
1. `adapters/protocol/mcp/` — MCP adapter that lets AICP consume external MCP tools as governed capabilities.
2. `mcp/` — MCP server that exposes AICP capabilities outward to MCP clients (Claude, Cursor, etc.).

### AICP vs LangChain / LangGraph

LangChain provides agent building blocks. AICP provides the governance and execution substrate those agents operate on.

| Dimension | LangChain/LangGraph | AICP |
|-----------|-------------------|------|
| Layer | Agent framework | Agent operating system |
| Tool governance | None built-in | Policy evaluation, risk scoring, approval |
| Workflow model | Chain/graph composition | Stateful workflows with compensation |
| State persistence | Optional (checkpointing) | Mandatory (resumable across restarts) |
| Audit | Optional logging | Mandatory immutable audit trail |
| Human oversight | Manual implementation | Protocol-native HITL checkpoints |
| Interop | AICP has LangChain and LangGraph adapters | Use AICP capabilities as LangChain tools |

---

## Positioning

```
                    ┌─────────────────────────────────────────────────┐
                    │           Mammoth: Interaction OS                │
                    │  Terminal | Web | CLI | Chrome Extension         │
                    └───────────────────┬─────────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────────────┐
                    │            AICP: Execution OS                    │
                    │  Policy | Workflow | Audit | Federation           │
                    └───────┬────────────┬────────────┬───────────────┘
                            │            │            │
                    ┌───────▼──┐   ┌─────▼─────┐  ┌──▼──────────┐
                    │ OpenAPI  │   │   MCP     │  │ LangChain   │
                    │ (schema) │   │(transport)│  │ (framework)  │
                    └──────────┘   └───────────┘  └─────────────┘
                            │            │            │
                    ┌───────▼────────────▼────────────▼───────────┐
                    │          Backend Services / APIs              │
                    └───────────────────────────────────────────────┘
```

- **OpenAPI** describes APIs. AICP imports them.
- **MCP** transports tools. AICP governs them.
- **LangChain** builds agents. AICP runs their actions under policy.
- **CrewAI** coordinates agents. AICP provides the execution substrate.
- **Claude Code** is a coding terminal. Mammoth is a governed interaction OS with AICP as its backbone.
- **OpenCode** is an open-source coding terminal with plan mode. Mammoth is a governed interaction OS with protocol-native policy, approval, and audit.
- **Cursor** is an AI editor. Mammoth is a terminal-first agent surface with governance, web console, and extension.
- **Windsurf** is an AI IDE with deep editor integration. Mammoth is a terminal-first agent OS with AICP governance.
- **Warp** is an AI terminal. Mammoth is a governed agent interaction OS with four channels.
- **Tool calling** (OpenAI, Anthropic) invokes functions. AICP adds governance, state, and audit around those invocations.

Mammoth is not a replacement for Claude Code, Cursor, or Warp. It is a different layer — the interaction OS that makes AICP's governed execution surface accessible to humans and agents across all channels.

---

## What Only This Stack Provides

| Capability | Description |
|-----------|-------------|
| Four-channel interaction OS | Terminal, web, CLI, and extension channels — all governed by AICP |
| Execution envelope | Every action returns a canonical, structured result consumed by all planes |
| `allowed_next_actions` | Agent always knows what it can do next, with confidence scores |
| Policy-before-execution | No side effects without policy evaluation |
| Structured approval lifecycle | Not just "confirm Y/N" but approve/reject/modify/delegate/escalate |
| Compensation semantics | Workflows can roll back completed steps on failure |
| Determinism classification | Planners and judges can reason about action repeatability |
| Federation | Cross-organization capability discovery via `/.well-known/aicp` |
| 11-plane architecture | Signal, Perception, AI, Capability, Workflow, Governance, Execution, Multi-Agent, Federation, Supervision, Learning |

---

## See Also

- [MAMMOTH.md](../guides/MAMMOTH.md) — Mammoth architecture (4 channels, channel trait, extension protocol)
- [ACTION_SURFACE.md](./ACTION_SURFACE.md) — What makes AICP's capability model unique
- [GOVERNANCE.md](./GOVERNANCE.md) — The governance layer no other framework has
- [VISION.md](./VISION.md) — The Agentic Web OS vision
- [ARCHITECTURE.md](../guides/ARCHITECTURE.md) — Full 11-plane architecture
