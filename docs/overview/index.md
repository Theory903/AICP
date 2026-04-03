# AICP Documentation

> The Agentic Web Operating System -- protocol, runtime, memory, governance, perception, execution, and federation layer that turns the human web into an agent-operable web.

---

## Getting Started

| Guide | Description |
|-------|-------------|
| [Vision](./overview/VISION.md) | Why the Agentic Web OS exists |
| [Action Surface](./overview/ACTION_SURFACE.md) | The agent-facing surface of software |
| [Architecture](../ARCHITECTURE.md) | 11-plane system architecture |
| [Quick Start](./guides/index.md) | Installation and first steps |
| [How-To Guide](./guides/HOW_TO_USE.md) | Complete usage reference |
| [Platform Demo](./examples/PLATFORM_DEMO.md) | End-to-end walkthrough |

---

## Architecture: 11 Planes

```
┌─────────────────────────────────────────────────────────────┐
│  Plane 10: Learning    │ Skill mining, drift, calibration   │
│  Plane 9:  Supervision │ Live feed, approval queue, replay  │
│  Plane 8:  Federation  │ /.well-known/aicp, CRDT, DID auth  │
│  Plane 7:  Multi-Agent │ Orchestrator, specialist, worker   │
│  Plane 6:  Execution   │ Realtime, transactional, event     │
│  Plane 5:  Governance  │ Policy, trust tiers, risk scoring  │
│  Plane 4:  Workflow    │ Sequential, parallel, sagas        │
│  Plane 3:  Capability  │ Registry, discovery, search        │
│  Plane 2:  AI          │ Planner, judge, memory             │
│  Plane 1:  Perception  │ a11y tree, DOM, screenshots        │
│  Plane 0:  Signal      │ Event ingestion, dedup, routing    │
└─────────────────────────────────────────────────────────────┘
```

---

## Product Stack

| Layer | Purpose | Documentation |
|-------|---------|--------------|
| **Protocol** | JSON schemas defining the agent-application contract | [Spec](./spec/index.md) |
| **Runtime** | Execution engine, services, persistence | [Architecture Guide](./guides/ARCHITECTURE.md) |
| **Connect** | Adapters importing existing systems as governed capabilities | [How-To Guide](./guides/HOW_TO_USE.md) |
| **Studio** | Supervision console: approvals, audit, workflows | [Runtime/Studio Guide](./guides/RUN_RUNTIME_STUDIO.md) |

---

## Overview Documents

| Document | Description |
|----------|-------------|
| [Vision](./overview/VISION.md) | The Agentic Web OS vision and design principles |
| [Action Surface](./overview/ACTION_SURFACE.md) | Capability model, execution envelope, capability families |
| [Governance](./overview/GOVERNANCE.md) | Policy, trust tiers, risk scoring, approval lifecycle |
| [HITL](./overview/HITL.md) | Human-in-the-loop approval model |
| [Comparison](./overview/COMPARISON.md) | AICP vs OpenAPI, MCP, LangChain, CrewAI |
| [Use Cases](./overview/USE_CASES.md) | Domain packs, multi-agent scenarios, cognitive protocols |
| [PRD](./overview/PRD.md) | Full product requirements document |
| [Next Milestone](./overview/MVP.md) | v0.2.0 scope and exit criteria |

---

## Guides

| Guide | Description |
|-------|-------------|
| [Architecture](./guides/ARCHITECTURE.md) | Technical architecture for contributors |
| [How to Use AICP](./guides/HOW_TO_USE.md) | Complete usage reference |
| [CLI Reference](./guides/CLI_REFERENCE.md) | 28 CLI commands |
| [Runtime and Studio](./guides/RUN_RUNTIME_STUDIO.md) | Running the runtime and Studio |
| [Technical Specification](./guides/TECH_SPEC.md) | Protocol technical specification |

---

## Handbook

| Document | Description |
|----------|-------------|
| [Agentic Experience](./handbook/AGENTIC_EXPERIENCE.md) | Cognitive protocols, perception model, 11-plane awareness |

---

## Protocol Specification

| Document | Description |
|----------|-------------|
| [Protocol Schemas](./spec/index.md) | All 9 JSON schemas with examples |
| [AICP TOON](./spec/AICP_TOON.md) | Protocol specification prose |

---

## Reference

| Document | Description |
|----------|-------------|
| [API Reference](./reference/index.md) | 30+ endpoints across 13 route groups |
| [Examples](./examples/index.md) | Reference applications |
| [Platform Demo](./examples/PLATFORM_DEMO.md) | End-to-end demo walkthrough |

---

## Project State

| Document | Description |
|----------|-------------|
| [Status](../STATUS.md) | Current v0.1.1-alpha implementation inventory |
| [Roadmap](../ROADMAP.md) | 10-phase roadmap to v1.0.0 |
| [Module Map](../MODULE_MAP.md) | Feature-to-module mapping for all 20 modules |
| [Contributing](../governance/CONTRIBUTING.md) | How to contribute |

---

## Core Concepts

### Capabilities

The atomic unit of the Action Surface. A governed action with typed I/O, side-effect classification, risk metadata, and error codes.

```python
Capability(
    name="payments.transfer",
    kind=CapabilityKind.ACTION,
    input_schema={"type": "object", "properties": {"amount": {"type": "number"}}},
    requires_approval=True,
    risk_level="high",
)
```

### Policies

Rules defining what is allowed, denied, or requires approval. Evaluated before every side-effecting execution.

```python
Policy(
    name="high_value_transfers",
    effect=PolicyEffect.REQUIRE_APPROVAL,
    conditions={"amount_gt": 10000},
)
```

### Workflows

Multi-step stateful processes with branching, retries, approval checkpoints, and compensation.

```python
Workflow(
    name="payment_flow",
    steps=[resolve_recipient, check_balance, transfer, confirm],
    on_failure="compensate",
)
```

### Execution Envelope

The canonical response from every capability execution. All planes consume it.

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "orders.place",
  "status": "success",
  "policy_result": { "effect": "allow", "trust_tier": 2 },
  "allowed_next_actions": [{ "name": "order.track", "confidence": 0.95 }],
  "rendered": "Order placed. Delivery at 7:30 PM."
}
```

---

*Built for agents. Governed by design. v0.1.1-alpha.*
