# Technical Specification

> Protocol technical specification — core data model and behavior for AICP-compliant implementations.

---

## Scope

This specification defines the core data model and behavior required for the AICP v1.0.0 feature set, including complete L5 protocol with 16 JSON schemas.

---

## Protocol Versioning

| Version | Status | Compliance Level |
|---------|--------|-----------------|
| v1.0.0 | Current | L5 (Protocol Ready) |
| v0.3.0 | Previous milestone | L3+L4 |
| v0.2.0 | Historical | L4 (AI Planning Support) |

**Note:** v1.0.0 protocol is complete. Real service implementations for modules 6, 16-20 are in progress. |

---

## Core Objects

### Capability

The atomic semantic action exposed to AI systems.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Fully qualified capability name (e.g., `payments.transfer`) |
| `description` | string | Yes | Human-readable description |
| `kind` | enum | Yes | `query`, `action`, `confirm`, `notify`, `batch` |
| `input_schema` | JSON Schema | Yes | Input validation schema |
| `output_schema` | JSON Schema | Yes | Output result schema |
| `side_effects` | array | No | Declared side effects |
| `idempotent` | boolean | No | Whether repeated calls produce same result |
| `retry_policy` | object | No | Retry configuration |
| `error_codes` | array | No | Defined error codes |
| `tags` | array | No | Capability tags for discovery |
| `requires_approval` | boolean | No | Whether approval is required |
| `risk_level` | enum | No | `low`, `medium`, `high`, `critical` |
| `determinism_class` | enum | No | `deterministic`, `bounded_nondeterministic`, `nondeterministic` |

### Capability Kinds

| Kind | Description | Side Effects |
|------|-------------|-------------|
| `query` | Read-only data retrieval | None |
| `action` | State-changing operation | Yes |
| `confirm` | Explicit human confirmation | None directly |
| `notify` | Fire-and-forget notification | External |
| `batch` | Bulk operation over collection | Varies |

---

## Input and Output Type Requirements

### Input Schema Requirements

| Feature | Description |
|---------|-------------|
| Scalar types | `string`, `number`, `boolean`, `integer` |
| Arrays | `array` with `items` definition |
| Objects | `object` with `properties` and `required` |
| Enums | `enum` with allowed values |
| Nested schemas | `$ref` to other schema definitions |
| Required vs optional | `required` array in parent |
| Constraints | `minimum`, `maximum`, `minLength`, `pattern`, etc. |
| Defaults | `default` value specification |

### Output Schema Requirements

| Feature | Description |
|---------|-------------|
| Structured success data | Object with typed fields |
| Nested objects | Complex result structures |
| Enums | Status codes, result types |
| Optional fields | Nullable or optional properties |
| Render hints | Links to presentation guidance |

---

## Policy Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `effect` | enum | `allow`, `deny`, `ask`, `require_approval`, `limit` |
| `conditions` | object | Policy matching conditions |
| `risk` | object | Risk score configuration |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `approval_thresholds` | object | Auto-approval thresholds |
| `role_requirements` | array | Required roles |
| `rate_limits` | object | Rate limiting configuration |
| `cost_limits` | object | Cost threshold configuration |
| `environment_restrictions` | object | Environment constraints |

---

## Workflow State Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | string | Unique workflow identifier |
| `name` | string | Workflow name |
| `current_step` | string | Current step ID |
| `completed_steps` | array | List of completed step IDs |
| `next_possible_steps` | array | Valid next steps from current state |
| `status` | enum | `pending`, `running`, `paused`, `completed`, `failed`, `compensated` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `pending_approvals` | array | Outstanding approval requests |
| `warnings` | array | Warning messages |
| `context` | object | Workflow context data |
| `last_result` | object | Last step execution result |
| `compensation_policy` | object | Rollback behavior (v1.0.0) |

---

## Execution Result Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | string | Unique execution identifier |
| `capability_name` | string | Invoked capability |
| `status` | enum | See Statuses below |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `data` | object | Successful result payload |
| `error` | object | Error details |
| `pagination` | object | Pagination info for list results |
| `job` | object | Async job status |
| `render` | object | Render hints |
| `policy_result` | object | Policy evaluation result |
| `approval_state` | object | Approval lifecycle state |
| `allowed_next_actions` | array | What the agent can do next |
| `execution_time_ms` | number | Wall-clock execution time |
| `idempotency_key` | string | For retry deduplication |
| `actor` | object | Who initiated the action |

---

## Standard Statuses

### Success-Related

| Status | Description |
|--------|-------------|
| `success` | Capability executed successfully |
| `partial_success` | Some work completed with warnings |
| `paginated` | Results span multiple pages |
| `async_pending` | Long-running job submitted |

### Input/Decision-Related

| Status | Description |
|--------|-------------|
| `needs_input` | Additional input required |
| `needs_confirmation` | Explicit confirmation needed |
| `pending_approval` | Paused for human approval |

### Failure-Related

| Status | Description |
|--------|-------------|
| `denied` | Policy denied execution |
| `invalid_input` | Input validation failed |
| `unavailable` | Service unavailable |
| `rate_limited` | Rate limit exceeded |
| `timeout` | Execution timed out |
| `failed` | General failure |
| `compensated` | Rollback completed |

---

## Error Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Error code |
| `message` | string | Human-readable message |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `field` | string | Field that caused error |
| `retryable` | boolean | Whether operation can be retried |
| `details` | object | Additional error details |
| `upstream_status` | number | Original HTTP status code |
| `correlation_id` | string | Links to execution context |

---

## Pagination Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Result items |
| `page_info` | object | Pagination metadata |

### Page Info Fields

| Field | Type | Description |
|-------|------|-------------|
| `has_next_page` | boolean | More pages available |
| `next_token` | string | Token for next page |
| `end_cursor` | string | Cursor for current position |
| `count` | number | Total items count |

---

## Async Job Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `status` | enum | Job status |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `poll_after_ms` | number | Recommended poll interval |
| `submitted_at` | string | Submission timestamp |
| `completed_at` | string | Completion timestamp |
| `result` | object | Job result when complete |
| `error` | object | Error if failed |

---

## Render Contract

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_hint` | enum | `text`, `markdown`, `json`, `html` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `rendered` | string | Human-readable summary |
| `important_fields` | array | Fields to highlight |
| `empty_state_message` | string | Message for empty results |
| `suggested_actions` | array | Recommended next actions |
| `title` | string | Result title |

---

## Discovery Contract

The discovery endpoint returns:

| Field | Description |
|-------|-------------|
| `protocol_version` | AICP protocol version |
| `capabilities` | List of available capabilities |
| `type_definitions` | Shared type definitions |
| `workflows` | Available workflow definitions |
| `policies` | Policy configurations |
| `metadata` | Extension metadata |

---

## Execution Envelope (Canonical Response)

Every capability execution returns this structure:

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

---

## Extension Model

Extensions must:
- Not break existing required fields
- Use namespacing for experimental features
- Be documented in `/spec/extensions/`

---

## Versioning

AICP follows semantic versioning:
- **major**: Breaking changes to required fields
- **minor**: Backwards-compatible additions
- **patch**: Clarifications and fixes

---

## JSON Schema Reference

All protocol objects are defined in `/spec/schemas/`:

| Schema | Description |
|--------|-------------|
| `capability.schema.json` | Capability definition |
| `workflow.schema.json` | Workflow definition |
| `policy.schema.json` | Policy rules |
| `execution-result.schema.json` | Execution response |
| `error.schema.json` | Error structure |
| `approval-request.schema.json` | Approval request |
| `approval-decision.schema.json` | Approval decision |
| `audit-entry.schema.json` | Audit record |
| `discovery.schema.json` | Discovery manifest |

---

## Implementation Requirements

1. All capability definitions must validate against JSON schemas
2. All runtime implementations must handle standard statuses
3. All adapters must preserve AICP semantics
4. All error responses must use the error contract
5. All list responses must use the pagination contract
6. All executions must produce the canonical execution envelope

---

## See Also

- [/spec/schemas/](../../spec/schemas/) — JSON schema source of truth
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model details
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and trust tier details
- [/ARCHITECTURE.md](../../ARCHITECTURE.md] — 11-plane system architecture
