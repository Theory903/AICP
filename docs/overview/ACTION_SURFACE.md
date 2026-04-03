# Action Surface

> The agent-facing surface of software -- structured, typed, policy-governed actions that replace the ad-hoc tool-calling layer between AI and applications.

---

## What Is an Action Surface?

APIs are optimized for developers. UIs are optimized for humans. Neither is optimized for autonomous agents that must discover, reason about, and safely execute multi-step operations under governance constraints.

An Action Surface is the semantic operating layer where agents can:

1. **Discover** what actions exist and what they do.
2. **Understand** typed inputs, outputs, side-effect classifications, and error codes.
3. **Evaluate** policy before execution -- not after.
4. **Pause** at approval checkpoints when risk requires human judgment.
5. **Resume** safely after approval, rejection, or timeout.
6. **Receive** structured outcomes with continuation guidance.
7. **Audit** every action through an immutable journal.

The Action Surface is not a visual UI. It is not a REST API. It is the canonical interface between agents and the applications they operate.

---

## Action Surface Components

| Component | Purpose | Schema |
|-----------|---------|--------|
| Capability | A governed action with typed I/O, side-effect class, risk metadata | `capability.schema.json` |
| Policy | Rules that allow, deny, or gate actions before execution | `policy.schema.json` |
| Workflow | Multi-step stateful process with branching, retries, compensation | `workflow.schema.json` |
| Execution Envelope | Canonical response from every capability execution | `execution-result.schema.json` |
| Approval Request | Structured pause for human review of risky actions | `approval-request.schema.json` |
| Approval Decision | Human resolution (approve, reject, modify, delegate, escalate) | `approval-decision.schema.json` |
| Audit Entry | Immutable record of every significant event | `audit-entry.schema.json` |
| Discovery Manifest | Machine-readable inventory of available capabilities | `discovery.schema.json` |
| Error | Structured failure with category, retry guidance, recovery hints | `error.schema.json` |

---

## Capability Anatomy

A capability is the atomic unit of the Action Surface. Every capability declares:

```json
{
  "name": "orders.place",
  "description": "Place an order for the current cart contents",
  "kind": "action",
  "input_schema": { "type": "object", "properties": { "cart_id": { "type": "string" } }, "required": ["cart_id"] },
  "output_schema": { "type": "object", "properties": { "order_id": { "type": "string" } } },
  "side_effects": ["financial_transaction", "inventory_change", "notification"],
  "idempotent": false,
  "retry_policy": { "max_retries": 2, "backoff": "exponential" },
  "error_codes": ["cart_empty", "payment_failed", "out_of_stock", "address_missing"],
  "tags": ["commerce", "order"],
  "requires_approval": true,
  "risk_level": "high"
}
```

### Capability Kinds

| Kind | Description | Side Effects | Example |
|------|-------------|-------------|---------|
| `query` | Read-only data retrieval | None | `restaurant.search`, `account.balance` |
| `action` | State-changing operation | Yes | `orders.place`, `payment.transfer` |
| `confirm` | Explicit human confirmation step | None directly | `payment.confirm`, `booking.confirm` |
| `notify` | Fire-and-forget notification | External | `notification.send`, `alert.trigger` |
| `batch` | Bulk operation over a collection | Varies | `orders.bulk_cancel`, `users.bulk_update` |

### Determinism Classification

Every capability declares its determinism class so planners and judges can reason about repeatability:

| Class | Meaning | Example |
|-------|---------|---------|
| `deterministic` | Same input always produces same output | `math.calculate`, `schema.validate` |
| `bounded_nondeterministic` | Output varies within known bounds | `restaurant.search`, `inventory.check` |
| `nondeterministic` | Output is unpredictable | `ai.generate`, `market.price` |

---

## Capability Families

AICP organizes capabilities into families that represent coherent operational domains. At v1.0.0, the protocol targets 100+ capability definitions across these families:

| Family | Prefix | Example Capabilities | Count Target |
|--------|--------|---------------------|-------------|
| Commerce | `orders.*`, `cart.*`, `menu.*` | `orders.place`, `cart.add`, `menu.search` | 15+ |
| Payments | `payment.*` | `payment.transfer`, `payment.confirm`, `payment.refund` | 10+ |
| Identity | `auth.*`, `user.*`, `org.*` | `auth.login`, `user.profile`, `org.invite` | 12+ |
| Travel | `booking.*`, `flight.*`, `hotel.*` | `booking.create`, `flight.search`, `hotel.reserve` | 12+ |
| Forms | `form.*`, `document.*` | `form.fill`, `form.validate`, `document.sign` | 8+ |
| Support | `ticket.*`, `issue.*` | `ticket.create`, `ticket.resolve`, `issue.escalate` | 8+ |
| Enterprise | `approval.*`, `invoice.*`, `report.*` | `approval.route`, `invoice.process` | 10+ |
| Communication | `notification.*`, `message.*` | `notification.send`, `message.compose` | 6+ |
| Data | `query.*`, `export.*`, `import.*` | `query.execute`, `export.csv`, `import.bulk` | 8+ |
| Admin | `config.*`, `audit.*`, `policy.*` | `config.update`, `audit.search`, `policy.evaluate` | 10+ |

---

## Execution Envelope

Every capability execution produces the canonical execution envelope. This is the single most important data structure in AICP -- all planes consume it.

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
  "data": { "order_id": "ord_m3n4o5p6" },
  "error": null,
  "error_detail": null,
  "execution_time_ms": 234,
  "idempotency_key": "cart_q7r8s9t0",
  "allowed_next_actions": [
    {
      "kind": "capability",
      "name": "order.track",
      "reason": "Track delivery",
      "requires_approval": false,
      "confidence": 0.95
    }
  ],
  "rendered": "Order placed. Estimated delivery: 7:30 PM.",
  "format_hint": "text",
  "audit_correlation_id": "corr_u1v2w3x4",
  "actor": {
    "type": "agent",
    "agent_id": "agent_y5z6",
    "session_id": "sess_i9j0k1l2"
  },
  "timestamp": "2026-04-03T18:45:12.456Z"
}
```

### Envelope Field Reference

| Field | Type | Purpose |
|-------|------|---------|
| `execution_id` | string | Unique identifier for this execution |
| `capability_name` | string | Which capability was invoked |
| `capability_kind` | enum | `query`, `action`, `confirm`, `notify`, `batch` |
| `determinism_class` | enum | `deterministic`, `bounded_nondeterministic`, `nondeterministic` |
| `workflow_id` | string? | Parent workflow if executing within one |
| `step_id` | string? | Current step within workflow |
| `session_id` | string | Execution session context |
| `execution_mode` | enum | `sync`, `async`, `streaming`, `deferred` |
| `policy_result` | object | Full policy evaluation outcome |
| `approval_state` | object | Approval lifecycle state |
| `status` | enum | `success`, `failure`, `pending_approval`, `compensated` |
| `data` | object? | Successful result payload |
| `error` | string? | Error code on failure |
| `error_detail` | object? | Structured error details |
| `execution_time_ms` | number | Wall-clock execution time |
| `idempotency_key` | string? | For retry deduplication |
| `allowed_next_actions` | array | What the agent can do next |
| `rendered` | string? | Human-readable summary |
| `format_hint` | enum | `text`, `markdown`, `json`, `html` |
| `audit_correlation_id` | string | Links to audit trail |
| `actor` | object | Who initiated the action |
| `timestamp` | string | ISO 8601 execution time |

---

## Execution Modes

| Mode | Latency | Use Case | v0.1.1 |
|------|---------|----------|--------|
| `sync` | <500ms | Simple queries and actions | Implemented |
| `async` | Seconds to hours | Long-running operations with callbacks | Planned (v0.3.0) |
| `streaming` | Continuous | Real-time data feeds, progress updates | Planned (v0.4.0) |
| `deferred` | Scheduled | Batch jobs, scheduled operations | Planned (v0.5.0) |

---

## Side-Effect Classification

Every capability must declare its side effects so the governance plane can make informed policy decisions:

| Side Effect | Risk Factor | Example |
|------------|-------------|---------|
| `financial_transaction` | High | Payment processing, refunds |
| `data_mutation` | Medium | Database writes, record updates |
| `external_api_call` | Medium | Third-party service invocations |
| `notification` | Low | Email, SMS, push notifications |
| `inventory_change` | Medium | Stock adjustments, reservations |
| `access_control_change` | High | Permission grants, role assignments |
| `pii_access` | High | Personal data reads |
| `none` | None | Pure computation, read-only queries |

---

## Design Rules

These are non-negotiable properties of a well-formed Action Surface:

| Rule | Rationale |
|------|-----------|
| No hidden state | Agents cannot reason about what they cannot observe |
| No ambiguous outcomes | Every execution produces a typed, structured result |
| No unstructured failures | Errors have codes, categories, and recovery hints |
| No policy as afterthought | Policy evaluation happens before side effects, always |
| No human-only assumptions | Every interaction path must be machine-navigable |
| No implicit transitions | State changes require explicit, auditable actions |
| No fire-and-forget side effects | Every side effect is logged and traceable |

---

## Relationship to AICP Products

| Product | Role | Action Surface Interaction |
|---------|------|---------------------------|
| **Protocol** | Defines the contract | JSON schemas that specify capability, policy, workflow, execution envelope structures |
| **Runtime** | Executes the contract | Evaluates policy, runs capabilities, persists state, produces execution envelopes |
| **Connect** | Imports into the contract | Adapters (OpenAPI, MCP, cURL, HAR, Postman) that wrap existing APIs as governed capabilities |
| **Studio** | Observes the contract | Dashboard for approval queues, audit trails, workflow visualization, policy editing |

---

## v0.1.1 Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Capability schema and validation | Complete | 9 JSON schemas in `/spec/schemas/` |
| Policy evaluation before execution | Complete | JSON rule engine |
| Approval checkpoints | Complete | CLI inline + API |
| Execution envelope | Complete | All fields populated |
| `allowed_next_actions` | Complete | Returned on every execution |
| Audit trail | Complete | Append-only journal |
| Sync execution mode | Complete | Default mode |
| Async execution mode | Not started | Planned for v0.3.0 |
| Streaming execution mode | Not started | Planned for v0.4.0 |
| Semantic capability discovery | Partial | Keyword scoring only, embeddings planned |

---

## See Also

- [VISION.md](./VISION.md) -- Why the Agentic Web OS exists
- [GOVERNANCE.md](./GOVERNANCE.md) -- Policy, trust tiers, and risk scoring
- [HITL.md](./HITL.md) -- Human-in-the-loop approval model
- [/spec/schemas/](../../spec/schemas/) -- JSON schema source of truth
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- 11-plane system architecture
- [/MODULE_MAP.md](../../MODULE_MAP.md) -- Feature-to-module mapping
