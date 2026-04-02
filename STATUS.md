# AICP — Current State & Roadmap

**Date:** 2026-04-01  
**Version:** 0.1.0-alpha

---

## Product Definition

> **AICP is an AI-first application control plane that lets agents operate real apps through structured capabilities, stateful workflows, policy-gated execution, and human supervision.**

Instead of humans clicking through apps, AICP turns applications into structured action spaces that AI agents can safely operate end-to-end.

### Mental Model

AICP sits between:
1. **LLM / agent** — the "user" of the app
2. **Application capabilities** — structured, AI-safe actions
3. **Workflow engine** — multi-step orchestration
4. **State/session store** — resumable execution context
5. **Human approval layer** — governance, not friction
6. **UX plane** — monitoring, intervention, replay, debugging

The frontend is not "for humans to do the task." It is **"for humans to supervise the AI doing the task."**

---

## Architecture Planes

| Plane | Purpose | Key Components |
|-------|---------|----------------|
| **Control Plane** | Registry, policy, orchestration | Capability registry, workflow registry, policy engine, approval service, execution orchestrator, session manager |
| **Data Plane** | Actual backend services | REST APIs, databases, external services |
| **AI Plane** | Agent reasoning | Planner, executor, judge, memory/context builder, tool selection layer |
| **UX Plane** | Human supervision | Operator dashboard, approval UI, replay debugger, workflow builder, audit logs |

---

## What We've Built ✅

### Core Protocol (100% Complete)

| Component | Status | Details |
|-----------|--------|---------|
| **JSON Schema Spec** | ✅ Complete | 9 schemas: capability, workflow, policy, execution-result, approval-request, approval-decision, audit-entry, discovery, error |
| **Capability Model** | ✅ Complete | 5 kinds (action, query, workflow, async_action, batch_action), input/output schemas, side-effect classification, auth requirements |
| **Policy Engine** | ✅ Complete | Effects: allow/deny/ask/limit, condition matching, risk inference |
| **Executor** | ✅ Complete | Deterministic execution, result normalization, approval routing, continuation hints |
| **Workflow Runtime** | ✅ Complete | Sequential steps, approval checkpoints, compensation/rollback, state persistence |
| **Approval System** | ✅ Complete | CRUD, decisions, intent matching, review packets, blast radius estimation, compliance flags |
| **Session Management** | ✅ Complete | Create/refresh/revoke, OAuth flow, health tracking, tenant isolation |
| **Audit Trail** | ✅ Complete | Append-only journal, filtered listing, correlation IDs |

### Runtime Services (100% Complete)

| Service | Status | Details |
|---------|--------|---------|
| **Execution Service** | ✅ Complete | HTTP execution, session attachment, interaction context, persistence, resume after approval |
| **Approval Service** | ✅ Complete | 619 lines, intent matching, review packets with impact analysis |
| **Workflow Service** | ✅ Complete | 697 lines, step execution, resume, timeline, compensation, audit integration |
| **Session Service** | ✅ Complete | 247 lines, OAuth refresh, health status, mark_used |
| **Discovery Service** | ✅ Complete | 571 lines, ranking with keyword scoring, semantic similarity (keyword co-occurrence), graph building |
| **Audit Service** | ✅ Complete | 104 lines, append-only, filtered listing |
| **Interaction Service** | ✅ Complete | 134 lines, CRUD, execution recording, session linking |
| **Provider Health** | ✅ Complete | 350 lines, aggregated health, auth/network failure tracking, latency |

### API Surface (100% Complete)

| Endpoint Group | Status | Endpoints |
|----------------|--------|-----------|
| **`/v1/execute`** | ✅ Complete | AI action endpoint with session redaction, continuation hints, fix hints |
| **`/v1/capabilities/rank`** | ✅ Complete | Ranked discovery with keyword scoring |
| **`/v1/sessions`** | ✅ Complete | Full lifecycle: create/list/get/refresh/revoke |
| **`/v1/interactions`** | ✅ Complete | CRUD with session linking |
| **`/v1/workflows`** | ✅ Complete | Create, execute, resume |
| **`/v1/approvals`** | ✅ Complete | List, get, find-by-intent |
| **`/v1/executions`** | ✅ Complete | History listing |
| **`/discover`** | ✅ Complete | Capability discovery document |
| **`/.well-known/aicp`** | ✅ Complete | Well-known discovery |
| **`/approvals/*`** | ✅ Complete | CRUD, decide, review-packet, find-by-intent |
| **`/workflows/*`** | ✅ Complete | CRUD, detail, timeline, execute, resume |
| **`/history`** | ✅ Complete | Audit log |
| **`/providers/health`** | ✅ Complete | Provider health aggregation |
| **`/console`** | ✅ Complete | Agent dashboard UI (840 lines HTML) |

### CLI (100% Complete)

| Command | Status | Details |
|---------|--------|---------|
| **`aicp run`** | ✅ Complete | Execute with inline approval prompt, --yes, --no-input, --verbose flags |
| **`aicp dev`** | ✅ Complete | Dev server with mounted app support, hot reload |
| **`aicp scan`** | ✅ Complete | OpenAPI capability discovery |
| **`aicp appr`** | ✅ Complete | Approval queue: ls, show, ok, no |
| **`aicp test`** | ✅ Complete | Integration test suite |
| **`aicp bootstrap`** | ✅ Complete | Scaffold AICP config for existing app |
| **`aicp preview`** | ✅ Complete | Preview capability details |
| **`aicp import`** | ✅ Complete | Import from curl, HAR, OpenAPI, Postman |
| **`aicp policy`** | ✅ Complete | safe, ask, deny, approve, protect, limit shortcuts |

### Persistence (100% Complete)

| Backend | Status | Details |
|---------|--------|---------|
| **In-Memory** | ✅ Complete | 143 lines, full RuntimeStore interface |
| **File (JSON)** | ✅ Complete | 245 lines, atomic writes, JSONL audit |
| **SQLite** | ✅ Complete | 240 lines, WAL mode, 7 tables |

### Adapters (Partial)

| Adapter | Status | Details |
|---------|--------|---------|
| **FastAPI** | ✅ Complete | mount_aicp, capability mapping, discovery endpoint |
| **MCP** | ✅ Complete | Protocol adapter with tests |
| **OpenAPI** | ✅ Complete | Protocol adapter with tests |
| **cURL Import** | ✅ Complete | Importer with tests |
| **HAR Import** | ✅ Complete | Importer with tests |
| **Postman Import** | ✅ Complete | Importer with tests |
| **HTTP** | ❌ Empty | Directory exists, no implementation |
| **GraphQL** | ❌ Empty | Directory exists, no implementation |
| **WebSocket** | ❌ Empty | Directory exists, no implementation |
| **Express** | ❌ Empty | Directory exists, no implementation |
| **NestJS** | ❌ Empty | Directory exists, no implementation |
| **Next.js** | ❌ Empty | Directory exists, no implementation |
| **Spring Boot** | ❌ Empty | Directory exists, no implementation |
| **LangChain** | ❌ Empty | Directory exists, no implementation |
| **LangGraph** | ❌ Empty | Directory exists, no implementation |
| **CrewAI** | ❌ Empty | Directory exists, no implementation |

### SDKs (Partial)

| SDK | Status | Details |
|-----|--------|---------|
| **TypeScript Core** | ✅ Built | Has dist/, package.json, tsconfig |
| **Python SDK** | ❌ Skeleton | Directory exists, no package definition |
| **TypeScript Runtime** | ❌ Skeleton | src/ only |
| **TypeScript Client** | ❌ Skeleton | src/ only |

### Tests (100% Passing)

| Area | Tests | Status |
|------|-------|--------|
| **Core** | Capability, approval, schemas, adapters, benchmarks | ✅ 172 passing |
| **Runtime** | Services, server, persistence | ✅ All passing |
| **CLI** | Commands, execute, dev, scan, import, registry | ✅ All passing |

---

## What's Left to Build 🚧

### High Priority

| Feature | Plane | Why It Matters | Effort |
|---------|-------|----------------|--------|
| **AI Planner** | AI | Selects next valid action from policy-constrained options | Large |
| **AI Judge** | AI | Evaluates if result is sufficient, failed, unsafe, or ambiguous | Large |
| **AI Memory/Context Builder** | AI | Builds working memory from execution history | Large |
| **YAML/JSON Workflow DSL** | Control | Clean way to define flows without code | Medium |
| **Event-Driven Async Flows** | Control | Wait-for-event, resume-on-event, timeout branching | Large |
| **LangChain/LangGraph Adapters** | Connect | Bridge to major AI agent frameworks | Medium |
| **Food Ordering Reference Flow** | Examples | Prove end-to-end autonomous operation | Medium |

### Medium Priority

| Feature | Plane | Why It Matters | Effort |
|---------|-------|----------------|--------|
| **Parallel Step Execution** | Control | Simultaneous branches (prepare food + assign driver) | Medium |
| **Loop/Iteration Support** | Control | Repeat until condition (add items to cart) | Medium |
| **Dynamic Routing** | Control | Branch based on results (payment failed → retry) | Medium |
| **Subflow Invocation** | Control | Composable workflows | Medium |
| **Threshold-Based Auto-Approval** | Control | Auto-approve below amount, always ask above | Medium |
| **HTTP Protocol Adapter** | Connect | Generic HTTP capability execution | Medium |
| **Idempotency Key Support** | Core | Prevent double-charging on retries | Medium |
| **Failure Recovery Recipes** | Core | Structured retry/fallback patterns | Medium |
| **Risk Scoring Per Action** | Core | Financial, irreversible, privacy risk | Medium |
| **Live Session View** | UX | Real-time execution monitoring | Medium |
| **State Inspector** | UX | Current session/workflow/entity state | Medium |
| **Multi-Tenant Isolation** | Control | Enforce tenant boundaries | Medium |

### Low Priority

| Feature | Plane | Why It Matters | Effort |
|---------|-------|----------------|--------|
| **Approval Memory/Learning** | Control | Auto-approve patterns over time | Small |
| **Replay/Debug Mode** | UX | Step-by-step execution replay | Large |
| **Flow Builder (Visual)** | UX | Drag-drop workflow editor | Large |
| **GraphQL Adapter** | Connect | GraphQL capability mapping | Small |
| **WebSocket Adapter** | Connect | Real-time streaming | Medium |
| **Express/NestJS/Next.js/Spring Boot** | Connect | Framework adapters | Medium each |
| **Capability Graph Visualization** | Core | Visual capability relationships | Medium |
| **Simulation Mode** | Core | Test workflows with fake backends | Large |
| **Natural Language → Workflow Compiler** | AI | "Order my usual dinner" → workflow | Large |
| **Parent/Child Workflows** | Control | Multi-flow orchestration | Medium |
| **Cross-Flow Event Passing** | Control | Event sharing between workflows | Medium |

---

## Build Order Recommendation

### Phase 1: AI Execution Core (Now)
1. **Planner** — Next valid action selection from capability graph
2. **Judge** — Result evaluation (success/failure/unsafe/ambiguous)
3. **Memory Builder** — Session context from execution history

### Phase 2: Workflow DSL & Events
4. **YAML Workflow DSL** — Define flows declaratively
5. **Event-Driven Flows** — Wait-for-event, timeout, resume
6. **Parallel + Loop Support** — Complex flow patterns

### Phase 3: Agent Integration
7. **LangChain Adapter** — Bridge to LangChain tools
8. **LangGraph Adapter** — Bridge to LangGraph state machines
9. **Food Ordering Demo** — End-to-end reference flow

### Phase 4: UX Plane
10. **Live Session View** — Real-time monitoring
11. **State Inspector** — Working memory visualization
12. **Replay Debugger** — Step-by-step execution replay

### Phase 5: Production Hardening
13. **Idempotency Keys** — Safe retries
14. **Risk Scoring** — Per-action risk assessment
15. **Threshold Auto-Approval** — Smart governance
16. **Multi-Tenant Enforcement** — Production isolation

---

## Non-Negotiable Engineering Rules

1. Every capability must be deterministic at interface level
2. Every side effect must be logged
3. Every action must be replayable
4. Every risky action must be policy-gated
5. Every workflow must be resumable
6. Every flow must be idempotent where possible
7. Every execution must expose "allowed next actions"

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **Tests Passing** | 172 |
| **API Endpoints** | 30+ |
| **Runtime Services** | 8 |
| **Persistence Backends** | 3 |
| **CLI Commands** | 28 |
| **Working Adapters** | 6 |
| **JSON Schemas** | 9 |
| **Code Coverage** | >80% (core) |
| **Lines of Code** | ~15,000+ |

---

## Recent Changes (2026-04-01)

- ✅ Fixed `aicp dev` to properly mount AICP routes on user apps
- ✅ Added inline approval prompt to `aicp run` with --yes, --no-input, --verbose flags
- ✅ Fixed approval auto-resume flow (intent matching working)
- ✅ Updated AGENTS.md with AI-first control plane definition
- ✅ Updated ARCHITECTURE.md with 4-plane architecture
- ✅ Updated README.md with new product definition
- ✅ Created this status document
