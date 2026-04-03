# AICP -- Current State

> **Version:** 0.3.0 | **Date:** 2026-04-03 | **Compliance Level:** 4 (AI Planning Support) — Phase 2 complete

---

## Product Definition

AICP is the Agentic Web Operating System -- the protocol, runtime, memory, governance, perception, execution, and federation layer that turns the human web into an agent-operable web. The current release is v0.3.0, a Python reference implementation at Compliance Level 3 (Event-Driven Orchestration) with full governance, planner, judge, memory system, intent router, cognitive protocols, parallel/loop/subflow/event-driven workflow execution, YAML DSL round-trip, 11 JSON schemas, 8 runtime services, and 692 passing tests. Phase 2 (Orchestration) is complete. Everything described below as "built" is tested and working. Everything described as "planned" does not exist yet.

---

## What is Built (v0.3.0)

### Spec

9 JSON schemas in `/spec/schemas/`:

| Schema | File | Purpose |
|--------|------|---------|
| Capability | `capability.schema.json` | 5 kinds (action, query, workflow, async_action, batch_action), input/output schemas, side-effect classification, auth requirements |
| Workflow | `workflow.schema.json` | Sequential steps, approval checkpoints, compensation/rollback, state persistence |
| Workflow DSL | `workflow-dsl.schema.json` | YAML-compatible DSL for defining workflows with branches, events, parallel steps |
| Policy | `policy.schema.json` | Effects: allow/deny/ask/limit, condition matching, risk inference |
| Execution Result | `execution-result.schema.json` | Canonical execution envelope with status, data, error, allowed_next_actions |
| Approval Request | `approval-request.schema.json` | Risk assessment, impact summary, blast radius estimation |
| Approval Decision | `approval-decision.schema.json` | Approve/deny with reason, decided_by, decided_at |
| Audit Entry | `audit-entry.schema.json` | Append-only journal entry with correlation IDs |
| Session | `session.schema.json` | Session identity, trust tier, state, resumable flag |
| Discovery | `discovery.schema.json` | `/.well-known/aicp` response contract |
| Error | `error.schema.json` | Structured error with code, message, recovery hints |

**Known spec gaps:**
- No enforcement semantics for `often_follows`. The field exists on the capability contract but has no defined behavior -- does it affect ranking, pre-fetching, planner behavior? Needs a spec note.
- No workflow-level `compensation_policy`. Compensation exists at step level but not workflow level. If a workflow fails before reaching a step with declared compensation, earlier steps have no compensation path.
- Policy schema migration path to OPA/Cedar WASM not yet documented in an RFC.
- No enforcement semantics for `often_follows`. The field exists on the capability contract but has no defined behavior -- does it affect ranking, pre-fetching, planner behavior? Needs a spec note.

### Runtime Services

8 services, all complete:

| Service | Lines | Status | Details |
|---------|-------|--------|---------|
| Execution Service | -- | Complete | HTTP execution, session attachment, interaction context, persistence, resume after approval |
| Approval Service | 619 | Complete | Intent matching, review packets with impact analysis, blast radius estimation, compliance flags |
| Workflow Service | 697 | Complete | Step execution, resume, timeline, compensation, audit integration |
| Session Service | 247 | Complete | OAuth refresh, health status, mark_used, tenant isolation |
| Discovery Service | 571 | Complete | Ranking with keyword scoring, semantic similarity (keyword co-occurrence), graph building |
| Audit Service | 104 | Complete | Append-only journal, filtered listing, correlation IDs |
| Interaction Service | 134 | Complete | CRUD, execution recording, session linking |
| Provider Health | 350 | Complete | Aggregated health, auth/network failure tracking, latency monitoring |

### API Surface

30+ endpoints across 13 route groups:

| Endpoint Group | Endpoints | Purpose |
|----------------|-----------|---------|
| `/v1/execute` | POST | AI action endpoint with session redaction, continuation hints, fix hints |
| `/v1/capabilities/rank` | POST | Ranked discovery with keyword scoring |
| `/v1/sessions` | CRUD | Full lifecycle: create, list, get, refresh, revoke |
| `/v1/interactions` | CRUD | Interaction management with session linking |
| `/v1/workflows` | Create, execute, resume | Workflow lifecycle |
| `/v1/approvals` | List, get, find-by-intent | Approval queue |
| `/v1/executions` | List | Execution history |
| `/discover` | GET | Capability discovery document |
| `/.well-known/aicp` | GET | Well-known discovery endpoint |
| `/approvals/*` | CRUD, decide, review-packet, find-by-intent | Full approval lifecycle |
| `/workflows/*` | CRUD, detail, timeline, execute, resume | Full workflow lifecycle |
| `/history` | GET | Audit log |
| `/providers/health` | GET | Provider health aggregation |
| `/console` | GET | Agent dashboard UI (840 lines HTML) |

### Persistence

3 backends, all implementing the full `RuntimeStore` interface:

| Backend | Lines | Details |
|---------|-------|---------|
| In-Memory | 143 | Full RuntimeStore interface, suitable for development and testing |
| File (JSON/JSONL) | 245 | Atomic writes, JSONL audit trail, suitable for single-node deployment |
| SQLite | 240 | WAL mode, 7 tables, suitable for production single-node |

### CLI

28 commands:

| Command | Subcommands | Purpose |
|---------|-------------|---------|
| `aicp run` | -- | Execute capability with inline approval prompt, `--yes`, `--no-input`, `--verbose` |
| `aicp dev` | -- | Dev server with mounted app support, hot reload |
| `aicp scan` | -- | OpenAPI capability discovery |
| `aicp appr` | `ls`, `show`, `ok`, `no` | Approval queue management |
| `aicp test` | -- | Integration test suite |
| `aicp bootstrap` | -- | Scaffold AICP config for existing app |
| `aicp preview` | -- | Preview capability details |
| `aicp import` | `--curl`, `--har`, `--openapi`, `--postman` | Import capabilities from external formats |
| `aicp policy` | `safe`, `ask`, `deny`, `approve`, `protect`, `limit` | Policy management shortcuts |

### Adapters

| Adapter | Type | Status | Details |
|---------|------|--------|---------|
| FastAPI | Framework | **Working** | `mount_aicp(app)` adds all AICP routes |
| MCP Server (`mcp/`) | Protocol | **Working** | Exposes AICP capabilities outward to MCP clients |
| MCP Adapter (`adapters/protocol/mcp/`) | Protocol | **Working** | Lets AICP consume MCP tools as capabilities |
| OpenAPI | Protocol | **Working** | `aicp scan --openapi` imports capabilities |
| cURL | Importer | **Working** | `aicp import --curl` converts cURL commands |
| HAR | Importer | **Working** | `aicp import --har` converts HTTP archives |
| Postman | Importer | **Working** | `aicp import --postman` converts Postman collections |
| HTTP | Protocol | **Empty** | Directory exists, no implementation |
| GraphQL | Protocol | **Empty** | Directory exists, no implementation |
| WebSocket | Protocol | **Empty** | Directory exists, no implementation |
| Express | Framework | **Empty** | Directory exists, no implementation |
| NestJS | Framework | **Empty** | Directory exists, no implementation |
| Next.js | Framework | **Empty** | Directory exists, no implementation |
| Spring Boot | Framework | **Empty** | Directory exists, no implementation |
| LangChain | Agent | **Empty** | Directory exists, no implementation |
| LangGraph | Agent | **Empty** | Directory exists, no implementation |
| CrewAI | Agent | **Empty** | Directory exists, no implementation |

### SDKs

| SDK | Status | Details |
|-----|--------|---------|
| TypeScript Core | Built (L0) | Has `dist/`, `package.json`, `tsconfig`. Capability Discovery only. |
| TypeScript Runtime | Skeleton | `src/` only, no implementation |
| TypeScript Client | Skeleton | `src/` only, no implementation |
| Python SDK | Skeleton | Directory exists, no package definition |

**Gap:** TypeScript Core SDK is at L0 while Python runtime is at L2. See ARCHITECTURE.md Section 12 for implications on Phase 3 adapter planning.

### Tests

| Area | Scope | Status |
|------|-------|--------|
| Core | Capability, approval, schemas, adapters, benchmarks | 445 passing |
| Runtime | Services, server, persistence | All passing |
| CLI | Commands, execute, dev, scan, import, registry | All passing |

### UI

Agent console at `/console` -- 840 lines of self-contained HTML. Provides execution monitoring, approval management, and capability browsing. This is a development/debugging tool, not the v1.0.0 supervision dashboard.

---

## 20-Module Status Matrix

This is the canonical module list. See ARCHITECTURE.md Section 3 for the same table. See README.md for the condensed version.

| # | Module | Plane | v0.1.1 Status | What Exists | What v1.0.0 Needs |
|---|--------|-------|---------------|-------------|-------------------|
| 1 | Principal and Org Control | Governance | **Not started** | Nothing | Identity hierarchy, org boundaries, delegation chains, principal attribution |
| 2 | Identity and Trust | Governance | **Partial** | Session tokens, basic auth | DID-based auth, trust tiers 0-4, credential verification, trust decay |
| 3 | Capability Registry | Capability | **Complete (L2)** | In-memory, file, SQLite stores; 5 kinds; schema validation | Distributed CRDT registry, 50k+ capabilities via domain packs + federation |
| 4 | Tool Runtime | Execution | **Complete (L2)** | Sync invocation, result normalization, persistence | Three execution classes, sandboxing, resource locks, idempotency engine |
| 5 | Workflow Engine | Workflow | **Complete (L3)** | Sequential + compensation, approval checkpoints, state persistence, parallel steps (fork/join), event-driven wait/resume, YAML DSL, loop support (for-each/while), subflow invocation, `compensation_policy` at workflow level | -- |
| 6 | Perception and Signal Layer | Signal / Perception | **Not started** | Nothing | DOM observers, a11y tree, screenshots, behavioral signals, sub-ms event ingestion |
| 7 | Human Cognitive Protocols | Supervision | **Partial** | Approval CLI + API, review packets | 5-view dashboard, risk visualization, replay debugger, policy editor |
| 8 | AI Plane | AI | **Complete (L4)** | Planner (`AICPlanner`), judge (`AICJudge`), intent router (`IntentRouter`), 5 cognitive protocols (UX, SWE, Ops, Research, Finance), `/v1/plan`, `/v1/judge`, `/v1/route` endpoints | Code intelligence DB, semantic memory retrieval |
| 9 | Memory System | AI | **Complete (L4)** | 5-layer `MemoryStore` (working, episodic, semantic, skill, environmental), `MetaMemory` token budget manager, `MemorySnapshot`, session-persisted memory via `SessionService.update_memory/get_memory` | Encrypted storage, semantic retrieval with embeddings |
| 10 | Code Intelligence DB | AI | **Not started** | Nothing | AST indexing, symbol graph, call-chain analysis, code-aware context building |
| 11 | Crawl / Map / Discovery Engine | Capability | **Partial** | Keyword scoring + co-occurrence similarity | Semantic retrieval with embeddings, web crawler, 800k+ service scanner |
| 12 | Governance and Policy | Governance | **Complete (L2)** | JSON policy objects, allow/deny/ask/limit effects | Compiled WASM policies (OPA/Cedar), trust tiers, risk scoring, anomaly detection, compliance layers |
| 13 | Execution Engine | Execution | **Complete (L2)** | Synchronous execution, result normalization | Three classes (realtime <5ms, transactional/saga, event-driven/wait), idempotency, resource locks |
| 14 | Multi-Agent Hierarchy | Multi-Agent | **Not started** | Nothing | 4-tier hierarchy (orchestrator, specialist, worker, supervisor), 40 specialist types |
| 15 | Agent Communication Bus | Multi-Agent | **Not started** | Nothing | Typed message passing, pub/sub channels, coordination protocols |
| 16 | Federation and Agentic WWW | Federation | **Minimal** | `/.well-known/aicp` endpoint | CRDT sync, DID auth, push/pull discovery, regional mirrors, 800k scanner |
| 17 | Human Web Compatibility | Perception | **Not started** | Nothing | Browser automation fallback, form filling, navigation, legacy app support |
| 18 | Audit / Replay / Observability | Supervision | **Partial** | Append-only journal, filtered listing, correlation IDs | Replay debugger, distributed tracing, live feed, streaming |
| 19 | Learning / Drift / Growth | Learning | **Not started** | Nothing | Skill mining, policy learning, drift detection, autonomy calibration |
| 20 | Domain Packs and Benchmarks | Learning | **Not started** | Nothing | Pre-built capability sets (e-commerce, fintech, healthcare, devops, CRM, ERP), evaluation suites |

**Summary:** 7 modules complete (5 at L2, 2 at L4), 4 modules partial, 9 modules not started.

---

## Compliance Level Status

| Level | Name | Status | What's Implemented | What's Missing |
|-------|------|--------|--------------------|----------------|
| 0 | Capability Discovery | **Complete** | Registry, schema validation, basic execution | -- |
| 1 | Governed Execution | **Complete** | Policy evaluation, approval checkpoints, audit trail, session management | -- |
| 2 | Resumable Workflows | **Complete** | Sequential workflows, compensation, state persistence, resume after approval | -- |
| 3 | Event-Driven Orchestration | **Complete** | Parallel steps (fork/join, fail_fast/wait_all), event-driven wait/resume (`wait_for_event`), timeout branching, loop support (for-each/while), subflow invocation, YAML DSL round-trip, L3 conformance tests | -- |
| 4 | AI Planning Support | **Complete** | Planner, judge, intent router, context budget manager, 5 cognitive protocols, `allowed_next_actions` schema, L4 HTTP conformance tests | -- |
| 5 | Full Orchestration | **Not started** | -- | Multi-agent coordination, subflows, cross-flow events, federation, supervision console |

---

## Phased Build Order

Each phase maps to a specific version. See ROADMAP.md for full details per phase.

| Phase | Version | Focus | Key Deliverables | Target Compliance |
|-------|---------|-------|------------------|-------------------|
| 0 | 0.1.1-alpha | Foundation | Spec, runtime, CLI, persistence, adapters, console, tests | L2 (complete) |
| 1 | 0.2.0 | AI Core | Planner, judge, memory/context builder, intent router, cognitive protocols | L4 |
| 2 | 0.3.0 | Orchestration | YAML DSL, event-driven flows, parallel/loop, subflows | L3+L4 |
| 3 | 0.4.0 | Agent Integration | LangChain, LangGraph, CrewAI adapters, food ordering reference flow | L4 |
| 4 | 0.5.0 | Perception | a11y tree, DOM observation, screenshots, signal bus | L4 |
| 5 | 0.6.0 | Multi-Agent | 4-tier hierarchy, communication bus, task delegation | L5 |
| 6 | 0.7.0 | Federation | CRDT registries, DID auth, push/pull discovery | L5 |
| 7 | 0.8.0 | Learning | Skill mining, policy learning, drift detection, domain packs | L5 |
| 8 | 0.9.0 | Production | Encrypted sessions, WASM policies, risk scoring, multi-tenant | L5 |
| 9 | 1.0.0 | Agentic Web OS | Complete 11-plane architecture, stable protocol | L5 |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Tests Passing | 692 |
| API Endpoints | 30+ |
| Runtime Services | 8 |
| Persistence Backends | 3 |
| CLI Commands | 28 |
| Working Adapters | 6 (+ MCP server) |
| Empty Adapter Dirs | 11 |
| JSON Schemas | 11 |
| Compliance Level | 4 (of 5), L3 complete |
| Modules Complete | 7 (of 20) |
| Modules Partial | 4 (of 20) |
| Modules Not Started | 9 (of 20) |
| Lines of Code | ~15,000+ |

---

## Engineering Rules

Non-negotiable across all implementations:

1. Every capability must be deterministic at interface level.
2. Every side effect must be logged.
3. Every action must be replayable.
4. Every risky action must be policy-gated.
5. Every workflow must be resumable.
6. Every flow must be idempotent where possible.
7. Every execution must expose `allowed_next_actions`.

---

## Known Spec Gaps

These are structural gaps in the current v0.1.1-alpha spec that must be resolved before v0.2.0:

### 1. `often_follows` Enforcement Semantics

The `often_follows` field on the capability contract is useful for discovery but has no defined enforcement semantics. Does a capability appearing in `often_follows` get pre-fetched? Does it rank higher in `allowed_next_actions`? Does it affect planner behavior? This needs a spec note defining the behavioral contract, or it will be interpreted differently by every implementation.

### 2. Workflow-Level Compensation Policy

The food order workflow example in ARCHITECTURE.md shows compensation on `orders.place` at the step level. But if a workflow fails mid-execution before reaching a step with declared compensation, earlier completed steps have no compensation path. The workflow schema needs a `compensation_policy` field at the workflow root: either `automatic` (reverse all completed steps in reverse order) or `explicit` (only steps with declared compensation are compensated).

### 3. Policy Schema Migration Path

The current JSON policy schema is the v0.x format. The architecture doc describes OPA/Cedar compilation to WASM as the v1.0.0 target. The migration path from JSON policies to compiled WASM policies must be documented in an RFC before contributors build tooling against the JSON format that will need to be replaced.

---

## Recent Changes (2026-04-03)

### Phase 2 Complete — v0.3.0 / Compliance Level 3

- Wired `LoopStepExecutor` into `DefaultWorkflowRuntime`: for-each (items_variable), while (exit_condition), max_iterations cap, do-while semantics
- Wired `SubflowExecutor` into `DefaultWorkflowRuntime`: creates child workflow via parent runtime, drives to completion, propagates failures
- Added `publish_event(workflow_id, name, payload)` HTTP endpoint (`POST /workflows/{workflow_id}/events`)
- Added `compensation_policy` field to workflow schema
- Added 17 L3 conformance tests (parallel, wait_event, loop, subflow, DSL round-trip)
- Fixed `SubflowExecutor` infinite loop: checks `child_wf.is_complete` before entering polling loop
- Fixed `FakeProvider.execute()` signature in integration tests to accept 3rd positional `context` arg
- Fixed `WorkflowDSL` → `WorkflowDSLParser` import in conformance tests
- Fixed `provider.call_count` → `len(provider.calls)` in loop integration tests
- Total tests: 692 (was 638 at v0.2.0)

### Phase 2 In Progress — v0.3.0-dev / Orchestration

- Wired `DefaultWorkflowRuntime` to dispatch `type:parallel` steps to `ParallelStepExecutor` (fail_fast + wait_all join strategies)
- Wired `DefaultWorkflowRuntime` to dispatch `type:wait_event` steps to `EventWaiter` (with timeout)
- Added `publish_event(workflow_id, name, payload)` public API to `DefaultWorkflowRuntime`
- Relaxed `create_workflow()`: parallel/wait_event/branch/loop steps no longer require `capability_name`
- DSL key compatibility: reads both `wait_for_event` / `parallel_failure_policy` (DSL keys) and `event_name` / `failure_policy` (direct keys)
- Added 16 new runtime parallel integration tests (`test_runtime_parallel_integration.py`)
- Added 11 new DSL→runtime integration tests (`test_dsl_runtime_integration.py`)
- Total tests: 638 (was 611 at v0.2.0)

### Phase 1 Complete — v0.2.0 / Compliance Level 4

- Implemented `AICPlanner` with `PlanStep` / `PlannerOutput` models; POST `/v1/plan` endpoint
- Implemented `AICJudge` with `JudgeError`; POST `/v1/judge` endpoint
- Implemented `IntentRouter` with `RoutingDestination`; POST `/v1/route` endpoint
- Implemented 5-layer `MemoryStore` (working, episodic, semantic, skill, environmental) with `MetaMemory` token budget manager and `MemorySnapshot`
- Added 5 cognitive protocols: UX, SWE, Ops, Research, Finance
- Added `SessionService.update_memory` / `get_memory` for cross-session memory persistence
- Added 26 L4 HTTP conformance tests (plan response, judge response, route response, plan-judge round-trip)
- Total tests: 611 (was 445 at v0.1.1-alpha)
- Updated STATUS.md, ARCHITECTURE.md, AGENTS.md to v0.2.0 / CL4 framing

### v0.1.1-alpha Baseline (previous session)

- Rewrote README.md for v1.0.0 Agentic Web OS framing (11 planes, 20 modules)
- Rewrote ARCHITECTURE.md with full 10-plane architecture, execution contract, protocol invariants
- Rewrote STATUS.md with 20-module status matrix and known spec gaps
- Reconciled execution envelope (README now matches ARCHITECTURE canonical version)
- Reconciled 20-module tables (README canonical, ARCHITECTURE references same table)
- Added MCP server vs MCP adapter disambiguation
- Added TypeScript SDK compliance lag note
- Fixed phase-to-version mapping across all docs
- Added `session.schema.json` and `workflow-dsl.schema.json` (spec now has 11 schemas)
- Added full fixture coverage for all 11 schemas (valid + invalid fixtures in `spec/tests/`)
- Updated test count from 172 to 445 (tests were already passing; STATUS.md was stale)
