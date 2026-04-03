<div align="center">

# AICP

### The Agentic Web Operating System

**The protocol, runtime, memory, governance, and federation layer that turns the human web into an agent-operable web.**

[![CI](https://github.com/Theory903/AICP/actions/workflows/ci.yml/badge.svg)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/Theory903/AICP?label=version&sort=semver)](https://github.com/Theory903/AICP/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-3776AB)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-692%20passing-brightgreen)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Compliance](https://img.shields.io/badge/compliance-Level%203-orange)](STATUS.md)
[![Spec](https://img.shields.io/badge/spec-11%20schemas-purple)](spec/schemas/)

[v0.3.0](https://github.com/Theory903/AICP/releases/tag/v0.3.0) · [Spec](spec/) · [Docs](docs/) · [Status](STATUS.md) · [Roadmap](ROADMAP.md) · [Architecture](ARCHITECTURE.md)

</div>

---

## What is AICP?

AICP (AI Capability Protocol) is an **operating system for autonomous AI agents on the internet**. It provides the full stack — signal ingestion, perception, planning, execution, governance, memory, multi-agent coordination, federation, supervision, and learning — that agents need to operate real applications safely, at scale, across organizational boundaries.

Today's AI agents interact with software through brittle tool calls: untyped function signatures, no governance, no memory, no coordination. This is roughly where networking was before TCP/IP. Every agent framework reinvents capability discovery, policy enforcement, workflow orchestration, and human oversight from scratch. The result is fragile, ungoverned, and unscalable.

AICP replaces this with a layered operating system:

| Plane | Purpose |
|-------|---------|
| **Signal** | Sub-ms event ingestion, dedup, classification, routing |
| **Perception** | a11y tree, DOM observation, screenshots, behavioral signals |
| **AI** | Planner, judge, intent router, memory, cognitive protocols |
| **Capability** | Registry, schema validation, ranked discovery, semantic search |
| **Workflow** | Sequential, parallel, fork/join, sagas, event-driven, loops, subflows |
| **Governance** | Compiled policy engine, trust tiers, risk scoring, approval lifecycle |
| **Execution** | Realtime (<5ms), transactional (saga), event-driven (wait/resume) |
| **Multi-Agent** | Orchestrator/specialist/worker/supervisor hierarchy, communication bus |
| **Federation** | `/.well-known/aicp` discovery, CRDT registries, DID auth |
| **Supervision** | Live feed, approval queue, replay debugger, policy editor |
| **Learning** | Skill mining, policy learning, drift detection, autonomy calibration |

The design principle: **agents are not users with a chatbox**. They are principals operating software at machine speed, and they need an operating system purpose-built for that reality. AICP is that operating system.

---

## Why AICP?

| Dimension | Traditional Tool Calling | AICP |
|-----------|--------------------------|------|
| **Discovery** | Agent guesses which tools exist | Global capability mesh with ranked discovery, semantic search, graph traversal |
| **Input/Output** | Untyped or loosely typed | Strict JSON Schema contracts with validation, side-effect classification, error codes |
| **Governance** | None; agent decides everything | Compiled policy engine: allow/deny/ask/limit per capability, trust tiers, risk scoring |
| **Approval** | Not supported | First-class approval lifecycle with intent matching, blast radius estimation, auto-resume |
| **Workflows** | Agent tracks state manually | Stateful, resumable orchestration: sequential, parallel, fork/join, sagas, compensation, loops, subflows |
| **Memory** | Conversation context window | Structured memory system: working, episodic, semantic, skill, environmental |
| **Multi-Agent** | Ad hoc message passing | Four-tier hierarchy: orchestrator, specialist, worker, supervisor |
| **Observability** | Logs, maybe | Append-only audit trail, replay debugger, live execution feed, correlation IDs |
| **Federation** | Not supported | `/.well-known/aicp` discovery, CRDT registries, DID authentication |
| **Learning** | Static | Skill mining, policy learning, drift detection, autonomy calibration |

---

## Quick Start

AICP v0.3.0 is a Python reference implementation at **Compliance Level 3** (Event-Driven Orchestration) with **692 passing tests**.

### Install

```bash
git clone https://github.com/Theory903/AICP.git
cd AICP
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi
```

### Run

```bash
# Start the AICP dev server
aicp dev

# Execute a capability
aicp run notes.create -i '{"title": "Hello", "body": "World"}'

# Execute with auto-approval
aicp run payments.transfer -i '{"to": "acct_123", "amount": 50}' --yes

# Non-interactive mode (CI/scripts)
aicp run notes.create -i '{"title": "Automated"}' --no-input
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

### Approval Queue

```bash
# List pending approvals
aicp appr ls

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

## Current State (v0.3.0)

### What's Built

| Area | Metric | Details |
|------|--------|---------|
| **Spec** | 11 JSON schemas | capability, workflow, workflow-dsl, policy, execution-result, approval-request, approval-decision, audit-entry, session, discovery, error |
| **Runtime** | 8 services | Execution, approvals, workflows, sessions, discovery, audit, interactions, provider health |
| **API** | 30+ endpoints | 13 route groups including `/v1` AI action surface, `/.well-known/aicp`, `/console` |
| **Persistence** | 3 backends | In-memory, file (JSON/JSONL), SQLite (WAL mode, 7 tables) |
| **CLI** | 28 commands | `run`, `dev`, `scan`, `preview`, `bootstrap`, `import`, `appr`, `policy`, `test` |
| **Adapters** | 6 working | FastAPI, MCP server, MCP adapter, OpenAPI, cURL/HAR/Postman importers |
| **Tests** | 692 passing | Core, runtime, CLI, adapters, conformance (L3+L4) |
| **SDKs** | 1 built | TypeScript Core (built and distributable) |
| **UI** | Agent console | 840-line HTML dashboard at `/console` |

### Compliance Levels

| Level | Name | Status |
|-------|------|--------|
| 0 | Capability Discovery | **Complete** |
| 1 | Governed Execution | **Complete** |
| 2 | Resumable Workflows | **Complete** |
| 3 | Event-Driven Orchestration | **Complete** |
| 4 | AI Planning Support | **Complete** |
| 5 | Full Orchestration | Not started |

### Workflow Capabilities

AICP workflows support:
- **Sequential steps** with approval checkpoints
- **Parallel execution** (fork/join) with `fail_fast` and `wait_all` strategies
- **Event-driven flows** with `wait_for_event` and timeout branching
- **Loops**: for-each (items_variable), while (exit_condition), max_iterations cap
- **Subflows**: child workflow invocation driven to completion
- **Compensation**: step-level and workflow-level rollback policies
- **YAML DSL**: human-readable workflow definitions compiled to runtime objects

---

## Architecture: The 11 Planes

AICP is organized into 11 architectural planes (0-10), each responsible for a distinct operational concern.

| # | Plane | Purpose | Key Capabilities |
|---|-------|---------|------------------|
| 0 | **Signal** | Sub-ms event ingestion | Event bus, webhook receivers, change-data-capture streams |
| 1 | **Perception** | Full sensory coverage | Accessibility tree parsing, DOM observation, state API polling, screenshot capture, behavioral signal extraction |
| 2 | **AI** | Agent cognition | Intent router, planner, judge, memory system, cognitive protocols, context budget management |
| 3 | **Capability** | Global action mesh | Capability registry, schema validation, ranked discovery, semantic search, dependency graph |
| 4 | **Workflow** | Orchestration | Sequential, parallel, fork/join, sagas, event-driven flows, compensation, loops, subflows, approval checkpoints |
| 5 | **Governance** | Governed autonomy | Compiled policy engine, trust tiers, risk scoring, approval lifecycle, compliance enforcement |
| 6 | **Execution** | Three-class runtime | Realtime (<5ms), transactional (with sagas), event-driven (wait/resume) |
| 7 | **Multi-Agent** | Coordination | Orchestrator, specialist, worker, supervisor hierarchy; task delegation, conflict resolution |
| 8 | **Federation** | Agentic WWW | `/.well-known/aicp` discovery, CRDT-based registries, DID authentication, cross-org capability sharing |
| 9 | **Supervision** | Human control tower | Live execution feed, approval queue, replay debugger, policy editor, health dashboard |
| 10 | **Learning** | Continuous improvement | Skill mining, policy learning, drift detection, autonomy calibration, benchmark regression |

---

## The 20 Modules

| # | Module | Plane | Status |
|---|--------|-------|--------|
| 1 | Principal and Org Control | Governance | Not started |
| 2 | Identity and Trust | Governance | Partial (session tokens, basic auth) |
| 3 | Capability Registry | Capability | **Complete (L2)** |
| 4 | Tool Runtime | Execution | **Complete (L2)** |
| 5 | Workflow Engine | Workflow | **Complete (L3)** |
| 6 | Perception and Signal Layer | Signal / Perception | Not started |
| 7 | Human Cognitive Protocols | Supervision | Partial (approval CLI + API) |
| 8 | AI Plane | AI | **Complete (L4)** |
| 9 | Memory System | AI | **Complete (L4)** |
| 10 | Code Intelligence DB | AI | Not started |
| 11 | Crawl / Map / Discovery Engine | Capability | Partial (keyword scoring) |
| 12 | Governance and Policy | Governance | **Complete (L2)** |
| 13 | Execution Engine | Execution | **Complete (L2)** |
| 14 | Multi-Agent Hierarchy | Multi-Agent | Not started |
| 15 | Agent Communication Bus | Multi-Agent | Not started |
| 16 | Federation and Agentic WWW | Federation | Minimal (well-known endpoint) |
| 17 | Human Web Compatibility | Perception | Not started |
| 18 | Audit / Replay / Observability | Supervision | Partial (append-only journal) |
| 19 | Learning / Drift / Growth | Learning | Not started |
| 20 | Domain Packs and Benchmarks | Learning | Not started |

**Summary:** 7 modules complete, 4 partial, 9 not started. See [STATUS.md](STATUS.md) for details.

---

## Repository Structure

```
AICP/
├── spec/                          # Protocol source of truth (JSON schemas)
│   ├── schemas/                   # 11 schema definitions
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
├── mcp/                           # MCP server (exposes AICP outward to MCP clients)
├── apps/
│   └── studio/                    # AICP Studio (control plane UI)
├── examples/                      # Reference applications
├── docs/                          # Human-readable documentation
├── rfcs/                          # Protocol change proposals
└── governance/                    # CONTRIBUTING.md, CODE_OF_CONDUCT.md
```

**Authoritative rule:** `/spec` is the source of truth. If runtime behavior and spec disagree, spec wins.

**MCP disambiguation:** `mcp/` is the **MCP server** (exposes AICP capabilities outward). `adapters/protocol/mcp/` is the **MCP adapter** (lets AICP consume external MCP tools). Both are complete. Opposite directions.

---

## Integrations

### Available

| Integration | Type | Status |
|-------------|------|--------|
| FastAPI | Framework adapter | Working. `mount_aicp(app)` adds all AICP routes. |
| MCP Server | Protocol server | Working. Exposes AICP capabilities to MCP clients. |
| MCP Adapter | Protocol adapter | Working. Consumes external MCP tools as capabilities. |
| OpenAPI | Protocol adapter | Working. `aicp scan --openapi` imports capabilities. |
| cURL | Importer | Working. `aicp import --curl` converts cURL commands. |
| HAR | Importer | Working. `aicp import --har` converts HTTP archives. |
| Postman | Importer | Working. `aicp import --postman` converts collections. |
| TypeScript Core SDK | SDK | Built and distributable. |

### Planned

| Integration | Type | Phase |
|-------------|------|-------|
| LangChain | Agent adapter | 3 (v0.4.0) |
| LangGraph | Agent adapter | 3 (v0.4.0) |
| CrewAI | Agent adapter | 3 (v0.4.0) |
| Express | Framework adapter | 8 (v0.9.0) |
| NestJS | Framework adapter | 8 (v0.9.0) |
| Next.js | Framework adapter | 8 (v0.9.0) |
| Spring Boot | Framework adapter | 8 (v0.9.0) |
| Python SDK | SDK | 2 (v0.3.0) |
| TypeScript Runtime SDK | SDK | 3 (v0.4.0) |
| TypeScript Client SDK | SDK | 3 (v0.4.0) |

---

## Execution Contract

Every capability execution produces a canonical envelope consumed by all planes (UI, planner, judge, audit, replay). Full schema: [`spec/schemas/execution-result.schema.json`](spec/schemas/execution-result.schema.json).

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "orders.place",
  "status": "success",
  "data": { "order_id": "ord_m3n4o5p6" },
  "policy_result": { "effect": "allow", "trust_tier": 2 },
  "allowed_next_actions": [
    { "kind": "capability", "name": "order.track", "requires_approval": false }
  ],
  "actor": { "type": "agent", "agent_id": "agent_y5z6" },
  "timestamp": "2026-04-03T18:45:12.456Z"
}
```

---

## Engineering Invariants

1. Every capability execution is policy-evaluated before side effects.
2. Every workflow step has persisted state before transition.
3. Every step completion produces an audit entry.
4. Every approval-gated action blocks until approval is resolved.
5. Every execution response exposes allowed next actions.
6. Every session is resumable across process restarts.
7. Every execution event is attributable to agent, human, or system actor.

---

## Roadmap

| Phase | Version | Focus | Status |
|-------|---------|-------|--------|
| 0 | **0.1.1-alpha** | Foundation | **Complete** |
| 1 | **0.2.0** | AI Core | **Complete** |
| 2 | **0.3.0** | Orchestration | **Complete** |
| 3 | 0.4.0 | Agent Integration | Not started |
| 4 | 0.5.0 | Perception | Not started |
| 5 | 0.6.0 | Multi-Agent | Not started |
| 6 | 0.7.0 | Federation | Not started |
| 7 | 0.8.0 | Learning | Not started |
| 8 | 0.9.0 | Production | Not started |
| 9 | **1.0.0** | Agentic Web OS | Not started |

See [ROADMAP.md](ROADMAP.md) for full details per phase.

---

## Contributing

AICP uses **spec-first** development: protocol changes must be documented in `/spec` before runtime implementation.

- [Contributing Guide](governance/CONTRIBUTING.md)
- [Code of Conduct](governance/CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Issue Tracker](https://github.com/Theory903/AICP/issues)

### Development

```bash
# Install all packages
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi

# Run tests
python -m pytest packages/ --tb=short -q

# Lint
ruff check . && ruff format --check .
```

---

## License

AICP is licensed under the [Apache 2.0 License](LICENSE).

---

<div align="center">

**The protocol layer for the agentic web.**

[Spec](spec/) · [Docs](docs/) · [Status](STATUS.md) · [Roadmap](ROADMAP.md) · [Contributing](governance/CONTRIBUTING.md)

</div>
