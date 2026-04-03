# Comparison

> How AICP relates to existing protocols, frameworks, and agent tooling -- and what it adds that nothing else provides.

---

## Feature Matrix

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

## Detailed Comparisons

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
1. `adapters/protocol/mcp/` -- MCP adapter that lets AICP consume external MCP tools as governed capabilities.
2. `mcp/` -- MCP server that exposes AICP capabilities outward to MCP clients (Claude, Cursor, etc.).

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

### AICP vs CrewAI

CrewAI provides multi-agent orchestration. AICP provides the governance layer that CrewAI agents should operate under.

| Dimension | CrewAI | AICP |
|-----------|--------|------|
| Focus | Agent role definition and delegation | Governed execution with audit |
| Multi-agent | Role-based teams | Hierarchical (orchestrator/specialist/worker/supervisor) |
| Governance | None | Full policy engine |
| State | In-memory | Persistent, resumable |
| Interop | AICP has CrewAI adapter | Expose AICP capabilities to CrewAI agents |

---

## Positioning

```
                    ┌─────────────────────────────────────────┐
                    │           AICP (Operating System)        │
                    │  Policy | Workflow | Audit | Federation  │
                    └───────┬────────────┬────────────┬───────┘
                            │            │            │
                    ┌───────▼──┐   ┌─────▼─────┐  ┌──▼──────────┐
                    │ OpenAPI  │   │   MCP     │  │ LangChain   │
                    │ (schema) │   │(transport)│  │ (framework)  │
                    └──────────┘   └───────────┘  └─────────────┘
                            │            │            │
                    ┌───────▼────────────▼────────────▼───────┐
                    │          Backend Services / APIs          │
                    └─────────────────────────────────────────┘
```

- **OpenAPI** describes APIs. AICP imports them.
- **MCP** transports tools. AICP governs them.
- **LangChain** builds agents. AICP runs their actions under policy.
- **CrewAI** coordinates agents. AICP provides the execution substrate.
- **Tool calling** (OpenAI, Anthropic) invokes functions. AICP adds governance, state, and audit around those invocations.

AICP is not a replacement for any of these. It is the governance, state, and execution layer that sits between agent frameworks and backend services.

---

## What Only AICP Provides

| Capability | Description |
|-----------|-------------|
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

- [ACTION_SURFACE.md](./ACTION_SURFACE.md) -- What makes AICP's capability model unique
- [GOVERNANCE.md](./GOVERNANCE.md) -- The governance layer no other framework has
- [VISION.md](./VISION.md) -- The Agentic Web OS vision
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- Full 11-plane architecture
