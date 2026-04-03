<div align="center">

# AICP

### The Agentic Web Operating System

**The protocol, runtime, and governance layer that turns the human web into an agent-operable web.**

v0.1.1-alpha | [Spec](spec/) | [Docs](docs/) | [Status](STATUS.md) | Apache 2.0

</div>

---

## What is AICP?

AICP (AI Capability Protocol) is an operating system for autonomous agents on the internet. It provides the full stack -- signal ingestion, perception, planning, execution, governance, memory, multi-agent coordination, federation, supervision, and learning -- that agents need to operate real applications safely, at scale, across organizational boundaries.

Today's AI agents interact with software through brittle tool calls: untyped function signatures, no governance, no memory, no coordination. This is roughly where networking was before TCP/IP. Every agent framework reinvents capability discovery, policy enforcement, workflow orchestration, and human oversight from scratch. The result is fragile, ungoverned, and unscalable.

AICP replaces this with a layered operating system. At the bottom, a signal plane ingests events at sub-millisecond latency. Above it, a perception plane gives agents full sensory coverage of applications -- accessibility trees, DOM state, screenshots, behavioral signals. The AI plane routes intent, plans multi-step operations, and evaluates results. The capability plane exposes a global mesh of governed actions. The workflow plane orchestrates them. The governance plane enforces policy in real time. The execution plane runs three classes of work (realtime, transactional, event-driven). The multi-agent plane coordinates hierarchies of specialists. The federation plane connects organizations into an agentic WWW. The supervision plane gives humans a control tower. The learning plane mines skills and calibrates autonomy over time.

The design principle: agents are not users with a chatbox. They are principals operating software at machine speed, and they need an operating system purpose-built for that reality. AICP is that operating system.

---

## Why AICP?

| Dimension | Traditional Tool Calling | AICP |
|-----------|--------------------------|------|
| **Discovery** | Agent guesses which tools exist | Global capability mesh with ranked discovery, semantic search, graph traversal |
| **Input/Output** | Untyped or loosely typed | Strict JSON Schema contracts with validation, side-effect classification, error codes |
| **Governance** | None; agent decides everything | Compiled policy engine: allow/deny/ask/limit per capability, trust tiers, risk scoring |
| **Approval** | Not supported | First-class approval lifecycle with intent matching, blast radius estimation, auto-resume |
| **Workflows** | Agent tracks state manually | Stateful, resumable orchestration: sequential, parallel, fork/join, sagas, compensation |
| **Memory** | Conversation context window | Structured memory system: working memory, episodic, semantic, procedural |
| **Multi-Agent** | Ad hoc message passing | Four-tier hierarchy: orchestrator, specialist, worker, supervisor |
| **Observability** | Logs, maybe | Append-only audit trail, replay debugger, live execution feed, correlation IDs |
| **Federation** | Not supported | `/.well-known/aicp` discovery, CRDT registries, DID authentication |
| **Learning** | Static | Skill mining, policy learning, drift detection, autonomy calibration |

---

## Architecture: The 11 Planes

AICP is organized into 11 architectural planes (0-10), each responsible for a distinct operational concern.

| # | Plane | Purpose | Key Capabilities |
|---|-------|---------|------------------|
| 0 | **Signal** | Sub-ms event ingestion | Event bus, webhook receivers, change-data-capture streams |
| 1 | **Perception** | Full sensory coverage | Accessibility tree parsing, DOM observation, state API polling, screenshot capture, behavioral signal extraction |
| 2 | **AI** | Agent cognition | Intent router, planner, judge, memory system, cognitive protocols, context budget management |
| 3 | **Capability** | Global action mesh | Capability registry, schema validation, ranked discovery, semantic search, dependency graph |
| 4 | **Workflow** | Orchestration | Sequential, parallel, fork/join, sagas, event-driven flows, compensation, approval checkpoints |
| 5 | **Governance** | Governed autonomy | Compiled policy engine, trust tiers, risk scoring, approval lifecycle, compliance enforcement |
| 6 | **Execution** | Three-class runtime | Realtime (<5ms), transactional (with sagas), event-driven (wait/resume) |
| 7 | **Multi-Agent** | Coordination | Orchestrator, specialist, worker, supervisor hierarchy; task delegation, conflict resolution |
| 8 | **Federation** | Agentic WWW | `/.well-known/aicp` discovery, CRDT-based registries, DID authentication, cross-org capability sharing |
| 9 | **Supervision** | Human control tower | Live execution feed, approval queue, replay debugger, policy editor, health dashboard |
| 10 | **Learning** | Continuous improvement | Skill mining, policy learning, drift detection, autonomy calibration, benchmark regression |

---

## The 20 Modules

Each plane is implemented through concrete modules. These are the building blocks of an AICP-compliant system.

| # | Module | Plane | Description |
|---|--------|-------|-------------|
| 1 | Principal and Org Control | Governance | Identity hierarchy, org boundaries, delegation chains, principal attribution |
| 2 | Identity and Trust | Governance | DID-based authentication, trust tiers, credential verification, session tokens |
| 3 | Capability Registry | Capability | Schema-validated capability store, versioning, deprecation, dependency tracking |
| 4 | Tool Runtime | Execution | Sandboxed capability invocation, timeout enforcement, result normalization |
| 5 | Workflow Engine | Workflow | Step execution, state persistence, branching, compensation, approval integration |
| 6 | Perception and Signal Layer | Perception / Signal | DOM observers, a11y tree extraction, screenshot pipeline, event ingestion |
| 7 | Human Cognitive Protocols | Supervision | Approval UX, review packets, impact summaries, decision lifecycle management |
| 8 | AI Plane | AI | Planner, judge, intent router, tool selection, context budget, cognitive loops |
| 9 | Memory System | AI | Working memory, episodic store, semantic index, procedural knowledge base |
| 10 | Code Intelligence DB | AI | AST indexing, symbol graph, call-chain analysis, code-aware context building |
| 11 | Crawl / Map / Discovery Engine | Capability | Web crawling, capability extraction, site mapping, capability graph construction |
| 12 | Governance and Policy | Governance | Policy DSL, compiled evaluation, effect resolution, audit integration |
| 13 | Execution Engine | Execution | Three-class dispatcher, saga coordinator, idempotency, failure recovery |
| 14 | Multi-Agent Hierarchy | Multi-Agent | Role assignment, task delegation, result aggregation, supervisor escalation |
| 15 | Agent Communication Bus | Multi-Agent | Typed message passing, pub/sub channels, coordination protocols |
| 16 | Federation and Agentic WWW | Federation | Discovery protocol, cross-org registry sync, trust federation, capability routing |
| 17 | Human Web Compatibility | Perception | Browser automation fallback, form filling, navigation, legacy app support |
| 18 | Audit / Replay / Observability | Supervision | Append-only audit journal, execution replay, correlation, distributed tracing |
| 19 | Learning / Drift / Growth | Learning | Skill extraction, policy refinement, performance drift detection, autonomy scaling |
| 20 | Domain Packs and Benchmarks | Learning | Pre-built capability sets per vertical, evaluation suites, regression testing |

---

## Quick Start

AICP v0.1.1-alpha is available today as a Python reference implementation. It covers Compliance Level 2 (Resumable Workflows) with full governance.

### Install

```bash
git clone https://github.com/aicp-ai/aicp.git
cd aicp
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi
```

### Bootstrap an Existing App

```bash
# Point AICP at a FastAPI application
aicp bootstrap fastapi server.main:app

# Scan capabilities from OpenAPI spec
aicp scan --openapi http://localhost:8000/openapi.json

# Preview what was discovered
aicp preview payments.transfer
```

### Add Governance

```bash
# Require approval for dangerous capabilities
aicp protect payments.transfer

# Rate-limit an entire namespace
aicp limit "users.*" --rpm 60

# Set a blanket policy
aicp policy safe "notes.*"
aicp policy ask "payments.*"
aicp policy deny "admin.delete_all"
```

### Run

```bash
# Start the AICP dev server (mounts on your app)
aicp dev

# Execute a capability
aicp run notes.create -i '{"title": "Hello", "body": "World"}'

# Execute with auto-approval
aicp run payments.transfer -i '{"to": "acct_123", "amount": 50}' --yes

# Non-interactive mode (for CI/scripts)
aicp run notes.create -i '{"title": "Automated"}' --no-input
```

### Approval Queue

```bash
# List pending approvals
aicp appr ls

# Inspect an approval
aicp appr show appr_abc123

# Approve or deny
aicp appr ok appr_abc123
aicp appr no appr_abc123 --reason "Amount too high"
```

### Mount in Code

```python
from fastapi import FastAPI
from aicp_connect_fastapi import mount_aicp

app = FastAPI()
mount_aicp(app)
# AICP routes now available at /v1/*, /console, /.well-known/aicp
```

---

## Compliance Levels

Implementations declare their conformance level. Each level subsumes all requirements of the levels below it.

| Level | Name | Requirements |
|-------|------|-------------|
| 0 | **Capability Discovery** | Capability registry, input/output schema validation, basic execution |
| 1 | **Governed Execution** | Policy evaluation, approval checkpoints, audit trail, session management |
| 2 | **Resumable Workflows** | Sequential workflows, compensation, state persistence, resume after approval |
| 3 | **Event-Driven Orchestration** | Wait-for-event, timeout branching, parallel steps, loops |
| 4 | **AI Planning Support** | Planner, judge, context builder, allowed-next-actions schema |
| 5 | **Full Orchestration** | Multi-flow orchestration, subflows, cross-flow events, supervision console |

The reference implementation in this repository is at **Level 2**.

---

## Current State

### v0.1.1-alpha -- What is Built

| Area | Metric | Details |
|------|--------|---------|
| **Spec** | 9 JSON schemas | capability, workflow, policy, execution-result, approval-request, approval-decision, audit-entry, discovery, error |
| **Runtime** | 8 services | Execution, approvals, workflows, sessions, discovery, audit, interactions, provider health |
| **API** | 30+ endpoints | 13 route groups including `/v1` AI action surface, `/.well-known/aicp`, `/console` |
| **Persistence** | 3 backends | In-memory, file (JSON/JSONL), SQLite (WAL mode, 7 tables) |
| **CLI** | 28 commands | `run`, `dev`, `scan`, `preview`, `bootstrap`, `import`, `appr`, `policy`, `test` |
| **Adapters** | 6 working | FastAPI, MCP, OpenAPI, cURL importer, HAR importer, Postman importer |
| **Tests** | 172 passing | Core, runtime, CLI, adapters, benchmarks |
| **SDKs** | 1 built | TypeScript Core (built and distributable) |
| **UI** | Agent console | 840-line HTML dashboard at `/console` |

### v1.0.0 -- What is Next

The path from v0.1.1 to v1.0.0 adds the remaining planes and completes the agentic web OS. Each phase maps to a specific version.

| Phase | Version | Focus | Key Deliverables | Compliance Level |
|-------|---------|-------|------------------|------------------|
| **1** | **0.2.0** | AI Core | Planner, judge, memory/context builder, intent router, cognitive protocols | L4 |
| **2** | **0.3.0** | Orchestration | YAML workflow DSL, event-driven flows, parallel/loop support, subflows | L3+L4 |
| **3** | **0.4.0** | Agent Integration | LangChain, LangGraph, CrewAI adapters, food ordering reference flow | L4 |
| **4** | **0.5.0** | Perception | a11y tree extraction, DOM observation, screenshot pipeline, signal bus | L4 |
| **5** | **0.6.0** | Multi-Agent | 4-tier hierarchy, communication bus, task delegation, supervisor roles | L5 |
| **6** | **0.7.0** | Federation | Cross-org discovery, CRDT registries, DID auth, trust federation | L5 |
| **7** | **0.8.0** | Learning | Skill mining, policy learning, drift detection, domain packs, benchmarks | L5 |
| **8** | **0.9.0** | Production | Encrypted sessions, compiled WASM policies, risk scoring, multi-tenant | L5 |
| **9** | **1.0.0** | Agentic Web OS | Complete 11-plane architecture, stable protocol, production-ready | L5 |

**Note on compliance levels:** L3 (Event-Driven Orchestration) ships in v0.3.0, but L4 (AI Planning Support) is already reached in v0.2.0. Compliance levels are cumulative -- reaching L4 does not require L3 features to ship first, but L5 requires all of L0-L4.

---

## Repository Structure

```
aicp/
├── spec/                          # Protocol source of truth (JSON schemas)
│   ├── schemas/                   # 9 schema definitions
│   ├── examples/                  # Valid/invalid examples
│   └── tests/                     # Schema validation tests
├── packages/
│   ├── core/                      # Protocol domain model (Python)
│   ├── runtime/                   # Execution engine, services, persistence
│   └── cli/                       # 28 CLI commands
├── adapters/
│   ├── protocol/                  # HTTP, MCP, OpenAPI, GraphQL, WebSocket
│   ├── framework/                 # FastAPI, Express, NestJS, Next.js, Spring Boot
│   ├── agent/                     # LangChain, LangGraph, CrewAI
│   └── importers/                 # cURL, HAR, Postman importers
├── sdks/
│   ├── typescript/                # TypeScript SDK (core built)
│   └── python/                    # Python SDK (skeleton)
├── mcp/                           # MCP server implementations
├── apps/
│   └── studio/                    # AICP Studio (control plane UI)
├── examples/                      # Reference applications
├── docs/                          # Documentation
├── rfcs/                          # Protocol change proposals
└── governance/                    # Contribution guidelines
```

**Authoritative rule:** `/spec` is the source of truth. If runtime behavior and spec disagree, spec wins.

**MCP disambiguation:** The repository contains two MCP packages that serve opposite directions. `mcp/` is the **MCP server** -- it exposes AICP capabilities outward to MCP clients (e.g., Claude, Cursor). `adapters/protocol/mcp/` is the **MCP adapter** -- it lets AICP consume external MCP tools as capabilities. Both are complete. They are different packages solving different problems. Do not confuse them.

---

## Integrations

### Available

| Integration | Type | Status |
|-------------|------|--------|
| FastAPI | Framework adapter | Working. `mount_aicp(app)` adds all AICP routes. |
| MCP | Protocol adapter | Working. Full MCP server with tool exposure. |
| OpenAPI | Protocol adapter | Working. `aicp scan --openapi` imports capabilities. |
| cURL | Importer | Working. `aicp import --curl` converts cURL commands. |
| HAR | Importer | Working. `aicp import --har` converts HTTP archives. |
| Postman | Importer | Working. `aicp import --postman` converts collections. |
| TypeScript Core SDK | SDK | Built and distributable. |

### Planned

| Integration | Type | Phase |
|-------------|------|-------|
| LangChain | Agent adapter | 3 |
| LangGraph | Agent adapter | 3 |
| CrewAI | Agent adapter | 3 |
| Express | Framework adapter | 8 |
| NestJS | Framework adapter | 8 |
| Next.js | Framework adapter | 8 |
| Spring Boot | Framework adapter | 8 |
| HTTP | Protocol adapter | 8 |
| GraphQL | Protocol adapter | 8 |
| WebSocket | Protocol adapter | 8 |
| Python SDK | SDK | 2 |
| TypeScript Runtime SDK | SDK | 3 |
| TypeScript Client SDK | SDK | 3 |

---

## Execution Contract

Every capability execution in AICP produces a canonical envelope. This is the fundamental interface that all planes consume -- UI, planner, judge, audit, and replay. The canonical definition lives in `spec/schemas/execution-result.schema.json`; what follows is the full envelope.

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "orders.place",
  "capability_kind": "action",
  "determinism_class": "bounded_nondeterministic",
  "workflow_id": "wf_e5f6g7h8",
  "step_id": "step_place_order",
  "session_id": "sess_i9j0k1l2",
  "execution_mode": "sync",
  "policy_result": {
    "effect": "allow",
    "policy_name": "default_actions",
    "trust_tier": 2,
    "risk_score": { "financial": 0.7, "irreversibility": 0.9, "privacy": 0.1 },
    "evaluation_time_ms": 0.3
  },
  "approval_state": {
    "status": "none",
    "approval_id": null,
    "decided_by": null,
    "decided_at": null
  },
  "status": "success",
  "data": { "order_id": "ord_m3n4o5p6", "estimated_delivery": "2026-04-03T19:30:00Z" },
  "error": null,
  "error_detail": null,
  "execution_time_ms": 234,
  "idempotency_key": "cart_q7r8s9t0",
  "allowed_next_actions": [
    {
      "kind": "capability",
      "name": "order.track",
      "reason": "Track delivery status",
      "requires_approval": false,
      "confidence": 0.95
    },
    {
      "kind": "capability",
      "name": "order.cancel",
      "reason": "Cancel if needed within 5 minutes",
      "requires_approval": true,
      "confidence": 0.3
    }
  ],
  "rendered": "Order ord_m3n4o5p6 placed. Estimated delivery: 7:30 PM.",
  "format_hint": "text",
  "audit_correlation_id": "corr_u1v2w3x4",
  "actor": { "type": "agent", "agent_id": "agent_y5z6", "session_id": "sess_i9j0k1l2" },
  "timestamp": "2026-04-03T18:45:12.456Z"
}
```

---

## Engineering Invariants

These are non-negotiable across all implementations:

1. Every capability execution is policy-evaluated before side effects.
2. Every workflow step has persisted state before transition.
3. Every step completion produces an audit entry.
4. Every approval-gated action blocks until approval is resolved.
5. Every execution response exposes allowed next actions.
6. Every session is resumable across process restarts.
7. Every execution event is attributable to agent, human, or system actor.

---

## Documentation

| Resource | Description |
|----------|-------------|
| [spec/](spec/) | Protocol JSON schemas -- the source of truth |
| [docs/](docs/) | Guides, concepts, API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design decisions |
| [STATUS.md](STATUS.md) | Current implementation state and detailed roadmap |
| [ROADMAP.md](ROADMAP.md) | High-level roadmap |
| [rfcs/](rfcs/) | Protocol change proposals |
| [examples/](examples/) | Working reference applications |

---

## Contributing

See [governance/CONTRIBUTING.md](governance/CONTRIBUTING.md) for the full contribution process. AICP uses spec-first development: protocol changes must be documented in `/spec` before runtime implementation.

- [Code of Conduct](governance/CODE_OF_CONDUCT.md)
- [Issue Tracker](https://github.com/aicp-ai/aicp/issues)

---

## License

AICP is licensed under the [Apache 2.0 License](LICENSE).

---

<div align="center">

**The protocol layer for the agentic web.**

[Spec](spec/) -- [Docs](docs/) -- [Status](STATUS.md) -- [Contributing](governance/CONTRIBUTING.md)

</div>
