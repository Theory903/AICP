# AICP Architecture

> Technical architecture for contributors — the layered protocol and runtime design that powers the Agentic Web Operating System.

---

## Architectural Principles

| Principle | Description |
|-----------|-------------|
| **Spec first** | Protocol contract defined before implementation details. `/spec` is the source of truth. |
| **Framework-agnostic core** | Core domain model must not depend on one backend framework. |
| **Thin adapters** | Adapters translate existing systems into AICP concepts, not reinvent core logic. |
| **Policy as first-class layer** | Permissions, trust tiers, and approvals are part of the schema, not post-processing. |
| **Workflow state is explicit** | Every workflow tracks current step, completed steps, missing inputs — not hidden in prompts. |
| **Fail-closed defaults** | If policy evaluation fails, deny the action. If schema validation fails, reject. |
| **Defense in depth** | Policy checked at API boundary, service layer, and data layer. |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client / Agent                                │
│  (LangChain, CrewAI, Claude, Cursor, custom AI)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Discovery + Planning Layer                         │
│  (Capability Registry, Semantic Search, AI Planner/Judge)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Capability Registry                          │
│  (Store, validate, rank, discover capabilities)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Policy Evaluation Layer                         │
│  (Trust tier, risk scoring, approval gates)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Runtime                              │
│  (Stateful execution, compensation, resume, parallel steps)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Execution Layer                              │
│  (Realtime <5ms, transactional, event-driven)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Underlying APIs / Services / Tools                  │
│  (Backend services, external APIs, databases)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            Result Normalization + Render Layer                   │
│  (Execution envelope, allowed_next_actions, audit trail)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Main Components

### 1. Capability Registry

Stores and serves capability definitions — the atomic semantic actions exposed to AI systems.

| Responsibility | Description |
|---------------|-------------|
| Capability discovery | Enumerate available capabilities |
| Schema validation | Validate input/output schemas against JSON schemas |
| Ranked discovery | Keyword scoring + semantic search |
| Metadata organization | Tags, categories, capability families |

**Key files:**
- `packages/core/src/aicp/capability.py` — Capability domain model
- `packages/runtime/src/aicp_runtime/services/capability_registry.py` — Registry service
- `spec/schemas/capability.schema.json` — Protocol schema

### 2. Policy Engine

Evaluates whether an action is allowed, denied, or requires approval before execution.

| Responsibility | Description |
|---------------|-------------|
| Scope checks | Verify actor permissions |
| Trust tier evaluation | Apply baseline autonomy rules |
| Risk scoring | Compute multi-dimensional risk scores |
| Approval logic | Determine when to pause for human decision |
| Policy effects | `allow`, `deny`, `ask`, `require_approval`, `limit` |

**Key files:**
- `packages/core/src/aicp/policy.py` — Policy domain model
- `packages/runtime/src/aicp_runtime/services/policy_engine.py` — Policy evaluation service
- `spec/schemas/policy.schema.json` — Protocol schema

### 3. Workflow Runtime

Tracks multi-step state with branching, retries, compensation, and approval checkpoints.

| Responsibility | Description |
|---------------|-------------|
| Current step tracking | Where are we in the workflow? |
| Completed steps | What has already executed? |
| Next transitions | What can happen next? |
| Missing inputs | What data is still needed? |
| Resume after approval | Continue from checkpoint after human decision |
| Compensation | Rollback completed steps on failure |

**Key files:**
- `packages/core/src/aicp/workflow.py` — Workflow domain model
- `packages/runtime/src/aicp_runtime/services/workflow_runtime.py` — Workflow execution service
- `spec/schemas/workflow.schema.json` — Protocol schema

### 4. Execution Engine

Runs the selected capability against underlying systems with normalized results.

| Responsibility | Description |
|---------------|-------------|
| Execute action | Invoke the underlying capability |
| Adapt transport | HTTP, MCP, WebSocket, etc. |
| Capture raw response | Get the backend response |
| Return structured results | Produce execution envelope |

**Key files:**
- `packages/runtime/src/aicp_runtime/services/execution_service.py` — Main executor
- `packages/runtime/src/aicp_runtime/services/tool_runtime.py` — Tool invocation
- `spec/schemas/execution-result.schema.json` — Protocol schema

### 5. Approval Service

Manages the human-in-the-loop checkpoint lifecycle.

| Responsibility | Description |
|---------------|-------------|
| Create approval request | Pause execution, create structured request |
| Route to human | CLI inline, REST API, dashboard, Slack/webhook |
| Resolve decision | Approve, reject, modify, delegate, escalate |
| Resume execution | Continue after approval is granted |
| Intent matching | Verify resumed action still makes sense |

**Key files:**
- `packages/runtime/src/aicp_runtime/services/approval_service.py`
- `spec/schemas/approval-request.schema.json`
- `spec/schemas/approval-decision.schema.json`

### 6. Audit Service

Immutable append-only journal of every significant event.

| Responsibility | Description |
|---------------|-------------|
| Log executions | Every capability invocation |
| Log approvals | Every approval request and decision |
| Log state transitions | Every workflow step change |
| Log errors | Every failure and compensation |

**Key file:**
- `packages/runtime/src/aicp_runtime/services/audit_service.py`
- `spec/schemas/audit-entry.schema.json`

### 7. Session Service

Manages execution context that persists across process restarts.

| Responsibility | Description |
|---------------|-------------|
| Session lifecycle | Create, resume, close sessions |
| State persistence | Workflow state, approval state, execution history |
| Resumability | Survive process restarts |

**Key file:**
- `packages/runtime/src/aicp_runtime/services/session_service.py`

---

## Data Flow Example: Payment Transfer

```
1. Client submits: "Transfer ₹1000 to Rahul"
           │
           ▼
2. Discovery + Planner identifies: payment.transfer capability
           │
           ▼
3. Policy Engine evaluates:
   - Trust tier: 2 (Trusted)
   - Risk score: {financial: 0.7, irreversibility: 0.9}
   - Effect: require_approval (threshold exceeded)
           │
           ▼
4. Approval Service creates request, pauses execution
           │
           ▼
5. Human approves via CLI, API, or dashboard
           │
           ▼
6. Workflow Runtime resumes, steps to execution
           │
           ▼
7. Execution Engine invokes payment.transfer
           │
           ▼
8. Result Normalizer produces execution envelope:
   {
     "execution_id": "exec_...",
     "status": "success",
     "data": { "transaction_id": "txn_..." },
     "allowed_next_actions": [...],
     "rendered": "Transfer of ₹1000 to Rahul completed"
   }
           │
           ▼
9. Audit Service logs the complete flow
```

---

## Architectural Boundaries

### Core Protocol Boundary (`/packages/core`)

Defines capabilities, workflows, policies, statuses, and render semantics. Runtime-agnostic. Adapter-agnostic.

**Must NOT import from:**
- `/packages/runtime`
- Any adapter package

### Runtime Boundary (`/packages/runtime`)

Handles execution, planning, evaluation, normalization, persistence.

**Must NOT contain:**
- Core domain model logic (belongs in core)
- Adapter-specific logic (belongs in adapters)

### Adapter Boundary (`/adapters/`)

Maps AICP into or out of specific systems (FastAPI, Express, NestJS, LangChain, MCP, OpenAPI).

**Rules:**
- Adapters translate only — no business logic
- Adapter-specific logic must not leak into core models
- Each adapter has its own `pyproject.toml`, `tests/`, `README.md`

---

## Directory Structure

```
aicp/
├── spec/                          # Protocol source of truth (JSON schemas)
│   ├── schemas/                   # 9 schema definitions
│   ├── examples/                  # Valid/invalid examples
│   └── tests/                     # Schema validation tests
├── packages/
│   ├── core/                      # Protocol domain models (runtime-agnostic)
│   │   └── src/aicp/             # Capability, Workflow, Policy, etc.
│   ├── runtime/                   # Execution engine, services, persistence
│   │   └── src/aicp_runtime/     # Runtime services
│   └── cli/                       # 28 CLI commands
├── adapters/
│   ├── protocol/                  # HTTP, MCP, OpenAPI adapters
│   ├── framework/                 # FastAPI, Express, NestJS adapters
│   ├── agent/                     # LangChain, LangGraph, CrewAI adapters
│   └── importers/                 # cURL, HAR, Postman importers
├── sdks/
│   ├── typescript/                # TypeScript SDK (core built, runtime skeleton)
│   └── python/                    # Python SDK (skeleton)
├── mcp/                           # MCP server (exposes AICP outward)
├── apps/
│   └── studio/                    # Supervision console (minimal seed)
├── examples/                      # Reference applications
├── docs/                          # Human-readable documentation
│   ├── overview/                  # Vision, status, roadmap
│   ├── guides/                    # Architecture, usage, CLI
│   └── handbook/                  # Concept deep-dives
├── rfcs/                          # Protocol change proposals
└── governance/                    # Contributing guidelines
```

---

## Key Design Patterns

### Spec-First

The protocol is defined in `/spec` before runtime behavior drifts. If runtime behavior and spec disagree, spec wins.

### Reference Implementation

`/packages/core` and `/packages/runtime` are reference implementations, not the only way to build AICP.

### Thin Adapters

Adapters translate framework semantics to AICP concepts, not reinvent AICP internally.

### No Mega-Utils

No `utils.ts` or `helpers.py`. Domain logic lives in domain-named modules.

### Single Responsibility

Each module does one thing: capability validation, policy evaluation, workflow transitions.

### Branded Types

Use TypeScript branded types for IDs (`SessionId`, `ExecutionId`) to prevent mix-ups at compile time.

### Discriminated Unions

Use discriminated unions for status types, execution modes, and error categories.

### Custom Error Hierarchy

All errors extend `AicpError` with structured `code` and `status` fields.

---

## v0.1.1 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Capability Registry | Complete | 9 schemas, validation |
| Policy Engine | Complete | JSON rule-based |
| Workflow Runtime | Complete | Sequential + compensation |
| Execution Engine | Complete | Sync mode |
| Approval Service | Complete | CLI + API |
| Audit Service | Complete | Append-only journal |
| Session Service | Complete | Resume after restart |
| Semantic Discovery | Partial | Keyword scoring only |
| Session Encryption | Not started | Planned for v0.2.0 |
| Event-driven workflows | Not started | Planned for v0.3.0 |
| AI Planner/Judge | Not started | Planned for v0.3.0 |

---

## See Also

- [/ARCHITECTURE.md](../../ARCHITECTURE.md) — 11-plane system architecture overview
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model details
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and trust tier details
- [/spec/schemas/](../../spec/schemas/) — JSON schema source of truth
- [CLI_REFERENCE.md](./CLI_REFERENCE.md) — 28 CLI commands
