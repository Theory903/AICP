# AICP Vision

The protocol, runtime, and operating system layer that turns the human web into an agent-operable web.

---

## The Problem

Software has two native surfaces: APIs for developers and UIs for humans. Neither is designed for autonomous agents that must discover actions, evaluate risk, obtain approval, maintain state across failures, and produce auditable outcomes.

The result: agents today operate through brittle tool-calling layers that provide no governance, no workflow memory, no structured error recovery, and no continuation guidance. They can start tasks but cannot safely finish them.

## The Thesis

The internet needs a third surface.

| Surface | Optimized For | Primary Consumer |
|---------|---------------|-----------------|
| API | Developer integration | Backend services |
| UI | Human interaction | End users |
| **Action Surface** | **Agent operation** | **AI agents** |

AICP defines that third surface: the **Action Surface** -- a structured, typed, policy-governed, stateful interface that any agent can discover, reason about, and operate through safely.

## What AICP Solves

Three systemic failures break agent systems in production:

| Failure | Symptom | AICP Solution |
|---------|---------|---------------|
| **Governance gap** | No policy, no approval, no audit | Protocol-native policy engine with trust tiers, risk scoring, approval lifecycle |
| **State gap** | No workflow memory, no resumable execution | Stateful workflows with persistence, compensation, and resume-after-approval |
| **Signal gap** | Weak errors, no repair hints, no next-step guidance | Structured execution envelopes with `allowed_next_actions`, `fix_hint`, error taxonomy |

## Architecture: 11 Planes

AICP is not a tool-calling library. It is an operating system for agent-operable software, organized into 11 architectural planes:

| # | Plane | Purpose |
|---|-------|---------|
| 0 | Signal | Sub-ms event ingestion, dedup, classification, routing |
| 1 | Perception | a11y tree, DOM observation, screenshots, behavioral signals |
| 2 | AI | Planner, judge, intent router, memory, cognitive protocols |
| 3 | Capability | Registry, schema validation, ranked discovery, semantic search |
| 4 | Workflow | Sequential, parallel, fork/join, sagas, event-driven, subflows |
| 5 | Governance | Compiled policy engine, trust tiers, risk scoring, approval lifecycle |
| 6 | Execution | Realtime (<5ms), transactional (saga), event-driven (wait/resume) |
| 7 | Multi-Agent | Orchestrator/specialist/worker/supervisor hierarchy, communication bus |
| 8 | Federation | `/.well-known/aicp` discovery, CRDT registries, DID auth |
| 9 | Supervision | Live feed, approval queue, replay debugger, policy editor |
| 10 | Learning | Skill mining, policy learning, drift detection, autonomy calibration |

## Product Stack

| Layer | Name | Purpose |
|-------|------|---------|
| Protocol | AICP Protocol | The open contract -- JSON schemas, capability kinds, execution envelope, compliance levels |
| Runtime | AICP Runtime | The execution engine -- policy evaluation, workflow orchestration, persistence, session management |
| Connect | AICP Connect | The adoption wedge -- adapters for HTTP, MCP, OpenAPI, FastAPI, cURL, HAR, Postman, LangChain |
| Studio | AICP Studio | The supervision console -- approval dashboard, audit timeline, workflow replay, policy editor |

## Core Beliefs

A **capability** is not a callable function. It is a governed action with:

- Typed inputs and outputs (JSON Schema)
- Policy metadata (risk, trust tier, approval requirements)
- Workflow relevance (step position, prerequisites, compensation)
- Recovery semantics (retry policy, idempotency, compensation handlers)
- Continuation hints (`allowed_next_actions` with confidence scores)
- Auditability (immutable journal entries, correlation IDs, actor attribution)

## Design Principles

| Principle | Meaning |
|-----------|---------|
| Governance is protocol-native | Not middleware, not afterthought -- policy evaluation happens before every side effect |
| Execution is stateful | Every workflow is resumable across process restarts, approval pauses, and failures |
| Errors are actionable | Every failure includes structured codes, fix hints, and retry guidance |
| Signals are structured | Every execution produces the canonical envelope consumed by planner, judge, UI, and audit |
| Adoption is incremental | Zero-code onramp via `aicp scan` and `aicp dev` on existing FastAPI apps |
| Spec is source of truth | If runtime behavior and schema disagree, schema wins |
| Adapters translate only | No business logic in adapters -- they map between AICP and external protocols |

## Adoption Path

AICP Connect is the onramp. Existing systems become agent-operable without rebuilding:

```
OpenAPI spec  ---->  aicp map openapi api.json         ---->  Governed capabilities
FastAPI app   ---->  aicp scan fastapi app:app          ---->  Governed capabilities
Postman       ---->  aicp map postman collection.json   ---->  Governed capabilities
HAR file      ---->  aicp map har session.har           ---->  Governed capabilities
cURL command  ---->  aicp map curl "curl ..."           ---->  Governed capabilities
MCP server    ---->  MCP adapter auto-discovery         ---->  Governed capabilities
```

## Current State

**v0.1.1-alpha** -- Compliance Level 2 (Resumable Workflows). 9 JSON schemas, 8 runtime services, 30+ API endpoints, 3 persistence backends, 28 CLI commands, 6 working adapters, 172 passing tests. See [STATUS.md](../../STATUS.md) for the full inventory.

## Target State

**v1.0.0** -- Compliance Level 5 (Full Orchestration). All 11 planes operational, all 20 modules implemented, multi-agent coordination, federation, perception, learning. See [ROADMAP.md](../../ROADMAP.md) for the phased build order.

## The Long-Term Outcome

If AICP succeeds, every application on the internet exposes three surfaces:

- **APIs** for developers
- **UIs** for humans
- **AICP Action Surfaces** for agents

That is the product.

---

## See Also

- [ACTION_SURFACE.md](ACTION_SURFACE.md) -- The agent-facing surface of software
- [GOVERNANCE.md](GOVERNANCE.md) -- Policy, trust, and approval
- [COMPARISON.md](COMPARISON.md) -- AICP vs MCP, OpenAPI, tool calling
- [ARCHITECTURE.md](../../ARCHITECTURE.md) -- 11-plane system architecture
- [STATUS.md](../../STATUS.md) -- Current implementation state
- [ROADMAP.md](../../ROADMAP.md) -- Phased roadmap to v1.0.0
