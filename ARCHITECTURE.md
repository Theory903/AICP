# AICP Architecture

> **Version Target:** 1.0.0 feature set | **Target:** 1.0.0
> **Last updated:** 2026-04-05

---

## 1. Mental Model

**Current practical model:**
```
operator or agent → Mammoth → AICP control plane → business systems
```

**v1.0.0 target:**
```
any intent, anywhere → Mammoth surfaces → AICP mesh → governed execution across apps, orgs, and protocols
```

AICP is the **control plane**. Mammoth is the **interaction shell**. For now, if a human or agent is operating the system, they do it through Mammoth. Studio is not a separate front door; it is supervision UX that should live inside Mammoth.

The mesh remains protocol-driven, but the product experience should be read through this boundary:

- **Mammoth decides how users and agents interact with the system**
- **AICP decides what can run, how it runs, what needs approval, and how it is recorded**

**Current layer model:**

| Layer | Role |
|-------|------|
| Mammoth | Operator and agent shell: prompt, invoke, supervise, review, approve |
| AICP control plane | Policy, capabilities, workflows, sessions, approvals, audit, discovery |
| Connected systems | Apps, tools, services, organizational backends |

This architecture is for **secure org automation**, not generic chat. Mammoth initiates and supervises work. AICP governs it.

---

## 2. Architecture Planes

### Plane 0 — Signal Plane

**Purpose:** Sub-millisecond event ingestion, deduplication, classification, and routing. The nervous system that converts raw events into actionable signals.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Ingestion | HTTP request/response | Sub-ms stream ingestion (HTTP/2, WebSocket, gRPC, SSE) |
| Deduplication | Idempotency key on capability | Content-hash dedup with sliding window, bloom filters |
| Classification | Capability kind matching | ML classifier: intent, urgency, risk, domain routing |
| Routing | Single runtime dispatch | Mesh-aware routing to nearest capable node |

**Core invariants:**
- Every signal MUST be classified before routing.
- Duplicate signals MUST be collapsed; only the first reaches execution.
- Signal latency from ingestion to classification MUST be <5ms at p99.

**Key components:** Event ingress, dedup engine, signal classifier, priority queue, route table.

---

### Plane 1 — Perception Plane

**Purpose:** Turn any application surface into structured, machine-readable state. The eyes and ears of the agent.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Sources | API response parsing | a11y tree, DOM, state APIs, screenshots, behavioral signals |
| Perception mode | Static (request/response) | Differential perception with change detection |
| Caching | None | Perception cache with TTL and invalidation |
| Cognitive signals | None | User intent signals, attention patterns, interaction velocity |

**Core invariants:**
- Perception output MUST be deterministic for the same application state.
- Perception cache MUST invalidate on any state mutation.
- Cognitive signals MUST NOT be used for policy decisions without explicit opt-in.

**Key components:** a11y tree parser, DOM state extractor, screenshot analyzer, behavioral signal collector, perception cache, differential perception engine, cognitive signal processor.

---

### Plane 2 — AI Plane

**Purpose:** Agent reasoning — intent routing, planning, execution, judgment, and memory. The brain.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Planning | None (agent selects capabilities directly) | Intent router + multi-step planner with constraint satisfaction |
| Execution | Direct capability invocation | Executor with speculative execution, rollback, parallel paths |
| Judgment | None | Judge evaluates success/failure/unsafe/ambiguous per result |
| Memory | Session state only | 5-layer memory system |
| Context | Full context passed per call | Context budget manager with token-aware truncation |
| Protocols | None | Cognitive protocol library (UX, SWE, Ops, Research, Finance) |

**Memory system (5 layers):**

| Layer | Scope | Persistence | Purpose |
|-------|-------|-------------|---------|
| Working | Current task | Request lifetime | Active variables, intermediate results |
| Episodic | Session | Session lifetime | Execution history, outcomes, approval decisions |
| Semantic | Global | Permanent | Domain knowledge, capability relationships, learned patterns |
| Skill | Per-agent | Permanent | Learned execution strategies, retry heuristics |
| Environmental | Per-deployment | Permanent | System topology, latency profiles, failure patterns |

**Cognitive protocol library:** Domain-specific reasoning templates that constrain and guide the planner:
- **UX Protocol:** Form completion, navigation, accessibility-aware interaction
- **SWE Protocol:** Code generation, PR review, deployment, incident response
- **Ops Protocol:** Monitoring, scaling, failover, runbook execution
- **Research Protocol:** Information gathering, synthesis, citation tracking
- **Finance Protocol:** Transaction validation, compliance checks, audit trail

**Core invariants:**
- The planner MUST only select from policy-allowed capabilities.
- The judge MUST evaluate every execution result before the agent proceeds.
- Memory layers MUST be queryable independently and in combination.
- Context budget MUST be enforced — exceeding budget truncates lowest-priority context.

**Key components:** Intent router, planner, executor, judge, memory system (5 layers), context budget manager, cognitive protocol library.

---

### Plane 3 — Capability Plane

**Purpose:** Registry, contracts, discovery, versioning, and composition of all agent-operable actions. The vocabulary of the agentic web.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Registry | In-memory, file, SQLite | Distributed registry with CRDT sync |
| Capabilities | Manual registration + OpenAPI/cURL/HAR/Postman import | 50,000+ capabilities via domain packs + federation |
| Versioning | `version` field on capability | Semantic versioning with backward compatibility checks |
| Composition | `dependency_capabilities` + `often_follows` | Full capability composition with cost optimization |
| Cost | None | Cost oracle: latency, financial cost, risk cost per invocation |
| Discovery | Keyword scoring + co-occurrence similarity | Semantic retrieval with embeddings + graph traversal |

**Capability kinds:** `query`, `action`, `workflow`, `async_action`, `batch_action`

**Determinism classes:** `deterministic`, `bounded_nondeterministic`, `observational`, `heuristic`

**Domain packs** (v1.0.0): Pre-built capability sets for verticals — e-commerce, fintech, healthcare, devops, CRM, ERP.

**Core invariants:**
- Every capability MUST have a name, kind, input schema, and output schema.
- Capability names MUST be globally unique within a registry.
- Deprecated capabilities MUST remain discoverable with `deprecated: true`.
- Capability composition MUST NOT create circular dependencies.

**Key components:** Capability registry, capability validator, cost oracle, domain packs, version manager, composition engine, discovery service.

---

### Plane 4 — Workflow Plane

**Purpose:** Stateful, resumable, multi-step process orchestration. The conductor.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Patterns | Sequential + compensation | Sequential, parallel, fork/join, loops, sagas, event-driven, subflows |
| Definition | Code-defined steps | YAML DSL + visual authoring + code |
| State | In-memory, file, SQLite | Distributed state with conflict resolution |
| Simulation | None | Simulation mode: test workflows against mock backends |
| Step types | capability, approval | capability, approval, wait_event, branch, parallel, loop, subflow, terminal, human_task, transform |

**Workflow statuses:** `created`, `running`, `waiting_approval`, `waiting_event`, `paused`, `failed`, `completed`, `cancelled`

**Step statuses:** `pending`, `running`, `completed`, `failed`, `skipped`, `awaiting_confirmation`, `retrying`, `blocked`

**Core invariants:**
- A workflow MUST always have persisted state before transition.
- A workflow step CANNOT be marked complete without an audit entry.
- A workflow run has at most one active current step unless inside a declared parallel block.
- A resumed workflow MUST preserve prior audit lineage.
- A workflow terminal state is immutable except via replay/fork semantics.

**Key components:** Workflow engine, step executor, state manager, YAML DSL parser, visual authoring API, simulation engine, compensation handler.

---

### Plane 5 — Governance Plane

**Purpose:** Policy evaluation, approval gates, trust management, compliance, and risk scoring. The immune system.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Policy format | JSON policy objects | Compiled policy (OPA/Cedar → WASM) for sub-ms evaluation |
| Effects | allow, deny, ask, limit | Same effects + conditional escalation chains |
| Trust model | None | Trust tiers 0–4 with decay over inactivity |
| Risk scoring | Side-effect classification (high/low) | Multi-dimensional: financial, irreversibility, privacy, blast radius |
| Anomaly detection | None | Behavioral anomaly detection with automatic policy tightening |
| Compliance | None | GDPR, SOC2, HIPAA, PCI compliance layers |
| Policy learning | None | Policy suggestion engine based on approval patterns |

**Trust tiers:**

| Tier | Name | Autonomy |
|------|------|----------|
| 0 | Untrusted | All actions require approval |
| 1 | Observed | Queries auto-approved, actions require approval |
| 2 | Trusted | Low-risk actions auto-approved, high-risk require approval |
| 3 | Autonomous | Most actions auto-approved, critical require approval |
| 4 | Sovereign | Full autonomy with audit trail (human-equivalent trust) |

**Policy effects:** `allow` (proceed), `deny` (block with reason), `ask` (halt for human approval), `limit` (proceed with rate/amount constraints).

**Core invariants:**
- A capability execution MUST always be policy-evaluated before side effects.
- An approval-gated action CANNOT execute before approval is resolved.
- Policy evaluation MUST complete in <5ms at p99 (WASM target: <1ms).
- Trust tier changes MUST be audited.
- Trust decay MUST be automatic — no activity for N days reduces tier by 1.

**Key components:** Policy engine, policy compiler (OPA/Cedar → WASM), trust tier manager, risk scorer, anomaly detector, approval engine, compliance layer, policy learning engine.

---

### Plane 6 — Execution Plane

**Purpose:** Deterministic capability invocation with result normalization, idempotency, persistence, and audit. The hands.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Mode | Synchronous only | Three execution classes (see below) |
| Idempotency | `idempotency_key` field on capability | Full idempotency engine with key management |
| Locking | None | Resource lock protocol for concurrent access |
| Envelope | Partial (status + next + data) | Full canonical execution envelope |

**Three execution classes:**

| Class | Latency | Pattern | Use case |
|-------|---------|---------|----------|
| Realtime | <5ms | Direct invocation, no saga | Queries, reads, low-risk actions |
| Transactional | Variable | Saga with compensation | Payments, orders, multi-step mutations |
| Event-driven | Indefinite | Wait/resume on external event | Delivery tracking, approval flows, webhooks |

**Execution modes:** `sync`, `async`, `approval_blocked`, `event_wait`, `streaming`

**Core invariants:**
- Every execution MUST produce the canonical execution envelope.
- Every execution MUST be attributable to agent, human, or system actor.
- Idempotent executions with the same key MUST return the cached result.
- Resource locks MUST have TTL — no indefinite locks.
- Execution errors MUST include structured `error_detail` with recovery hints.

**Key components:** Executor, result normalizer, idempotency engine, resource lock manager, saga coordinator, audit writer.

---

### Plane 7 — Multi-Agent Plane

**Purpose:** Hierarchical coordination across multiple agents. The organization chart.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Agents | Single agent per session | Four-tier hierarchy with 40 specialist types |
| Communication | None (single agent) | Inter-agent communication protocol with message routing |
| Coordination | None | Task delegation, result aggregation, conflict resolution |

**Four-tier hierarchy:**

| Tier | Role | Count (v1.0.0) | Responsibility |
|------|------|-----------------|----------------|
| Orchestrator | Strategic planning | 1 per workflow | Goal decomposition, specialist selection, progress tracking |
| Specialist | Domain execution | 40 types | Domain-specific task execution (e.g., commerce, finance, devops) |
| Worker | Atomic actions | N per specialist | Individual capability invocation |
| Supervisor | Quality & safety | 1 per orchestrator | Result validation, policy compliance, escalation |

**Core invariants:**
- An orchestrator MUST NOT execute capabilities directly — it delegates to specialists.
- A worker MUST NOT make planning decisions — it executes assigned capabilities.
- A supervisor MUST have read access to all agent communications in its scope.
- Inter-agent messages MUST be audited.

**Key components:** Agent registry, task delegator, message router, result aggregator, conflict resolver, supervisor.

---

### Plane 8 — Federation Plane

**Purpose:** Cross-organization capability discovery, registry synchronization, and trust establishment. The internet of agents.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Discovery | `/.well-known/aicp` endpoint | Push/pull discovery with scanner (800k+ services) |
| Registry sync | None | CRDT-based registry synchronization across nodes |
| Authentication | None | DID-based mutual authentication |
| Topology | Single node | Regional mirrors with eventual consistency |

**Discovery protocol:**
1. `GET /.well-known/aicp` → returns node capabilities, version, trust level
2. Push: node announces capabilities to known peers
3. Pull: node queries peers for capabilities matching criteria
4. Scanner: crawls known domains for `/.well-known/aicp` endpoints

**Core invariants:**
- Federated registries MUST converge (CRDT guarantee).
- Cross-org capability invocation MUST require mutual DID authentication.
- Scanner MUST respect `robots.txt` and rate limits.
- Regional mirrors MUST NOT serve stale data beyond configured TTL.

**Key components:** Discovery endpoint, push/pull sync engine, CRDT registry, DID authenticator, scanner, regional mirror manager.

---

### Plane 9 — Supervision Plane

**Purpose:** Human oversight — monitoring, intervention, replay, and debugging. The control room.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| UI | Agent console (840 lines HTML) | 5-view supervision dashboard |
| Monitoring | Execution history via `/history` | Real-time live feed with streaming |
| Approvals | CLI + API | Approval queue with risk visualization |
| Debugging | Timeline endpoint | Full replay debugger with step-by-step execution |
| Policy editing | JSON files | Visual policy editor with simulation |

**Five views:**

| View | Purpose | Data source |
|------|---------|-------------|
| Live Feed | Real-time execution stream | Execution events via SSE/WebSocket |
| Approval Queue | Pending approvals with risk context | Approval service |
| Replay Debugger | Step-by-step execution replay with state inspection | Audit trail + persisted state |
| Policy Editor | Create/edit/simulate policies | Policy engine |
| Health Dashboard | System health, latency, error rates, agent performance | Provider health + metrics |

**Core invariants:**
- The supervision UI MUST NOT be able to bypass policy evaluation.
- Replay MUST be read-only — replayed executions MUST NOT trigger side effects.
- The approval queue MUST show risk assessment for every pending approval.
- Health data MUST be real-time (< 5s lag).

**Key components:** Live feed, approval queue UI, replay debugger, policy editor, health dashboard.

---

### Plane 10 — Learning Plane

**Purpose:** Continuous improvement through pattern mining, policy learning, and autonomy calibration. The growth engine.

| Aspect | v0.1.1 | v1.0.0 |
|--------|--------|--------|
| Learning | None | Full learning pipeline |
| Skill mining | None | Extract reusable execution patterns from successful workflows |
| Policy learning | None | Suggest policy changes based on approval patterns |
| Gap detection | None | Identify missing capabilities from failed/abandoned workflows |
| Drift detection | None | Detect when agent behavior diverges from expected patterns |
| Autonomy calibration | None | Adjust trust tiers based on agent performance |

**Learning pipeline:**
1. **Skill mining:** Analyze successful workflow executions → extract reusable patterns → propose as new capabilities or workflow templates
2. **Policy learning:** Analyze approval decisions → identify patterns (always approved, always denied) → suggest policy updates
3. **Capability gap detection:** Analyze failed/abandoned workflows → identify missing capabilities → propose new capability contracts
4. **Drift detection:** Compare current agent behavior against baseline → flag anomalies → trigger supervisor review
5. **Autonomy calibration:** Aggregate agent performance metrics → adjust trust tiers → expand or contract autonomy

**Core invariants:**
- Learning outputs MUST be proposals — never auto-applied without human review.
- Drift detection MUST trigger alerts, not automatic remediation.
- Autonomy calibration MUST only increase trust after N consecutive successful executions.
- Skill mining MUST NOT expose sensitive data from execution history.

**Key components:** Skill miner, policy learner, capability gap detector, drift detector, autonomy calibrator.

---

## 3. The 20 Modules

These are the canonical modules of an AICP-compliant system. Each module maps to one or more planes. The sub-components listed in the plane sections above (Intent Router, Planner, Judge, etc.) are implementation components *within* these modules, not modules themselves.

| # | Module | Plane | Description |
|---|--------|-------|-------------|
| 1 | **Principal and Org Control** | Governance | Identity hierarchy, org boundaries, delegation chains, principal attribution |
| 2 | **Identity and Trust** | Governance | DID-based authentication, trust tiers 0-4, credential verification, session tokens |
| 3 | **Capability Registry** | Capability | Schema-validated capability store, versioning, deprecation, dependency tracking |
| 4 | **Tool Runtime** | Execution | Sandboxed capability invocation, timeout enforcement, result normalization |
| 5 | **Workflow Engine** | Workflow | Step execution, state persistence, branching, compensation, approval integration |
| 6 | **Perception and Signal Layer** | Perception / Signal | DOM observers, a11y tree extraction, screenshot pipeline, event ingestion |
| 7 | **Human Cognitive Protocols** | Supervision | Approval UX, review packets, impact summaries, decision lifecycle management |
| 8 | **AI Plane** | AI | Planner, judge, intent router, tool selection, context budget, cognitive loops |
| 9 | **Memory System** | AI | Working memory, episodic store, semantic index, procedural knowledge base |
| 10 | **Code Intelligence DB** | AI | AST indexing, symbol graph, call-chain analysis, code-aware context building |
| 11 | **Crawl / Map / Discovery Engine** | Capability | Web crawling, capability extraction, site mapping, capability graph construction |
| 12 | **Governance and Policy** | Governance | Policy DSL, compiled evaluation, effect resolution, audit integration |
| 13 | **Execution Engine** | Execution | Three-class dispatcher, saga coordinator, idempotency, failure recovery |
| 14 | **Multi-Agent Hierarchy** | Multi-Agent | Role assignment, task delegation, result aggregation, supervisor escalation |
| 15 | **Agent Communication Bus** | Multi-Agent | Typed message passing, pub/sub channels, coordination protocols |
| 16 | **Federation and Agentic WWW** | Federation | Discovery protocol, cross-org registry sync, trust federation, capability routing |
| 17 | **Human Web Compatibility** | Perception | Browser automation fallback, form filling, navigation, legacy app support |
| 18 | **Audit / Replay / Observability** | Supervision | Append-only audit journal, execution replay, correlation, distributed tracing |
| 19 | **Learning / Drift / Growth** | Learning | Skill extraction, policy refinement, performance drift detection, autonomy scaling |
| 20 | **Domain Packs and Benchmarks** | Learning | Pre-built capability sets per vertical, evaluation suites, regression testing |

---

## 4. Execution Contract

The canonical execution envelope. Every execution MUST produce this structure. UI, planner, judge, audit, and replay all consume it.

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

## 5. Execution Flow

```
                            ┌─────────────────────────────────────────────────┐
                            │              SIGNAL PLANE (P0)                  │
                            │  ingest → dedup → classify → route             │
                            └──────────────────────┬──────────────────────────┘
                                                   │
                            ┌──────────────────────▼──────────────────────────┐
                            │            PERCEPTION PLANE (P1)               │
                            │  DOM / a11y / state / screenshots → context    │
                            └──────────────────────┬──────────────────────────┘
                                                   │
                            ┌──────────────────────▼──────────────────────────┐
                            │               AI PLANE (P2)                    │
                            │                                                │
                            │   ┌──────────┐    ┌──────────┐                │
                            │   │  Intent   │───▶│ Planner  │                │
                            │   │  Router   │    │          │                │
                            │   └──────────┘    └────┬─────┘                │
                            │                        │ selects capabilities  │
                            │   ┌──────────┐    ┌────▼─────┐                │
                            │   │  Memory   │◀──│ Context  │                │
                            │   │  System   │──▶│ Budget   │                │
                            │   └──────────┘    └──────────┘                │
                            └──────────────────────┬──────────────────────────┘
                                                   │
                  ┌────────────────────────────────▼────────────────────────────────┐
                  │                     CAPABILITY PLANE (P3)                       │
                  │  resolve capability → validate input → check cost → bind args   │
                  └────────────────────────────────┬────────────────────────────────┘
                                                   │
                  ┌────────────────────────────────▼────────────────────────────────┐
                  │                     GOVERNANCE PLANE (P5)                       │
                  │                                                                 │
                  │   evaluate policy ──┬── ALLOW ──────────────────┐               │
                  │                     ├── DENY ── return error    │               │
                  │                     ├── ASK ── approval gate ───┤ (on approve)  │
                  │                     └── LIMIT ── enforce cap ───┘               │
                  └────────────────────────────────┬────────────────────────────────┘
                                                   │
                  ┌────────────────────────────────▼────────────────────────────────┐
                  │                     EXECUTION PLANE (P6)                        │
                  │                                                                 │
                  │   check idempotency → acquire lock → invoke → normalize result  │
                  │                                                                 │
                  │   ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
                  │   │  Realtime   │  │  Transactional   │  │  Event-Driven    │  │
                  │   │   <5ms      │  │   saga+comp      │  │  wait/resume     │  │
                  │   └─────────────┘  └──────────────────┘  └──────────────────┘  │
                  └────────────────────────────────┬────────────────────────────────┘
                                                   │
                            ┌──────────────────────▼──────────────────────────┐
                            │               AI PLANE (P2) — Judge            │
                            │                                                │
                            │   evaluate result ──┬── SUCCESS ── continue    │
                            │                     ├── FAILURE ── retry/comp  │
                            │                     ├── UNSAFE ── escalate     │
                            │                     └── AMBIGUOUS ── clarify   │
                            └──────────────────────┬──────────────────────────┘
                                                   │
                  ┌────────────────────────────────▼────────────────────────────────┐
                  │                     AUDIT (Cross-cutting)                       │
                  │  append entry → correlate → persist → expose allowed_next       │
                  └────────────────────────────────┬────────────────────────────────┘
                                                   │
                            ┌──────────────────────▼──────────────────────────┐
                            │            LEARNING PLANE (P10)                │
                            │  mine skills ← learn policies ← detect drift  │
                            └─────────────────────────────────────────────────┘
```

---

## 6. Capability Contract

```yaml
name: orders.place
description: Place the prepared order for the active cart
kind: action
version: "1.2.0"
determinism_class: bounded_nondeterministic

input_schema:
  type: object
  properties:
    cart_id: { type: string, description: "Active cart identifier" }
    payment_method_id: { type: string, description: "Selected payment method" }
    delivery_address_id: { type: string, description: "Delivery destination" }
    special_instructions: { type: string, description: "Optional delivery notes" }
  required: [cart_id, payment_method_id, delivery_address_id]

output_schema:
  type: object
  properties:
    order_id: { type: string }
    status: { type: string, enum: [confirmed, pending_payment, failed] }
    estimated_delivery: { type: string, format: date-time }
    total_amount: { type: number }

tags: [commerce, orders, transactional, high-risk]

policy:
  policy_name: financial_actions
  parameters:
    max_amount: 500.00
    require_confirmation: true

auth:
  mode: session
  requires_session: true
  csrf_required: true
  refreshable: true
  required_session_provider: stripe
  allowed_scopes: [orders:write, payments:charge]

idempotency_key: cart_id
output_validation_mode: strict

render:
  format: confirmation
  fields: [order_id, status, estimated_delivery, total_amount]

continuation:
  can_continue: true
  next_capabilities: [order.track, order.cancel, order.modify]
  next_hint: Track order status or cancel within 5 minutes
  poll_capability: order.status
  poll_after_ms: 30000
  poll_argument: order_id

provider:
  name: internal-commerce
  type: rest
  url: https://api.example.com/v2

dependency_capabilities: [cart.checkout, payment.validate]
often_follows: [cart.add_item, cart.checkout]
rollback_capability: order.cancel

error_codes:
  - PAYMENT_DECLINED
  - CART_EXPIRED
  - DELIVERY_UNAVAILABLE
  - INSUFFICIENT_STOCK
  - ADDRESS_UNSERVICEABLE

deprecated: false
```

---

## 7. Workflow Model

```yaml
name: food_order_flow
description: End-to-end food ordering with delivery tracking
version: "1.0.0"

steps:
  - id: search_restaurants
    type: capability
    capability_name: restaurants.search
    input_mapping:
      cuisine: "$.context.user_preference"
      location: "$.context.delivery_address"
    output_mapping:
      restaurants: "$.result.restaurants"
    on_success: select_restaurant
    on_failure: search_failed
    retry_policy:
      max_attempts: 3
      backoff: exponential
      delay_ms: 1000

  - id: select_restaurant
    type: capability
    capability_name: restaurant.select
    input_mapping:
      restaurants: "$.context.restaurants"
    output_mapping:
      restaurant_id: "$.result.restaurant_id"
    on_success: browse_menu

  - id: browse_menu
    type: capability
    capability_name: menu.get
    input_mapping:
      restaurant_id: "$.context.restaurant_id"
    output_mapping:
      menu: "$.result.menu"
    on_success: build_cart

  - id: build_cart
    type: loop
    capability_name: cart.add_item
    loop_condition:
      exit_condition: "$.context.cart_ready == true"
      max_iterations: 20
    on_success: checkout

  - id: checkout
    type: capability
    capability_name: cart.checkout
    on_success: validate_payment

  - id: validate_payment
    type: parallel
    parallel_steps:
      - id: validate_card
        type: capability
        capability_name: payment.validate
      - id: check_fraud
        type: capability
        capability_name: fraud.check
    on_success: request_approval
    on_failure: payment_failed

  - id: request_approval
    type: approval
    approval_policy:
      required: true
      threshold: 50.00
      role: customer
    on_approved: place_order
    on_rejected: revise_cart
    timeout_ms: 300000
    on_timeout: order_expired

  - id: place_order
    type: capability
    capability_name: orders.place
    compensation:
      capability_name: order.cancel
      arguments:
        reason: "workflow_compensation"
    on_success: track_delivery

  - id: track_delivery
    type: wait_event
    wait_for_event: order_delivered
    timeout_ms: 7200000
    on_timeout: delivery_escalation
    on_success: complete

  - id: complete
    type: terminal

  - id: search_failed
    type: terminal

  - id: payment_failed
    type: branch
    branch_conditions:
      - condition: "$.error_code == 'PAYMENT_DECLINED'"
        then_step_id: retry_payment
      - condition: "$.error_code == 'FRAUD_DETECTED'"
        then_step_id: order_blocked

  - id: revise_cart
    type: capability
    capability_name: cart.edit
    on_success: checkout

  - id: order_expired
    type: terminal

  - id: delivery_escalation
    type: capability
    capability_name: support.escalate
    on_success: complete
```

---

## 8. Protocol Invariants

These are immovable architectural rails. Violating any of these breaks the protocol.

### Spec Invariants

1. `/spec` is authoritative for protocol structure.
2. Protocol changes MUST be documented in `/spec` before runtime implementation.
3. All implementations MUST validate protocol objects against JSON schemas.
4. Schema changes MUST maintain backward compatibility unless major version bump.

### Runtime Invariants

5. A capability execution MUST always be policy-evaluated before side effects.
6. A workflow run MUST always have persisted state before transition.
7. A workflow step CANNOT be marked complete without an audit entry.
8. An approval-gated action CANNOT execute before approval is resolved.
9. Every execution response MUST expose `allowed_next_actions`.
10. Session context MUST be resumable across process restarts.
11. A workflow run has at most one active current step unless inside a declared parallel block.
12. A resumed workflow MUST preserve prior audit lineage.
13. A workflow terminal state is immutable except via replay/fork semantics.
14. Every execution event MUST be attributable to agent, human, or system actor.

### Package Boundary Invariants

15. `/packages/core` MUST remain runtime-agnostic and adapter-agnostic.
16. `/packages/core` MUST NOT import from `/packages/runtime` or adapters.
17. Adapters MUST translate only; they MUST NOT contain core orchestration logic.
18. Adapter-specific logic MUST NOT leak into core models.

### Execution Invariants

19. Every execution MUST produce the canonical execution envelope.
20. Idempotent executions with the same key MUST return the cached result.
21. Resource locks MUST have TTL — no indefinite locks.
22. Execution errors MUST include structured `error_detail` with recovery hints.

### Federation Invariants

23. Federated registries MUST converge (CRDT guarantee).
24. Cross-org capability invocation MUST require mutual authentication.
25. Discovery endpoints MUST be available at `/.well-known/aicp`.

### Learning Invariants

26. Learning outputs MUST be proposals — never auto-applied without human review.
27. Autonomy calibration MUST only increase trust after N consecutive successful executions.

---

## 9. Compliance Levels

Implementations declare their conformance level:

| Level | Name | Requirements |
|-------|------|-------------|
| **0** | **Capability Discovery** | Capability registry, input/output schema validation, basic execution |
| **1** | **Governed Execution** | Level 0 + policy evaluation, approval checkpoints, audit trail, session management |
| **2** | **Resumable Workflows** | Level 1 + sequential workflows, compensation, state persistence, resume after approval |
| **3** | **Event-Driven Orchestration** | Level 2 + wait-for-event, timeout branching, parallel steps, loops |
| **4** | **AI Planning Support** | Level 3 + planner, judge, context builder, allowed-next-actions schema |
| **5** | **Full Orchestration** | Level 4 + multi-agent coordination, subflows, cross-flow events, federation, supervision console |

**Current reference implementation: Level 5** — full orchestration with multi-agent coordination, subflows, cross-flow events, federation, supervision, 16 schemas, 740 Python tests + 77 Rust tests passing.

---

## 10. Transport Layer

| Protocol | Use case | Status (v0.1.1) | Target (v1.0.0) |
|----------|----------|------------------|------------------|
| **HTTP/2** | Standard request/response, capability execution, discovery | Active | Primary transport |
| **WebSocket** | Live feed, real-time execution monitoring, streaming results | Not implemented | Supervision UI, streaming execution |
| **gRPC** | High-throughput inter-service, inter-agent communication | Not implemented | Multi-agent plane, federation sync |
| **SSE** | Server-sent events for live updates | Not implemented | Execution progress, approval notifications |

**Wire format:** JSON (HTTP/2, WebSocket, SSE), Protobuf (gRPC)

**Discovery:** `GET /.well-known/aicp` returns:
```json
{
  "aicp_version": "0.1.1",
  "compliance_level": 2,
  "capabilities_url": "/discover",
  "execution_url": "/v1/execute",
  "approvals_url": "/v1/approvals",
  "transports": ["http2"],
  "auth_methods": ["session", "bearer"],
  "trust_tier": 0
}
```

---

## 11. Directory Structure

```
aicp/
├── spec/                              # PLANE: Cross-cutting (source of truth)
│   ├── schemas/                       #   9 JSON Schema definitions
│   │   ├── capability.schema.json
│   │   ├── workflow.schema.json
│   │   ├── policy.schema.json
│   │   ├── execution-result.schema.json
│   │   ├── approval-request.schema.json
│   │   ├── approval-decision.schema.json
│   │   ├── audit-entry.schema.json
│   │   ├── discovery.schema.json
│   │   └── error.schema.json
│   ├── examples/                      #   Valid/invalid schema examples
│   └── tests/                         #   Schema validation tests
│
├── packages/                          # PLANE: 3 (Capability), 4 (Workflow), 5 (Governance), 6 (Execution)
│   ├── core/                          #   Domain models, validation, capability contracts
│   │   └── src/aicp/
│   │       ├── capability/            #     Capability model + validator
│   │       ├── workflow/              #     Workflow model + state machine
│   │       ├── policy/               #     Policy model + evaluator
│   │       ├── execution/            #     Execution model + result normalization
│   │       ├── errors/               #     Error hierarchy
│   │       ├── rendering/            #     Output rendering
│   │       └── pagination/           #     Pagination utilities
│   ├── runtime/                       #   Execution engine, services, persistence
│   │   └── src/aicp_runtime/
│   │       ├── services/             #     8 runtime services
│   │       ├── persistence/          #     Memory, file, SQLite backends
│   │       ├── server/               #     FastAPI server + routes
│   │       └── middleware/           #     Request processing
│   └── cli/                           #   Command-line interface
│       └── src/aicp_cli/
│           └── commands/             #     28 CLI commands
│
├── sdks/                              # PLANE: Client-facing
│   ├── typescript/                    #   TypeScript SDK (core built)
│   │   └── packages/
│   │       ├── core/                 #     Types, validation
│   │       ├── runtime/              #     Execution client (skeleton)
│   │       └── client/               #     HTTP client (skeleton)
│   └── python/                        #   Python SDK (skeleton)
│
├── adapters/                          # PLANE: Cross-cutting (translation layer)
│   ├── protocol/                      #   Protocol adapters
│   │   ├── http/                     #     HTTP adapter (empty)
│   │   ├── mcp/                      #     MCP adapter (complete)
│   │   ├── openapi/                  #     OpenAPI adapter (complete)
│   │   ├── graphql/                  #     GraphQL adapter (empty)
│   │   └── websocket/               #     WebSocket adapter (empty)
│   ├── framework/                     #   Framework adapters
│   │   ├── fastapi/                  #     FastAPI adapter (complete)
│   │   ├── express/                  #     Express adapter (empty)
│   │   ├── nestjs/                   #     NestJS adapter (empty)
│   │   ├── nextjs/                   #     Next.js adapter (empty)
│   │   └── spring-boot/             #     Spring Boot adapter (empty)
│   ├── importers/                     #   Import adapters
│   │   ├── curl/                     #     cURL importer (complete)
│   │   ├── har/                      #     HAR importer (complete)
│   │   └── postman/                  #     Postman importer (complete)
│   └── agent/                         #   Agent framework adapters
│       ├── langchain/                #     LangChain adapter (empty)
│       ├── langgraph/                #     LangGraph adapter (empty)
│       └── crewai/                   #     CrewAI adapter (empty)
│
├── mcp/                               # PLANE: 8 (Federation) — MCP bridge
├── apps/                              # PLANE: 9 (Supervision) — Studio UI
├── examples/                          # Reference applications
├── docs/                              # Human-readable documentation
├── rfcs/                              # Protocol change proposals
├── governance/                        # Contribution guidelines
└── tools/                             # Internal development tooling
```

---

## 12. Version Alignment

| Component | Current | Target | Compliance Level |
|-----------|---------|--------|------------------|
| Spec (JSON Schemas) | 0.1.1-alpha | 1.0.0 | -- |
| Python Core (`packages/core`) | 0.1.1-alpha | 1.0.0 | L2 |
| Python Runtime (`packages/runtime`) | 0.1.1-alpha | 1.0.0 | L2 |
| Python CLI (`packages/cli`) | 0.1.1-alpha | 1.0.0 | -- |
| TypeScript Core SDK | 0.1.1-alpha | 1.0.0 | L0 |
| TypeScript Runtime SDK | skeleton | 1.0.0 | -- |
| TypeScript Client SDK | skeleton | 1.0.0 | -- |
| Python SDK | skeleton | 1.0.0 | -- |
| FastAPI Adapter | 0.1.1-alpha | 1.0.0 | -- |
| MCP Adapter | 0.1.1-alpha | 1.0.0 | -- |
| MCP Server | 0.1.1-alpha | 1.0.0 | -- |

**TypeScript SDK compliance gap:** The TypeScript Core SDK is at L0 (Capability Discovery) while the Python runtime is at L2 (Resumable Workflows). Any Phase 3 adapter (LangChain, LangGraph) built in TypeScript will operate against an L0 SDK. Either the TypeScript SDK must be brought to L2 before Phase 3, or Phase 3 adapters must be Python-first with TypeScript work in parallel. This decision must be made before v0.4.0 planning begins.

**What ships at each milestone:**

| Phase | Version | Focus | What's new |
|-------|---------|-------|------------|
| 0 | **0.1.1-alpha** | Foundation | 9 schemas, 8 services, 30+ endpoints, 3 backends, 28 CLI commands, 6 adapters, 172 tests |
| 1 | **0.2.0** | AI Core | Planner, judge, memory/context builder, intent router, cognitive protocols |
| 2 | **0.3.0** | Orchestration | YAML workflow DSL, event-driven flows, parallel steps, loops, subflows |
| 3 | **0.4.0** | Agent Integration | LangChain, LangGraph, CrewAI adapters, food ordering reference flow |
| 4 | **0.5.0** | Perception | a11y tree, DOM observation, screenshot pipeline, signal bus |
| 5 | **0.6.0** | Multi-Agent | 4-tier hierarchy, communication bus, task delegation, supervisor roles |
| 6 | **0.7.0** | Federation | Cross-org discovery, CRDT registries, DID auth, trust federation |
| 7 | **0.8.0** | Learning | Skill mining, policy learning, drift detection, domain packs, benchmarks |
| 8 | **0.9.0** | Production | Encrypted sessions, compiled WASM policies, risk scoring, multi-tenant |
| 9 | **1.0.0** | Agentic Web OS | Complete 11-plane architecture, stable protocol, production-ready |

All components stay version-aligned. Spec is always authoritative. If docs and spec disagree, spec wins.

---

## 13. Mammoth Interaction Layer

Mammoth is the primary interaction shell for AICP. It sits above all 11 control-plane planes, consuming their capabilities through the AICP runtime and exposing them to operators and agents via four channels.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAMMOTH INTERACTION LAYER                   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Terminal    │  │ Web / Studio│  │   CLI    │  │ Chrome  │  │
│  │ TUI         │  │ (axum/HTML) │  │ (batch)  │  │ Ext MV3 │  │
│  │ (ratatui)   │  │             │  │          │  │ (SSE)   │  │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └────┬────┘  │
│         └────────────────┴──────────────┴──────────────┘       │
│                              channel.rs                         │
│                         (Channel trait)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
             ┌─────────────────▼──────────────────┐
             │        AICP RUNTIME (Rust)          │
             │  session · policy · tools · memory  │
             └──────────────────┬─────────────────┘
                                │
        ┌───────────────────────▼──────────────────────────┐
        │              AICP CONTROL PLANE                  │
        │  Planes 0–10: Signal · Perception · AI ·         │
        │  Capability · Workflow · Governance ·            │
        │  Execution · Multi-Agent · Federation ·          │
        │  Supervision · Learning                          │
        └──────────────────────────────────────────────────┘
```

### 13.1 Channel Architecture

All user-facing surfaces are instances of the `Channel` trait in `runtime/src/channel.rs`. Channels translate between human/agent intent and the AICP runtime. They MUST NOT contain orchestration logic.

| `ChannelKind` | Surface | Entry Point | Notes |
|---|---|---|---|
| `Terminal` | ratatui TUI | `mammoth` (interactive) | Full TUI: transcript, inspector, composer, slash palette |
| `Web` | Axum web server | `mammoth serve` | Studio HTML at `/`, session API at `/sessions/*`, SSE streams |
| `Cli` | Non-interactive batch | `mammoth <subcmd>` | `mammoth serve`, `mammoth ext`, scripted automation |
| `Extension` | Chrome MV3 extension | `mammoth ext` + `/ext/events` | SSE bridge at `/ext/events`, inbound at `/ext/message` |

**Channel trait contract:**

```rust
pub trait Channel: Send + Sync {
    fn name(&self) -> &str;
    fn kind(&self) -> ChannelKind;
    fn render_message(&self, msg: &ConversationMessage) -> String;
    fn request_approval(&self, req: &ApprovalRequest) -> ApprovalDecision;
    fn on_tool_progress(&self, event: &ToolProgressEvent);
    fn shutdown(&self);
}
```

Approval requests carry `channel: ChannelKind` so they route to the correct surface. The Terminal channel renders approval prompts inline; the Extension channel emits `ExtEvent::ApprovalRequest` over SSE for the browser to display.

### 13.2 Terminal TUI Layout

The ratatui TUI (`mammoth-cli/src/tui.rs`) renders a four-region layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER  Mammoth TUI · <branch>          <model> · <tokens>  │ 3 rows
├────────────────────────────────┬────────────────────────────┤
│                                │  INSPECTOR                 │
│  TRANSCRIPT                    │  [Status] [Diff] [Tools]   │
│  (scrollable conversation)     │                            │ fill
│                                │  (tab-switched panels)     │
│                                │                            │
├────────────────────────────────┴────────────────────────────┤
│ INPUT / COMPOSER                                            │ 6 rows
│ (multi-line, cursor-aware, Ctrl-J for newline)              │
├─────────────────────────────────────────────────────────────┤
│ FOOTER  Ctrl-P palette · Tab inspector · Enter send …       │ 1 row
└─────────────────────────────────────────────────────────────┘
```

**Inspector tabs:**

| Tab | Content |
|-----|---------|
| `Status` | Session status: model, permissions, LSP diagnostics, context size |
| `Diff` | Live `git diff` of the working tree, updated after each tool turn |
| `Tools` | Tool call log for the current session turn |

**Slash command palette** (`Ctrl-P`): fuzzy-filtered list of all registered slash commands. Commands are discovered from `commands::slash_command_specs()` at runtime. Selected command text is inserted into the composer.

**Key bindings:**

| Key | Action |
|-----|--------|
| `Enter` | Submit composer to AI |
| `Ctrl-J` | Insert newline in composer |
| `Ctrl-P` | Open slash command palette |
| `Tab` | Cycle inspector tab |
| `Ctrl-C` | Quit (session is persisted before exit) |
| `↑ / ↓` | Scroll transcript / navigate palette |

### 13.3 Web Channel and Studio

The `server` crate exposes an Axum HTTP server used by both the Web channel and the Chrome extension bridge.

**Routes:**

| Path | Handler | Purpose |
|------|---------|---------|
| `GET /` | Static HTML | Studio supervision UI |
| `POST /sessions` | `create_session` | Create a new Web channel session |
| `GET /sessions/:id/events` | SSE stream | Per-session `SessionEvent` stream to browser |
| `POST /sessions/:id/message` | `send_message` | Submit a user turn to a session |
| `GET /ext/events` | SSE broadcast | Extension event bus (`ExtEvent`) |
| `POST /ext/message` | `receive_ext_message` | Inbound message from Chrome extension |

**Extension events** over SSE:

```rust
pub enum ExtEvent {
    Message    { content: String },
    ApprovalRequest {
        approval_id:    String,
        capability_name: String,
        description:    String,
    },
}
```

**`TurnRunner` trait** (object-safe, `Send + Sync`): injected AI inference backend. Separates the HTTP server from the specific model router, enabling test doubles and future multi-model routing.

```rust
pub trait TurnRunner: Send + Sync {
    fn run_turn(
        &self,
        session_id: &str,
        messages: &[ConversationMessage],
        tx: Sender<SessionEvent>,
    ) -> BoxFuture<'_, Result<(), AicpError>>;
}
```

### 13.4 Crate Organization

The Mammoth workspace (`apps/mammoth/`) is a Rust workspace. Crates map to concerns:

| Crate | Role | AICP Planes consumed |
|-------|------|---------------------|
| `mammoth-cli` | Terminal TUI + CLI entry point; `run_repl()` / `run_prompt()` | All (via runtime) |
| `runtime` | Session management, permissions, config, hooks, MCP client, model router | Planes 2, 3, 5, 6, 7 |
| `tools` | 19 built-in tools + MCP tool wrappers | Plane 3 (Capability), Plane 6 (Execution) |
| `server` | Axum web server (Web channel + Extension SSE bridge) | Plane 9 (Supervision) |
| `lsp` | LSP client manager: diagnostics, go-to-def, references, context enrichment | Plane 1 (Perception) |
| `aicp` | AICP governance/policy bridge | Planes 4, 5 (Capability, Governance) |
| `api` | API client for AICP HTTP endpoints | Planes 3, 4, 5, 6 |
| `commands` | CLI sub-command implementations + slash command registry | — |
| `plugins` | Plugin loader and lifecycle | Plane 10 (Learning) |
| `compat-harness` | Compatibility test harness | — |

**Dependency order** (no cycles permitted):

```
aicp  ──►  runtime  ──►  tools  ──►  mammoth-cli
                    ──►  server
                    ──►  lsp
                    ──►  commands
                    ──►  plugins
api   ──►  runtime
```

`packages/core` (Python) MUST NOT be imported by any Rust crate. The boundary is the AICP HTTP API.

### 13.5 LSP Integration

The `lsp` crate maps to **Plane 1 (Perception)**. It manages connections to language server processes and enriches AI context with real IDE-quality signals.

| Method | Purpose |
|--------|---------|
| `collect_workspace_diagnostics()` | Harvest errors/warnings from all active LSPs |
| `go_to_definition(file, position)` | Resolve symbol definition location |
| `find_references(file, position)` | Find all references to a symbol |
| `context_enrichment()` → `LspContextEnrichment` | Package LSP signals into a prompt section |

`LspContextEnrichment::render_prompt_section()` serialises diagnostics, definitions, and references into a structured block that is prepended to AI turns. This is the primary mechanism by which Mammoth provides code-aware context to the planner (Plane 2).

### 13.6 Remote Session Topology

Mammoth supports three deployment topologies:

```
LOCAL (default)
  operator ──► mammoth (local) ──► AICP runtime (local) ──► tools

REMOTE SESSION  (MAMMOTH_CODE_REMOTE=1)
  operator ──► mammoth (local) ──► Anthropic API (remote session)
               └── MAMMOTH_CODE_REMOTE_SESSION_ID sets session ID
               └── ANTHROPIC_BASE_URL overrides API base

UPSTREAM PROXY  (CCR_UPSTREAM_PROXY_ENABLED=true + remote + token file)
  operator ──► mammoth ──► upstream proxy WebSocket
               ├── base_url/v1/code/upstreamproxy/ws  (https → wss)
               └── injects 8 proxy env vars into all subprocesses
```

**Remote session env vars:**

| Variable | Effect |
|----------|--------|
| `MAMMOTH_CODE_REMOTE` | `1 / true / yes / on` → activate remote session mode |
| `MAMMOTH_CODE_REMOTE_SESSION_ID` | Session ID to resume on the remote endpoint |
| `ANTHROPIC_BASE_URL` | Override API base URL for remote model endpoint |

**Upstream proxy env vars** (all require `CCR_UPSTREAM_PROXY_ENABLED=true` AND remote AND token file):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CCR_UPSTREAM_PROXY_ENABLED` | `false` | Master toggle |
| `CCR_SESSION_TOKEN_PATH` | `/run/ccr/session_token` | Path to bearer token file |
| `HTTPS_PROXY` | (from proxy WS) | Injected into subprocess env |
| `SSL_CERT_FILE` | `~/.ccr/ca-bundle.crt` | CA bundle for TLS verification |
| `NO_PROXY` | (from proxy) | Bypass list |
| `NODE_EXTRA_CA_CERTS` | (same as SSL_CERT_FILE) | Node.js CA path |
| `REQUESTS_CA_BUNDLE` | (same) | Python requests CA path |
| `CURL_CA_BUNDLE` | (same) | curl CA path |

The upstream proxy WebSocket URL is derived from `ANTHROPIC_BASE_URL` by replacing `https://` with `wss://` and appending `/v1/code/upstreamproxy/ws`.

### 13.7 Data Flow: User Turn End-to-End

```
User input (any channel)
       │
       ▼
channel.rs  ─────────────────────────────────────────────────
       │  render_message() / request_approval()
       │  Translates surface input to ConversationMessage
       ▼
runtime::ConversationClient
       │  Appends to conversation_history
       │  Enriches with LSP context (lsp::context_enrichment)
       │  Submits to model router (TurnRunner)
       ▼
AI Model (Anthropic / remote / proxy)
       │  Streams: TextDelta · ToolCallStart · ToolCallResult · Usage
       ▼
runtime::StreamEvent handler
       │  ToolCallStart  ──► tools crate (capability lookup + execution)
       │                      │
       │                      ▼
       │                 aicp::policy_eval()   (Plane 5 Governance)
       │                      │
       │                      ▼
       │                 approval_gate         (Plane 7 Cognitive Protocols)
       │                      │
       │                      ▼
       │                 tool execution        (Plane 6 Execution)
       │                      │
       │                      ▼
       │                 audit_entry           (Plane 18 Audit)
       │
       │  TextDelta     ──► channel.render_message()
       │  ToolCallResult──► channel.on_tool_progress()
       │                    inspector diff/tool cache refresh (TUI)
       ▼
Session persisted  (runtime::persist_session)
       │
       ▼
allowed_next_actions surfaced to channel (Execution Envelope)
```

### 13.8 Architectural Notes and Known Inconsistencies

**Version table (Section 12) is stale.** All entries show `0.1.1-alpha`. STATUS.md confirms L4 is complete and the reference implementation is currently at v0.3.0 with 692+ tests. Section 12 should be updated when Section 12 is next revised.

**Compliance level mismatch.** Section 11 states "Current reference implementation: Level 2." STATUS.md confirms L3 (Event-Driven Orchestration) and L4 (AI Planning Support) are both complete as of v0.3.0. Section 11 should read "Level 4."

**Studio is not a separate application.** The mental model in Section 1 is correct — Studio is supervision UX embedded in the `server` crate's static HTML. It is not a standalone primary app. Any references to Studio as a separate deployment target are outdated.

**Mammoth version alignment.** The Mammoth Rust workspace is not represented in the Section 12 version table. Mammoth should be added as a row when that table is next revised.
