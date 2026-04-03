# Human-in-the-Loop (HITL)

> Human-in-the-loop is a protocol checkpoint in AICP, not a popup. It is a structured lifecycle with persistence, traceability, and multiple resolution modes.

---

## Overview

When an agent encounters a high-risk action, AICP does not fire-and-forget or silently proceed. The governance plane evaluates policy, determines that human judgment is required, creates a structured approval request, pauses execution, and waits for an explicit human decision before resuming.

This is the principal model: humans are principals who delegate authority to agents within bounded trust tiers. HITL checkpoints are where that delegation boundary is enforced.

---

## Flow

```
Agent requests capability execution
  │
  ▼
Policy evaluation ──> effect = "allow" ──> Execute immediately
  │
  │ effect = "ask" or "require_approval"
  ▼
Create approval request (structured, persisted)
  │
  ▼
Pause execution (state persisted, resumable)
  │
  ▼
Route to human via configured channel
  │
  ├──> CLI inline prompt (< 1s)
  ├──> REST API (< 1s)
  ├──> Dashboard queue (seconds)
  ├──> Slack / webhook (seconds-minutes)
  ├──> Email (minutes-hours)
  └──> Auto-threshold (< 1ms, if enabled)
  │
  ▼
Human reviews:
  - What capability is being invoked
  - What arguments are being passed
  - What risk scores were computed
  - What policy triggered the checkpoint
  - What workflow context exists
  │
  ▼
Human decides:
  ├──> Approve ──> Resume with original arguments
  ├──> Reject ──> Return structured rejection
  ├──> Modify ──> Resume with changed arguments (diff recorded)
  ├──> Delegate ──> Re-route to another approver
  └──> Escalate ──> Bump to higher authority
  │
  ▼
Audit entry recorded (decision, actor, timestamp, reason)
```

---

## Approval Request Structure

When the runtime creates an approval request, it includes everything the human needs to make an informed decision:

```json
{
  "approval_id": "appr_a1b2c3",
  "capability_name": "payment.transfer",
  "arguments": { "recipient": "rahul@example.com", "amount": 1000, "currency": "INR" },
  "risk_score": { "financial": 0.8, "irreversibility": 0.9, "privacy": 0.1 },
  "policy_name": "high_value_transfers",
  "policy_reason": "Transfer amount exceeds auto-approve threshold (500 INR)",
  "trust_tier": 2,
  "session_id": "sess_x1y2z3",
  "workflow_id": "wf_e5f6g7",
  "step_id": "step_transfer",
  "requested_at": "2026-04-03T18:45:00.000Z",
  "timeout_seconds": 3600,
  "actor": { "type": "agent", "agent_id": "agent_abc" }
}
```

---

## Approval Decisions

| Decision | When to Use | Effect on Execution |
|----------|------------|-------------------|
| `approve` | Action is safe as-is | Resume with original arguments |
| `reject` | Action should not proceed | Return rejection reason to agent |
| `modify` | Action is acceptable with changes | Resume with modified arguments; diff is audit-logged |
| `delegate` | Different person should decide | Re-route to specified approver |
| `escalate` | Higher authority needed | Re-route with escalation metadata and urgency bump |

---

## Variable Human Involvement

Not all HITL checkpoints require the same level of human engagement. AICP supports a spectrum:

| Mode | Human Effort | Description | v0.1.1 |
|------|-------------|-------------|--------|
| Full review | High | Human examines all arguments and context | Implemented |
| Quick approve | Medium | Human sees summary, approves/rejects | Implemented |
| Auto-threshold | None | Below-threshold actions auto-approved, logged | Planned |
| Batch review | Low | Multiple approvals reviewed together | Planned |
| Delegated review | Varies | Routed to domain expert | Planned |

### Auto-Threshold Approval

At Trust Tier 3+, policies can define auto-approval thresholds. Actions below the threshold are automatically approved but still produce audit entries:

```json
{
  "policy_name": "payment_auto_threshold",
  "effect": "require_approval",
  "auto_approve": {
    "enabled": true,
    "conditions": {
      "risk_score_below": 0.3,
      "trust_tier_min": 3,
      "amount_below": 500
    }
  }
}
```

---

## Persistence and Resumability

HITL checkpoints are not ephemeral. The approval state is persisted so that:

| Requirement | Implementation |
|-------------|---------------|
| Approval survives process restart | State persisted to storage backend |
| Approval can be resolved hours later | Timeout configurable per policy |
| Modified arguments are recorded | Original + modified arguments stored in audit |
| Resume is explicit | Agent or system must call resume endpoint |
| Multiple pending approvals tracked | Approval queue with per-session scoping |

---

## Intent Matching on Resume

When an approval is resolved and execution resumes, the runtime uses intent matching to verify that the resumed action still makes sense in the current session context. This prevents stale approvals from executing against changed state.

```
Approval resolved
  │
  ▼
Match approval to pending execution context
  │
  ├──> Context unchanged ──> Resume execution
  ├──> Context changed (minor) ──> Resume with warning in audit
  └──> Context invalidated ──> Reject resume, notify agent
```

This is implemented and working in v0.1.1.

---

## What HITL Is Not

| HITL is not... | Because... |
|----------------|-----------|
| A UI alert | It is a protocol-level execution checkpoint with structured lifecycle |
| An informal email thread | Decisions are typed, persisted, and audit-logged |
| A hidden side channel | The agent knows it is paused and why |
| A blocking synchronous call | Execution is suspended, not blocking a thread |
| Optional for high-risk actions | Policy enforcement is mandatory; cannot be bypassed |

---

## v0.1.1 Implementation Status

| Feature | Status |
|---------|--------|
| Approval request creation | Complete |
| Approval decision resolution | Complete |
| CLI inline approval prompt (`--yes`, `--no-input`) | Complete |
| REST API approval endpoints | Complete |
| Intent matching on resume | Complete |
| Approval state persistence | Complete |
| Dashboard approval queue | Planned (v0.3.0) |
| Slack/webhook integration | Planned (v0.4.0) |
| Auto-threshold approval | Planned (v0.3.0) |
| Batch review | Planned (v0.5.0) |

---

## See Also

- [GOVERNANCE.md](./GOVERNANCE.md) -- Policy evaluation, trust tiers, risk scoring
- [ACTION_SURFACE.md](./ACTION_SURFACE.md) -- Capability model and execution envelope
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- Supervision Plane (Plane 9)
- [/MODULE_MAP.md](../../MODULE_MAP.md) -- Module 7: Human Cognitive Protocols
