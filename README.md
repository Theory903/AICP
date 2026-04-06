<div align="center">

# AICP

### The Agentic Control Plane for Secure Org Automation

**AICP governs execution. Mammoth is the shell. Together they turn existing software into an auditable, policy-controlled action surface for agents and operators.**

[![CI](https://github.com/Theory903/AICP/actions/workflows/ci.yml/badge.svg)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/Theory903/AICP?label=version&sort=semver)](https://github.com/Theory903/AICP/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-3776AB)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-941%20passing-brightgreen)](https://github.com/Theory903/AICP/actions/workflows/ci.yml)
[![Compliance](https://img.shields.io/badge/compliance-Level%205-green)](STATUS.md)
[![Spec](https://img.shields.io/badge/spec-23%20schemas-purple)](spec/schemas/)

[v1.0.0](https://github.com/Theory903/AICP/releases/tag/v1.0.0) · [Spec](spec/) · [Docs](docs/) · [Status](STATUS.md) · [Roadmap](ROADMAP.md) · [Architecture](ARCHITECTURE.md)

</div>

---

## What is AICP?

AICP (AI Capability Protocol) is the **control plane for secure agentic execution**. It gives organizations a governed way to expose application actions as typed capabilities, run resumable workflows, enforce policy before side effects, hold risky work for approval, and keep every execution attributable and replayable.

The practical product shape in this repository is:

- **AICP** is the control plane: capability registry, workflow runtime, policy engine, approvals, sessions, audit, discovery, and org automation contracts.
- **Mammoth** is the **only primary interaction shell for now**: the operator and agent-facing TUI/CLI for discovery, invocation, supervision, review, and approval.
- **Studio** is not a separate front door; it is control-plane UX that should be embedded into Mammoth over time.

This repo should therefore be read as an **org automation stack** rather than a collection of unrelated agent tools. Mammoth is where work is initiated and supervised. AICP is where work is governed.

Today's AI agents still interact with software through brittle tool calls: loose signatures, weak approval semantics, shallow memory, and almost no organizational controls. Every framework reinvents discovery, policy, orchestration, and audit from scratch. The result is fragile, ungoverned automation.

AICP replaces this with a governed execution model:

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

The design principle is simple: **agents are not users with a chatbox**. They are principals operating software at machine speed, and they need a control plane purpose-built for that reality.

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

### Mammoth-First Product Flow

```bash
# Start the Mammoth shell (primary interaction surface)
cd apps/mammoth
export OPENAI_API_KEY=ollama
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
cargo run -q -p mammoth-cli --bin mammoth -- --model kimi-k2.5:cloud
```

From Mammoth, the operator or agent interacts with the governed AICP runtime. AICP remains the enforcement and orchestration layer behind that shell.

AICP's v1.0.0 feature set delivers complete **L5 orchestration**, backed by **879 passing core/runtime/cli tests**.

### Install

```bash
git clone https://github.com/Theory903/AICP.git
cd AICP
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi
```

### Run the Control Plane

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

# Scan capabilities from an OpenAPI spec file
aicp scan openapi ./openapi.json

# Preview what was discovered
aicp preview payments.transfer
```

### Add Governance

```bash
# Require approval for dangerous capabilities
aicp protect payments.transfer

# Rate-limit an entire namespace
aicp limit "users.*" --rpm 60

# Set blanket policy shortcuts
aicp safe "notes.*"
aicp ask "payments.*"
aicp deny "admin.delete_all"
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

## Current State (v1.0.0)

### What's Built

| Area | Metric | Details |
|------|--------|---------|
| **Spec** | 20 JSON schemas | capability, workflow, workflow-dsl, policy, execution-result, approval-request, approval-decision, audit-entry, session, discovery, error, perception, web-compatibility, federation, learning, domains, ssrf-config, credential, plugin, plugin-manifest, openai-compatible |
| **Runtime** | 8 services | Execution, approvals, workflows, sessions, discovery, audit, interactions, provider health |
| **API** | 30+ endpoints | 13 route groups including `/v1` AI action surface, `/.well-known/aicp`, `/console` |
| **Persistence** | 3 backends | In-memory, file (JSON/JSONL), SQLite (WAL mode, 7 tables) |
| **CLI** | 28 commands | `run`, `dev`, `scan`, `preview`, `bootstrap`, `import`, `appr`, `safe`, `ask`, `deny`, `protect`, `limit`, `test` |
| **Adapters** | 6 working | FastAPI, MCP server, MCP adapter, OpenAPI, cURL/HAR/Postman importers |
| **Tests** | 879 passing | Core, runtime, CLI, adapters, conformance (L5) |
| **SDKs** | 1 built | TypeScript Core (built and distributable) |
| **UI** | Mammoth-first shell + console | Mammoth is the primary shell; `/console` remains a development/debugging supervision surface |
| **Enterprise Features** | 18 tasks | Permission patterns, SSRF guard, sandbox, audit CLI, plugin registry/signing/marketplace, cost estimation, tracing, telemetry, NL workflow, workflow compiler/simulator, flow builder |

### Compliance Levels

| Level | Name | Status |
|-------|------|--------|
| 0 | Capability Discovery | **Complete** |
| 1 | Governed Execution | **Complete** |
| 2 | Resumable Workflows | **Complete** |
| 3 | Event-Driven Orchestration | **Complete** |
| 4 | AI Planning Support | **Complete** |
| 5 | Full Orchestration | **Complete** |

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
| 1 | Principal and Org Control | Governance | **Complete (L2)** |
| 2 | Identity and Trust | Governance | **Complete (L5)** |
| 3 | Capability Registry | Capability | **Complete (L5)** |
| 4 | Tool Runtime | Execution | **Complete (L2)** |
| 5 | Workflow Engine | Workflow | **Complete (L3)** |
| 6 | Perception and Signal Layer | Signal / Perception | **Complete (L5)** |
| 7 | Human Cognitive Protocols | Supervision | **Complete (L5)** |
| 8 | AI Plane | AI | **Complete (L4)** |
| 9 | Memory System | AI | **Complete (L4)** |
| 10 | Code Intelligence DB | AI | **Complete (L4)** |
| 11 | Crawl / Map / Discovery Engine | Capability | **Complete (L4)** |
| 12 | Governance and Policy | Governance | **Complete (L2)** |
| 13 | Execution Engine | Execution | **Complete (L2)** |
| 14 | Multi-Agent Hierarchy | Multi-Agent | **Complete (L5)** |
| 15 | Agent Communication Bus | Multi-Agent | **Complete (L5)** |
| 16 | Federation and Agentic WWW | Federation | **Complete (L5)** |
| 17 | Human Web Compatibility | Perception | **Complete (L5)** |
| 18 | Audit / Replay / Observability | Supervision | **Complete (L5)** |
| 19 | Learning / Drift / Growth | Learning | **Complete (L5)** |
| 20 | Domain Packs and Benchmarks | Learning | **Complete (L5)** |

**Summary:** 20 fully implemented. See [STATUS.md](STATUS.md) for details.

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
│   ├── mammoth/                   # Primary interaction shell (Rust TUI/CLI)
│   └── studio/                    # Legacy or embedded supervision UI seed
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
| OpenAPI | Protocol adapter | Working. `aicp scan openapi ./openapi.json` imports capabilities. |
| cURL | Importer | Adapter package is present in the repo; CLI shortcut is not currently exposed. |
| HAR | Importer | Adapter package is present in the repo; CLI shortcut is not currently exposed. |
| Postman | Importer | Working. `aicp import postman collection.json` converts collections. |
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
| 3 | **0.4.0** | Agent Integration | **Complete** |
| 4 | **0.5.0** | Perception | **Complete** |
| 5 | **0.6.0** | Multi-Agent | **Complete** |
| 6 | **0.7.0** | Federation | **Complete** |
| 7 | **0.8.0** | Learning | **Complete** |
| 8 | **0.9.0** | Production | **Complete** |
| 9 | **1.0.0** | Agentic Web OS | **Complete** |

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
