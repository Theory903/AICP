# AICP Architecture

## Product Definition

> AICP is an AI-first application control plane that lets agents operate real apps through structured capabilities, stateful workflows, policy-gated execution, and human supervision.

## Architecture Planes

```
+-------------------------------------------------------------------+
|                           AI Plane                                 |
|  Planner  |  Executor  |  Judge  |  Memory Builder  |  Tool Select |
+-------------------------------------------------------------------+
|                        Control Plane                               |
|  Capability Registry | Workflow Registry | Policy Engine            |
|  Approval Service    | Execution Orchestrator | Session Manager     |
+-------------------------------------------------------------------+
|                           UX Plane                                 |
|  Operator Dashboard | Approval UI | Replay Debugger | Flow Builder  |
+-------------------------------------------------------------------+
|                          Data Plane                                |
|  REST APIs | Databases | External Services | Webhooks | Events      |
+-------------------------------------------------------------------+
```

### Control Plane
Registry, policy, orchestration. The brain that knows what actions exist, what's allowed, and how to sequence them.

### Data Plane
Actual backend services. The muscles that perform real work — databases, APIs, external integrations.

### AI Plane
Agent reasoning layer. Planner selects next valid action, executor calls capabilities, judge evaluates results, memory builds context.

### UX Plane
Human supervision console. Not for doing tasks — for supervising the AI doing tasks.

## Design Principles

### 1. Spec-First
- `/spec` contains JSON schemas that are the source of truth
- All implementations must validate against these schemas
- Examples in `/spec/examples/` test schema compliance

### 2. Reference Implementation
- `/packages/core` and `/packages/runtime` are reference implementations
- Clean, well-documented, not the "only way"
- Adapters translate between frameworks/protocols and AICP

### 3. Adapter Architecture
- Adapters in `/adapters/` translate between systems and AICP
- Protocol adapters: HTTP, MCP, OpenAPI, GraphQL, WebSocket
- Framework adapters: FastAPI, Express, NestJS, NextJS, Spring Boot
- Agent adapters: LangChain, LangGraph, CrewAI

### 4. SDK Layering
- `/sdks/typescript` and `/sdks/python` provide language-specific SDKs
- Built on top of core packages with ergonomic APIs

### 5. MCP Integration
- `/mcp/` contains MCP server implementations
- Bridges MCP clients to AICP capabilities

## Directory Purposes

| Directory | Purpose |
|-----------|---------|
| `/spec` | Protocol schemas, examples, validation tests |
| `/docs` | Human-readable documentation |
| `/packages` | Reference implementations |
| `/sdks` | Language-specific SDKs |
| `/adapters` | Framework and protocol adapters |
| `/mcp` | MCP server implementations |
| `/examples` | Working reference applications |
| `/rfcs` | Protocol change proposals |
| `/governance` | Contribution guidelines, maintainers |
| `/tools` | Internal development tooling |

## Key Protocol Concepts

### Capability
A governed action with strict input/output schema, side-effect classification, approval metadata, retry policy, and error codes. Not raw API endpoints — AI-safe action surfaces.

### Workflow
A stateful, resumable, multi-step process with branching, retries, approval checkpoints, and compensation.

### Policy
Rules defining what is allowed, denied, or requires approval — evaluated per capability call.

### Execution
The actual invocation of a capability with result normalization, persistence, and audit.

### Session
Resumable execution context with state, memory, and approval history.

### ApprovalRequest
A governance checkpoint with risk assessment, impact summary, and decision lifecycle.

### AuditEntry
An immutable record of every execution, policy evaluation, and approval event.

## Capability Contract

```yaml
name: order.place
description: Place the prepared order for the active cart
kind: action
input_schema:
  type: object
  properties:
    cart_id: { type: string }
    payment_method_id: { type: string }
    delivery_address_id: { type: string }
  required: [cart_id, payment_method_id, delivery_address_id]
side_effect: high
approval_required: true
idempotency_key: cart_id
retry_policy:
  max_attempts: 3
  backoff: exponential
error_codes:
  - PAYMENT_DECLINED
  - CART_EXPIRED
  - DELIVERY_UNAVAILABLE
continuation:
  can_continue: true
  next_capabilities: [order.track, order.cancel]
  next_hint: Track order status or cancel if needed
```

## Workflow Model

```yaml
name: food_order_flow
steps:
  - id: search_restaurants
    capability: restaurants.search
    on_success: select_restaurant

  - id: select_restaurant
    capability: restaurant.select
    on_success: browse_menu

  - id: browse_menu
    capability: menu.get
    on_success: build_cart

  - id: build_cart
    capability: cart.add_item
    loop: true
    exit_condition: cart_ready == true
    on_success: checkout

  - id: checkout
    capability: checkout.create
    on_success: request_payment_approval

  - id: request_payment_approval
    type: approval
    on_approved: place_order
    on_rejected: revise_cart

  - id: place_order
    capability: order.place
    on_success: track_order

  - id: track_order
    capability: delivery.track
    wait_for_event: order_delivered
    on_success: complete
```

## Execution Flow

```
AI Agent
   |
   v
+-------------+
|  Planner     | <- Current state + allowed actions
+------+------+
       | Selects next valid action
       v
+-------------+
| Policy Engine| <- Evaluates allow/deny/ask
+------+------+
       |
   +---+---+
   |       |
   v       v
 ALLOW    ASK -> ApprovalRequest -> Human decides
   |              |
   v              v (approved)
+-------------+
|  Executor    | <- Calls capability
+------+------+
       |
       v
+-------------+
|   Judge      | <- Evaluates result
+------+------+
       |
   +---+---+
   |       |
   v       v
SUCCESS  RETRY/ESCALATE
```

## API Surface

### AI Action Endpoints (`/v1/`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/execute` | POST | Execute a capability |
| `/v1/capabilities/rank` | GET | Ranked capability discovery |
| `/v1/sessions` | GET/POST | Session lifecycle |
| `/v1/sessions/{id}` | GET/DELETE | Session management |
| `/v1/sessions/{id}/refresh` | POST | Refresh session |
| `/v1/interactions` | GET/POST | Interaction state |
| `/v1/interactions/{id}` | GET/PATCH/DELETE | Interaction management |
| `/v1/workflows` | POST | Create workflow |
| `/v1/workflows/{id}/execute` | POST | Execute workflow |
| `/v1/approvals` | GET/POST | Approval operations |
| `/v1/approvals/{id}` | GET | Get approval |
| `/v1/executions` | GET | Execution history |

### Operational Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/discover` | GET | Capability discovery |
| `/.well-known/aicp` | GET | Well-known discovery |
| `/execute/{name}` | POST | Direct execution |
| `/approvals` | GET | List approvals |
| `/approvals/{id}/decide` | POST | Make approval decision |
| `/approvals/find-by-intent` | POST | Find approved intent |
| `/workflows` | GET/POST | Workflow management |
| `/workflows/{id}/detail` | GET | Enriched workflow view |
| `/workflows/{id}/timeline` | GET | Workflow timeline |
| `/history` | GET | Audit log |
| `/providers/health` | GET | Provider health |
| `/console` | GET | Agent dashboard UI |

## Version Alignment

| Component | Version | Notes |
|-----------|---------|-------|
| Spec | 0.1.0 | Initial capability/workflow/policy |
| Python Core | 0.1.0 | Matches spec |
| Python Runtime | 0.1.0 | Matches spec |
| TypeScript SDK | 0.1.0 | Matches spec |
| MCP Server | 0.1.0 | Bridges to MCP ecosystem |

All components stay aligned initially, then can diverge if needed.

## Non-Negotiable Rules

1. **Deterministic interfaces** — Every capability must be deterministic at interface level
2. **Logged side effects** — Every side effect must be logged
3. **Replayable actions** — Every action must be replayable
4. **Policy-gated risk** — Every risky action must be policy-gated
5. **Resumable workflows** — Every workflow must be resumable
6. **Idempotent flows** — Every flow must be idempotent where possible
7. **Explicit next actions** — Every execution must expose "allowed next actions"
