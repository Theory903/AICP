# Governance

> Policy evaluation, trust tiers, risk scoring, approval lifecycles, and audit trails -- governance is protocol-native in AICP, not middleware bolted on after the fact.

---

## Why Governance Is First-Class

Without governance, agents can act but cannot be safely controlled, inspected, or audited. Every other agent framework treats governance as optional middleware. AICP treats it as a protocol plane.

The Governance Plane (Plane 5) ensures that:

- Every capability execution is policy-evaluated **before** side effects occur.
- Every risky action is risk-scored across multiple dimensions.
- Every approval follows a structured lifecycle with full audit trail.
- Every decision is attributable to a specific actor (agent, human, or system).
- Every policy outcome is machine-readable and inspectable.

---

## Core Primitives

| Primitive | Schema | Purpose |
|-----------|--------|---------|
| Policy | `policy.schema.json` | Rules defining what is allowed, denied, or requires approval |
| Approval Request | `approval-request.schema.json` | Structured pause for human review |
| Approval Decision | `approval-decision.schema.json` | Human resolution of an approval request |
| Audit Entry | `audit-entry.schema.json` | Immutable record of every significant event |
| Trust Tier | (embedded in policy) | Agent autonomy level (0-4) |
| Risk Score | (embedded in execution result) | Multi-dimensional risk assessment |

---

## Policy Effects

Every policy evaluation produces one of these effects:

| Effect | Meaning | Execution Behavior |
|--------|---------|-------------------|
| `allow` | Action permitted | Execute immediately |
| `deny` | Action forbidden | Return denial with structured reason |
| `ask` | Soft approval needed | Pause, request human input, resume on decision |
| `require_approval` | Hard approval needed | Pause, block until explicit approval |
| `limit` | Action permitted with constraints | Execute with rate limits, amount caps, or scope restrictions |

### Policy Evaluation Order

```
Request arrives
  -> Match capability against policy rules (most specific first)
  -> Evaluate trust tier of the actor
  -> Compute risk score across all dimensions
  -> Apply threshold rules
  -> Produce policy result with effect + reason
  -> If allow/limit: proceed to execution
  -> If deny: return structured denial
  -> If ask/require_approval: create approval request, pause execution
```

---

## Trust Tiers

Trust tiers define the baseline autonomy level of an agent or session. Higher tiers grant broader default permissions.

| Tier | Name | Default Policy | Use Case |
|------|------|---------------|----------|
| 0 | Anonymous | Deny all side effects | Unknown agents, public discovery |
| 1 | Authenticated | Allow reads, require approval for writes | New agents, untrusted integrations |
| 2 | Trusted | Allow most actions, require approval for high-risk | Established agents, standard operations |
| 3 | Privileged | Allow all except critical, auto-approve medium-risk | Internal agents, automated workflows |
| 4 | Autonomous | Allow all, log-only governance | Fully verified agents, production automation |

### Trust Tier Escalation

Trust tiers are not permanent. They can be:

- **Promoted** based on successful execution history and low error rates.
- **Demoted** based on policy violations, anomalous behavior, or explicit operator action.
- **Scoped** to specific capability families (e.g., Tier 3 for `orders.*` but Tier 1 for `payment.*`).

---

## Risk Scoring

Every capability execution computes a multi-dimensional risk score. The formula:

```
R = severity * likelihood * (1 - mitigation)
```

### Risk Dimensions

| Dimension | Description | Weight | Example |
|-----------|-------------|--------|---------|
| `financial` | Monetary impact | 0.0-1.0 | Payment amount relative to account limits |
| `irreversibility` | Can this be undone? | 0.0-1.0 | Delete operations score high |
| `privacy` | PII exposure risk | 0.0-1.0 | Accessing personal data |
| `availability` | Service disruption risk | 0.0-1.0 | Bulk operations, resource exhaustion |
| `compliance` | Regulatory exposure | 0.0-1.0 | Actions touching regulated data |
| `reputation` | Brand/trust damage | 0.0-1.0 | Customer-facing communications |

### Risk Thresholds

| Combined Score | Default Effect | Override |
|---------------|----------------|----------|
| 0.0 - 0.3 | `allow` | Policy can override to `ask` |
| 0.3 - 0.6 | `ask` | Policy can override to `allow` or `require_approval` |
| 0.6 - 0.8 | `require_approval` | Policy can override to `ask` for Tier 3+ |
| 0.8 - 1.0 | `deny` | Only Tier 4 can override |

---

## Approval Lifecycle

When policy evaluation produces `ask` or `require_approval`, the runtime creates an approval request and pauses execution.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Pending  │────>│ Reviewed │────>│ Approved │───> Resume execution
└──────────┘     └──────────┘     └──────────┘
      │                │               
      │                └──────────>┌──────────┐
      │                            │ Rejected │───> Return denial
      │                            └──────────┘
      │                                 
      └───────────────────────────>┌──────────┐
                                   │ Expired  │───> Return timeout
                                   └──────────┘
```

### Approval Decisions

| Decision | Meaning | Effect |
|----------|---------|--------|
| `approve` | Allow the action as-is | Resume with original arguments |
| `reject` | Deny the action | Return structured rejection reason |
| `modify` | Allow with changed arguments | Resume with modified arguments (recorded in audit) |
| `delegate` | Forward to another approver | Re-route approval request |
| `escalate` | Bump to higher authority | Re-route with escalation metadata |

### Approval Channels (v1.0.0 Target)

| Channel | Latency | v0.1.1 Status |
|---------|---------|---------------|
| CLI inline prompt | <1s | Implemented |
| REST API | <1s | Implemented |
| Dashboard queue | Seconds | Planned |
| Slack / webhook | Seconds-minutes | Planned |
| Email | Minutes-hours | Planned |
| Auto-threshold | <1ms | Planned |

---

## Audit Trail

Every significant event produces an immutable audit entry. The audit trail is append-only and cannot be modified or deleted.

### What Gets Audited

| Event | Trigger |
|-------|---------|
| Capability execution | Every invocation, successful or failed |
| Policy evaluation | Every policy check with full result |
| Approval request created | When execution pauses for approval |
| Approval decision made | When human resolves an approval |
| Workflow state transition | Every step change in a workflow |
| Session created/resumed | Session lifecycle events |
| Trust tier change | Promotion or demotion |
| Error and compensation | Failures and rollback actions |

### Audit Entry Structure

```json
{
  "entry_id": "audit_x1y2z3",
  "timestamp": "2026-04-03T18:45:12.456Z",
  "event_type": "capability_executed",
  "actor": { "type": "agent", "agent_id": "agent_y5z6" },
  "capability_name": "orders.place",
  "execution_id": "exec_a1b2c3d4",
  "session_id": "sess_i9j0k1l2",
  "workflow_id": "wf_e5f6g7h8",
  "policy_effect": "allow",
  "status": "success",
  "correlation_id": "corr_u1v2w3x4",
  "metadata": {}
}
```

---

## Policy Engine Evolution

| Phase | Engine | Capability | v0.1.1 |
|-------|--------|-----------|--------|
| Phase 0-1 | JSON rule matching | Pattern-based allow/deny/ask | Implemented |
| Phase 2 | Compiled policy engine | Complex conditions, variables, functions | Planned |
| Phase 3 | WASM policy modules | Custom policy logic, portable execution | Planned |
| Phase 4 | Policy learning | Anomaly detection, auto-calibration | Planned |

### Known Spec Gap

There is no defined migration path from JSON rule policies to WASM policy modules. This is tracked as an open spec gap in STATUS.md. The v0.3.0 milestone should define the migration semantics.

---

## v0.1.1 Implementation Status

| Feature | Status |
|---------|--------|
| JSON rule-based policy evaluation | Complete |
| Policy effects (allow, deny, ask, require_approval) | Complete |
| Approval request/decision lifecycle | Complete |
| CLI inline approval prompt | Complete |
| REST API approval endpoints | Complete |
| Append-only audit journal | Complete |
| Trust tier enforcement | Partial (session tokens, basic auth) |
| Multi-dimensional risk scoring | Not started |
| Anomaly detection | Not started |
| WASM policy modules | Not started |

---

## Principles

| Principle | Meaning |
|-----------|---------|
| Policy is protocol-native | Governance is in the schema, not bolted on as middleware |
| Approvals are execution checkpoints | Not UI popups -- structured lifecycle objects |
| Audit is immutable | Append-only, no edits, no deletes |
| Decisions must be inspectable | Every policy outcome includes structured reasons |
| Fail closed | If policy evaluation fails, deny the action |
| Defense in depth | Policy checked at API boundary, service layer, and data layer |

---

## See Also

- [ACTION_SURFACE.md](./ACTION_SURFACE.md) -- Capability model and execution envelope
- [HITL.md](./HITL.md) -- Human-in-the-loop approval model
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- Governance Plane (Plane 5)
- [/MODULE_MAP.md](../../MODULE_MAP.md) -- Module 12: Governance and Policy
- [/spec/schemas/policy.schema.json](../../spec/schemas/policy.schema.json) -- Policy schema
