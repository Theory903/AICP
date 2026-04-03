# Agentic Experience

> How AICP delivers an AI-optimized experience — designed so that even small models can effectively operate complex applications without needing to infer, guess, or reason about system behavior.

---

## The Vision

AICP should be the **easiest protocol for AI to process**. Not "machine-readable" — but **AI-optimized**. Designed so that:

- A 1B parameter model can use it effectively
- Reasoning required is minimized to near-zero
- Every response tells the AI exactly what to do next
- Ambiguity is eliminated at every level
- The AI never has to guess, infer, or wonder

This is achieved through **cognitive protocols** — configuration profiles that adapt AICP behavior to different operational domains (UX, SWE, Ops, Research, Finance).

---

## Core Principle: AI-Ease Over Human-Ease

| Traditional APIs | Traditional Tool Schemas | AICP |
|-----------------|-------------------------|------|
| Designed for developers | Designed for prompt engineers | Designed for AI agents themselves |

AICP optimizes for:
- **Parseability**: AI can extract meaning without inference
- **Actionability**: AI knows what to do next from every response
- **Safety**: AI knows what's risky without guessing
- **Progress**: AI tracks workflow state without tracking it manually

---

## Cognitive Protocols

Cognitive protocols define how AICP adapts to different operational domains. Each protocol configures:

| Parameter | UX | SWE | Ops | Research | Finance |
|-----------|-----|------|-----|----------|--------|
| Default trust tier | 2 | 3 | 2 | 3 | 1 |
| Approval sensitivity | Medium | Low | High | Low | Very High |
| Risk weight priority | privacy > reputation > financial | availability > irreversibility > compliance | availability > financial > irreversibility | privacy > compliance > financial | financial > compliance > irreversibility |
| Render format | Rich (markdown, cards) | Technical (JSON, logs) | Dashboard (metrics, alerts) | Data (tables, charts) | Formal (receipts, confirmations) |
| Audit level | Normal | Verbose | Normal | Normal | Verbose |

### Protocol Configuration Example

```json
{
  "protocol": "finance",
  "trust_tier_default": 1,
  "approval_threshold": 0.2,
  "risk_weights": {
    "financial": 1.0,
    "compliance": 0.9,
    "irreversibility": 0.8,
    "privacy": 0.5,
    "availability": 0.3,
    "reputation": 0.4
  },
  "auto_approve_enabled": false,
  "render_format": "formal",
  "audit_level": "verbose"
}
```

---

## Design Rules for AI-Ease

### Rule 1: Explicit Over Implicit

**Traditional API response:**
```json
{ "error": "failed" }
```

**AICP response:**
```json
{
  "status": "failed",
  "error": {
    "code": "invalid_amount",
    "message": "Amount must be greater than 0",
    "field": "amount",
    "retryable": false,
    "fix_hint": "Provide a positive number for amount"
  }
}
```

The AI knows exactly what happened and what to do.

---

### Rule 2: Always Include Next Steps

**Traditional API:** Return result, let AI figure out next move.

**AICP:** Every response includes `allowed_next_actions`:

```json
{
  "status": "success",
  "data": { "order_id": "ord_123" },
  "allowed_next_actions": [
    {
      "kind": "capability",
      "name": "order.track",
      "reason": "Track delivery status",
      "requires_approval": false,
      "confidence": 0.95
    }
  ]
}
```

The AI never wonders "what now?"

---

### Rule 3: Enforced Action Types

**Traditional:** AI must guess if an action is safe to auto-execute.

**AICP:** Every capability declares policy upfront:

```json
{
  "name": "payment.transfer",
  "requires_approval": true,
  "risk_level": "high",
  "side_effects": ["financial_transaction", "irreversible"],
  "determinism_class": "bounded_nondeterministic"
}
```

The AI knows whether to ask or proceed.

---

### Rule 4: Schema Is Contract

**Traditional:** `input: { ... }` — AI must interpret what fields mean.

**AICP:** Every input field has complete metadata:

```json
{
  "input_schema": {
    "type": "object",
    "properties": {
      "recipient_id": {
        "type": "string",
        "description": "Unique recipient identifier",
        "example": "user_123",
        "required": true,
        "format": "uuid"
      }
    },
    "required": ["recipient_id"]
  }
}
```

The AI knows exactly what's valid.

---

### Rule 5: State Is Always Current

**Traditional:** AI must track workflow progress manually.

**AICP:** Workflow state is embedded in every response:

```json
{
  "workflow_id": "wf_order_123",
  "step_id": "step_payment",
  "current_step": "payment.confirm",
  "completed_steps": [
    "restaurant.search",
    "menu.select", 
    "cart.review",
    "address.select"
  ],
  "next_possible_steps": ["payment.confirm", "cancel_order"],
  "missing_inputs": []
}
```

The AI never loses track.

---

### Rule 6: Built-in Validation Feedback

**Traditional:** AI sends invalid input, gets generic error.

**AICP:** Structured validation errors with fix hints:

```json
{
  "status": "invalid_input",
  "error": {
    "code": "validation_failed",
    "message": "Input validation failed",
    "errors": [
      {
        "field": "email",
        "error": "format_invalid",
        "message": "Email format invalid",
        "received": "john@",
        "expected": "user@domain.com"
      }
    ],
    "fix_hint": "Provide valid email address and retry"
  }
}
```

The AI can auto-fix and retry.

---

### Rule 7: Opinionated Over Flexible

**Traditional:** Many ways to do the same thing.

**AICP:** One canonical way:

- Standard capability naming: `{domain}.{action}` (e.g., `payments.transfer`)
- Standard status values: `success`, `failure`, `pending_approval`
- Standard error codes: `invalid_input`, `denied`, `unavailable`
- Standard workflow patterns: sequential, parallel, compensation

The AI can predict and template.

---

## Perception Model

AICP's Perception Plane (Plane 1) enables agents to observe the state of web applications:

| Capability | Description |
|------------|-------------|
| a11y tree | Accessibility tree for UI element discovery |
| DOM observation | Real-time DOM mutation tracking |
| Screenshots | Visual state capture |
| Behavioral signals | User interaction patterns |

This allows agents to understand not just what APIs exist, but what the application state actually looks like.

---

## 11-Plane Awareness

AICP enables agents to be aware of all 11 planes simultaneously:

```
Plane 0: Signal      → Event ingestion, dedup, routing
Plane 1: Perception  → a11y tree, DOM, screenshots, behavioral signals
Plane 2: AI         → Planner, Judge, memory, cognitive protocols
Plane 3: Capability → Registry, discovery, semantic search
Plane 4: Workflow   → Sequential, parallel, sagas, compensation
Plane 5: Governance → Policy, trust tiers, risk scoring, approvals
Plane 6: Execution   → Realtime, transactional, event-driven
Plane 7: Multi-Agent→ Orchestrator, specialist, worker, supervisor
Plane 8: Federation → .well-known/aicp, CRDT, DID auth
Plane 9: Supervision→ Live feed, approval queue, replay debugger
Plane 10: Learning  → Skill mining, drift detection, calibration
```

---

## Response Templates

### Success Template

```json
{
  "status": "success",
  "capability_name": "orders.place",
  "data": { "order_id": "ord_123" },
  "workflow_id": "wf_order_123",
  "allowed_next_actions": [
    { "name": "order.track", "requires_approval": false, "confidence": 0.95 }
  ],
  "rendered": "Order #123 placed successfully. Estimated delivery: 7:30 PM.",
  "format_hint": "text"
}
```

### Failure Template

```json
{
  "status": "failure",
  "capability_name": "payment.transfer",
  "error": {
    "code": "insufficient_balance",
    "message": "Account balance too low",
    "field": "amount",
    "retryable": true,
    "fix_hint": "Reduce amount or add funds to account"
  },
  "allowed_next_actions": [
    { "name": "account.add_funds", "requires_approval": false },
    { "name": "payment.reduce_amount", "requires_approval": false }
  ]
}
```

### Approval Required Template

```json
{
  "status": "pending_approval",
  "capability_name": "payment.transfer",
  "approval_state": {
    "approval_id": "apr_abc123",
    "status": "pending",
    "requested_at": "2026-04-03T18:45:00Z",
    "timeout_seconds": 3600
  },
  "data": { "transfer_id": "txn_123" },
  "message": "Transfer of ₹1000 to Rahul requires approval"
}
```

---

## Why This Matters

### Traditional Tool Calling
```
AI: "I need to call payments.transfer... but what if it fails?
     What do I do next? Is this safe? What's the current state?"
```

### AICP Agentic Experience
```
AI: "Status is pending_approval. Policy requires_approval=true.
     I must wait for human decision. Here's the approval_id..."
```

**The AI doesn't think. It follows.**

---

## Implementation Priority

| Phase | Focus | v0.1.1 |
|-------|-------|--------|
| Phase 1 | Response templates, allowed_next_actions, structured errors | Implemented |
| Phase 2 | Workflow state tracking, current step context | Implemented |
| Phase 3 | Semantic discovery, cognitive protocols | Planned (v0.4.0) |
| Phase 4 | Perception layer, multi-agent coordination | Planned (v0.5.0+) |

---

## The Promise

With AICP, even a small model can:

| Capability | AICP Provides |
|------------|---------------|
| **Discover** | Clear capability list with descriptions |
| **Validate** | Input schema + validation errors |
| **Execute** | Policy tells if safe (requires_approval, risk_level) |
| **Understand** | Structured execution envelope |
| **Recover** | Error codes + fix_hint + retryable flag |
| **Progress** | allowed_next_actions on every response |
| **Complete** | Workflow state in every response |

**No reasoning required. Just follow AICP.**

---

## See Also

- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model details
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and trust tier details
- [HITL.md](../overview/HITL.md) — Approval lifecycle
- [/ARCHITECTURE.md](../../ARCHITECTURE.md] — 11-plane system architecture