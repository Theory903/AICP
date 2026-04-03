# Use Cases

> Where AICP stops being theory and becomes operational -- real-world scenarios across domain packs, multi-agent orchestration, and cognitive protocols.

---

## Overview

AICP is designed for tasks where AI must not only call an API but proceed through a sequence of governed actions while maintaining awareness of state, policy, failure, and human confirmation. Each use case demonstrates different planes of the architecture working together.

---

## Domain Packs

Domain packs are pre-built capability families with workflows, policies, and schemas tailored to specific industries. At v1.0.0, AICP targets four domain packs.

### Commerce Domain Pack

**Capabilities:** `restaurant.search`, `menu.browse`, `cart.create`, `cart.add`, `cart.update`, `cart.checkout`, `orders.place`, `orders.track`, `orders.cancel`, `delivery.estimate`, `payment.process`, `payment.confirm`

**Reference workflow: Food ordering**

```
User: "Order a paneer roll from my usual place and deliver it home."

Step 1: restaurant.search       -> Find "usual place" (query, deterministic lookup)
Step 2: menu.browse             -> Find paneer roll (query, bounded_nondeterministic)
Step 3: cart.create             -> Create cart (action, deterministic)
Step 4: cart.add                -> Add paneer roll (action, deterministic)
Step 5: delivery.estimate       -> Check delivery time (query, nondeterministic)
Step 6: payment.process         -> Process payment (action, high-risk, requires_approval)
   └── HITL checkpoint: Human confirms ₹180 payment
Step 7: orders.place            -> Place order (action, irreversible)
Step 8: orders.track            -> Track delivery (query, streaming)
```

**AICP value:** Workflow structure with approval at payment, compensation if payment fails after cart creation, `allowed_next_actions` guiding the agent through each step.

### Fintech Domain Pack

**Capabilities:** `account.balance`, `account.history`, `payment.transfer`, `payment.confirm`, `payment.refund`, `recipient.resolve`, `recipient.add`, `fx.rate`, `fx.convert`, `compliance.check`, `limit.check`

**Reference workflow: Payment transfer**

```
User: "Send ₹1000 to Rahul."

Step 1: recipient.resolve       -> Find Rahul (query, bounded_nondeterministic)
Step 2: account.balance         -> Check sufficient funds (query, deterministic)
Step 3: limit.check             -> Verify within transfer limits (query, deterministic)
Step 4: compliance.check        -> AML/KYC verification (query, deterministic)
Step 5: payment.transfer        -> Execute transfer (action, high-risk, requires_approval)
   └── HITL checkpoint: Human confirms ₹1000 to Rahul
   └── Risk score: {financial: 0.7, irreversibility: 0.9, privacy: 0.1}
Step 6: payment.confirm         -> Confirm completion (confirm, deterministic)
```

**AICP value:** Multi-dimensional risk scoring, mandatory approval for high-value transfers, compensation (reversal) if step 6 fails, full audit trail for compliance.

### Enterprise Domain Pack

**Capabilities:** `approval.route`, `approval.decide`, `invoice.lookup`, `invoice.process`, `report.generate`, `ticket.create`, `ticket.resolve`, `ticket.escalate`, `role.check`, `escalation.trigger`

**Reference workflow: Invoice approval**

```
Step 1: invoice.lookup          -> Retrieve invoice details (query)
Step 2: role.check              -> Verify approver authority (query)
Step 3: compliance.check        -> Policy evaluation against spend limits (query)
Step 4: approval.route          -> Route to correct approver (action)
   └── HITL checkpoint: Manager reviews invoice
Step 5: invoice.process         -> Process approved invoice (action)
Step 6: notification.send       -> Notify requester (notify)
```

**Reference workflow: Support ticket resolution**

```
Step 1: ticket.lookup           -> Retrieve ticket and customer context (query)
Step 2: account.history         -> Check recent orders and interactions (query)
Step 3: ticket.resolve          -> Apply resolution (action, may require_approval)
   └── If refund involved: HITL checkpoint
Step 4: notification.send       -> Notify customer (notify)
```

### Healthcare Domain Pack (v1.0.0 Target)

**Capabilities:** `patient.lookup`, `record.access`, `prescription.create`, `appointment.schedule`, `lab.order`, `consent.verify`, `audit.compliance`

**AICP value:** Mandatory consent verification before PII access, HIPAA-compliant audit trail, trust tier enforcement for record access.

---

## Multi-Agent Scenarios

AICP's Multi-Agent Plane (Plane 7) enables hierarchical agent coordination.

### Agent Hierarchy

| Role | Responsibility | Trust Tier |
|------|---------------|------------|
| Orchestrator | Decomposes goals into sub-tasks | 3-4 |
| Specialist | Handles domain-specific workflows | 2-3 |
| Worker | Executes individual capabilities | 1-2 |
| Supervisor | Monitors and intervenes | 4 |

### Scenario: Complex Travel Booking

```
Orchestrator receives: "Book a trip to Bangalore next Friday, hotel near office, 
                        return Sunday, budget under ₹15000"

Orchestrator decomposes:
  ├── Specialist (Flight): flight.search -> flight.select -> flight.book
  ├── Specialist (Hotel): hotel.search -> hotel.select -> hotel.reserve
  └── Specialist (Budget): budget.check -> budget.allocate

Communication Bus:
  - Flight Specialist -> Orchestrator: "Found flights ₹4500-₹8000"
  - Hotel Specialist -> Orchestrator: "Found hotels ₹2000-₹5000/night"
  - Budget Specialist -> Orchestrator: "₹15000 budget allows flight ₹5500 + hotel ₹3500/night"
  - Orchestrator -> Flight Specialist: "Book ₹5500 flight"
  - Orchestrator -> Hotel Specialist: "Book ₹3500/night hotel"

HITL checkpoint: Human confirms total ₹12500 booking
```

### Scenario: Automated Data Pipeline

```
Supervisor monitors pipeline execution:
  ├── Worker 1: data.extract (source A)
  ├── Worker 2: data.extract (source B)
  ├── Worker 3: data.transform (merge + clean)
  └── Worker 4: data.load (target warehouse)

Supervisor detects Worker 2 failure:
  -> Triggers compensation for Worker 3 (partial data)
  -> Retries Worker 2 with backoff
  -> Resumes pipeline on Worker 2 success
```

---

## Cognitive Protocols

Cognitive protocols define how AICP adapts its behavior to different operational domains. Each protocol configures trust thresholds, approval sensitivity, risk weighting, and rendering style.

| Protocol | Default Trust | Approval Sensitivity | Risk Weight Priority | Render Style |
|----------|--------------|---------------------|---------------------|-------------|
| UX | Tier 2 | Medium | `privacy > reputation > financial` | Rich (markdown, cards) |
| SWE | Tier 3 | Low | `availability > irreversibility > compliance` | Technical (JSON, logs) |
| Ops | Tier 2 | High | `availability > financial > irreversibility` | Dashboard (metrics, alerts) |
| Research | Tier 3 | Low | `privacy > compliance > financial` | Data (tables, charts) |
| Finance | Tier 1 | Very High | `financial > compliance > irreversibility` | Formal (receipts, confirmations) |

### Example: Finance Protocol

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

## Cross-Cutting Patterns

Every use case demonstrates these AICP patterns:

| Pattern | Description |
|---------|-------------|
| Workflow state tracking | Agent knows current step, completed steps, and remaining steps |
| Missing input detection | Agent knows what data is still needed before proceeding |
| Policy-gated execution | Risky actions require explicit policy evaluation |
| Structured approval | Not "confirm Y/N" but typed decisions with modification support |
| Compensation on failure | Completed steps can be rolled back when later steps fail |
| Continuation guidance | `allowed_next_actions` tells the agent what to do next |
| Render-aware output | Results include human-readable summaries with format hints |
| Determinism awareness | Planners know which actions are repeatable vs. side-effecting |
| Audit trail | Every action, decision, and state change is immutably recorded |

---

## v0.1.1 Implementation Status

| Use Case | Status | Notes |
|----------|--------|-------|
| Food ordering workflow | Example exists | `examples/fastapi-notes/` demonstrates the pattern |
| Payment transfer workflow | Example exists | `examples/payment-transfer/` |
| Enterprise approval | Partial | Approval lifecycle works, routing not implemented |
| Multi-agent scenarios | Not started | Planned for v0.5.0 |
| Cognitive protocols | Not started | Planned for v0.4.0 |
| Healthcare domain pack | Not started | Planned for v0.8.0 |

---

## See Also

- [ACTION_SURFACE.md](./ACTION_SURFACE.md) -- Capability model underlying all use cases
- [GOVERNANCE.md](./GOVERNANCE.md) -- Policy and risk scoring in action
- [HITL.md](./HITL.md) -- How approval checkpoints work in these flows
- [/MODULE_MAP.md](../../MODULE_MAP.md) -- Module 20: Domain Packs and Benchmarks
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- Multi-Agent Plane (Plane 7)
