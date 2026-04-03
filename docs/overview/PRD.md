# Product Requirements Document

> AICP -- the Agentic Web Operating System. Protocol, runtime, memory, governance, perception, execution, and federation layer that turns the human web into an agent-operable web.

---

## Product Name

**AICP -- AI Capability Protocol (Agentic Web OS)**

## Product Summary

AICP is a protocol and runtime model that provides the complete operating system layer between AI agents and the applications they operate. It covers 11 architectural planes: signal ingestion, perception, AI reasoning, capability management, workflow orchestration, governance, execution, multi-agent coordination, federation, supervision, and learning.

It is designed for developers, platform teams, agent framework authors, and AI infrastructure builders who need governed, stateful, auditable agent-to-application interaction.

---

## Problem Statement

Modern AI agents interact with software through ad-hoc tool calling. This approach fails at scale because:

| Problem | Impact |
|---------|--------|
| No governance layer | Agents execute high-risk actions without policy evaluation |
| No workflow state | Agents cannot resume multi-step processes after interruption |
| No approval semantics | No structured way to pause for human judgment |
| No audit trail | No immutable record of agent actions for compliance |
| No side-effect classification | Planners cannot reason about action consequences |
| No continuation guidance | Agents do not know what to do next after each action |
| No determinism classification | Judges cannot verify if a plan is safe to retry |
| No federation | Agents cannot discover capabilities across organizations |
| No perception layer | Agents cannot observe the state of web applications |
| No multi-agent coordination | No hierarchy, communication bus, or task delegation |
| No learning loop | Agents do not improve from past executions |

The result: agents can start tasks but cannot safely, reliably, or intelligently finish them.

---

## Target Users

### Primary

| User | Need |
|------|------|
| AI infrastructure engineers | Protocol and runtime for governed agent execution |
| Backend/platform engineers | Expose existing APIs as governed capabilities |
| Agent framework authors | Governance substrate for LangChain, CrewAI, etc. |
| Product teams | Build assistants and copilots with safety guarantees |

### Secondary

| User | Need |
|------|------|
| Enterprise architects | Standardize AI execution across teams |
| Open-source contributors | Extend the protocol and runtime |
| Compliance teams | Audit trails and policy enforcement for AI actions |

---

## Product Stack

| Layer | Purpose | Status |
|-------|---------|--------|
| **Protocol** | JSON schemas defining capability, workflow, policy, execution envelope | v0.1.1 (9 schemas) |
| **Runtime** | Execution engine, services, persistence, policy evaluation | v0.1.1 (8 services) |
| **Connect** | Adapters importing existing systems as governed capabilities | v0.1.1 (6 adapters) |
| **Studio** | Supervision console: approvals, audit, workflow visualization | Minimal |

---

## Product Goals

### Goal 1: Make the web agent-operable

Every application action should be discoverable, typed, policy-governed, and auditable by agents.

### Goal 2: Governance as protocol, not middleware

Policy evaluation, trust tiers, risk scoring, and approval lifecycles are defined in the protocol schema, not bolted on by runtime configuration.

### Goal 3: Stateful, resumable execution

Every workflow is stateful. Execution persists across process restarts. Approval checkpoints pause and resume cleanly.

### Goal 4: Multi-agent coordination

Orchestrators decompose goals. Specialists handle domains. Workers execute capabilities. Supervisors monitor and intervene.

### Goal 5: Federation across organizations

Agents discover capabilities across organizational boundaries via `/.well-known/aicp` manifests.

### Goal 6: Perception and signal processing

Agents observe the state of web applications through a11y trees, DOM observation, screenshots, and behavioral signals.

### Goal 7: Learning and adaptation

The system mines execution patterns, detects capability drift, and calibrates agent autonomy over time.

---

## Architecture: 11 Planes

| # | Plane | Purpose | v0.1.1 |
|---|-------|---------|--------|
| 0 | Signal | Sub-ms event ingestion, dedup, classification, routing | Not started |
| 1 | Perception | a11y tree, DOM observation, screenshots, behavioral signals | Not started |
| 2 | AI | Planner, judge, intent router, memory, cognitive protocols | Not started |
| 3 | Capability | Registry, schema validation, ranked discovery, semantic search | Complete (L2) |
| 4 | Workflow | Sequential, parallel, fork/join, sagas, event-driven, subflows | Complete (L2) |
| 5 | Governance | Compiled policy engine, trust tiers, risk scoring, approval lifecycle | Complete (L2) |
| 6 | Execution | Realtime (<5ms), transactional (saga), event-driven (wait/resume) | Complete (L2) |
| 7 | Multi-Agent | Orchestrator/specialist/worker/supervisor hierarchy, communication bus | Not started |
| 8 | Federation | `/.well-known/aicp` discovery, CRDT registries, DID auth | Minimal |
| 9 | Supervision | Live feed, approval queue, replay debugger, policy editor | Partial |
| 10 | Learning | Skill mining, policy learning, drift detection, autonomy calibration | Not started |

---

## Functional Requirements

| # | Requirement | Compliance Level |
|---|------------|-----------------|
| 1 | Capability discovery with typed I/O schemas | L0 |
| 2 | Policy evaluation before every side-effecting execution | L1 |
| 3 | Structured approval lifecycle (approve/reject/modify/delegate/escalate) | L1 |
| 4 | Immutable audit trail for every execution | L1 |
| 5 | Stateful, resumable workflows with compensation | L2 |
| 6 | Session persistence across process restarts | L2 |
| 7 | `allowed_next_actions` on every execution envelope | L0 |
| 8 | Event-driven workflow primitives (wait-for-event, timeout) | L3 |
| 9 | AI Planner and Judge integration | L4 |
| 10 | Multi-agent hierarchy with communication bus | L5 |
| 11 | Cross-organization federation | L5 |
| 12 | Perception and signal processing | L5 |
| 13 | Learning and autonomy calibration | L5 |

---

## Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Schema validation success rate | >99.9% |
| Policy evaluation latency | <5ms (L2), <1ms (L5) |
| Workflow state persistence durability | Zero data loss on process restart |
| Audit trail immutability | Append-only, no edits, no deletes |
| Adapter conformance | 100% schema compliance |
| Test coverage (core packages) | >80% |
| Backward compatibility | Schema changes maintain backward compatibility within major version |

---

## Compliance Levels

| Level | Name | Requirements |
|-------|------|-------------|
| 0 | Capability Discovery | Capability registry, schema validation, basic execution |
| 1 | Governed Execution | L0 + policy evaluation, approval checkpoints, audit trail, session management |
| 2 | Resumable Workflows | L1 + sequential workflows, compensation, state persistence, resume after approval |
| 3 | Event-Driven Orchestration | L2 + wait-for-event, timeout branching, parallel steps, loops |
| 4 | AI Planning Support | L3 + planner, judge, context builder, allowed-next-actions schema |
| 5 | Full Orchestration | L4 + multi-agent coordination, subflows, cross-flow events, federation, supervision |

**Current implementation: Level 2.**

---

## Non-Goals (v0.1.1)

These are explicitly excluded from the current scope:

| Non-Goal | Reason | Target |
|----------|--------|--------|
| Global identity system | OAuth/OIDC integration sufficient for now | v0.6.0 |
| Universal wallet/payments | Out of protocol scope | Never |
| Complete UI framework | Studio is supervision console, not app framework | N/A |
| All transport protocols | HTTP + MCP sufficient for now | Incremental |

---

## Success Metrics

### Adoption

| Metric | Target |
|--------|--------|
| Working adapters | 10+ (currently 6) |
| Reference applications | 5+ (currently 2) |
| Agent framework integrations | LangChain, LangGraph, CrewAI |
| Community contributors | 10+ |

### Quality

| Metric | Target |
|--------|--------|
| Schema conformance test pass rate | 100% |
| Runtime test coverage | >80% |
| Multi-step workflow completion rate | >95% in reference demos |
| Approval round-trip time | <2s for CLI, <5s for API |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Scope creep beyond v0.2.0 | Strict exit criteria per phase |
| Over-abstraction (too academic to adopt) | Concrete reference apps, not just schemas |
| Confusion with MCP/OpenAPI/LangChain | Clear positioning docs, comparison table |
| Inconsistent adapter behavior | Schema conformance test suite |
| Poor first-use experience | `aicp dev` one-command demo |
| AI Planner producing invalid plans | Judge validation gate before execution |

---

## See Also

- [VISION.md](./VISION.md) -- Why the Agentic Web OS exists
- [MVP.md](./MVP.md) -- v0.2.0 milestone scope
- [/STATUS.md](../../STATUS.md) -- Current implementation inventory
- [/ROADMAP.md](../../ROADMAP.md) -- 10-phase roadmap to v1.0.0
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) -- 11-plane system architecture
