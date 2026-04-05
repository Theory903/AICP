# Product Requirements Document

> Mammoth + AICP — the Interaction OS and Execution OS that together form the Agentic Web Operating System.

---

## Product Names

| OS | Name | Role |
|----|------|------|
| **Interaction OS** | **Mammoth** | Every channel a human or agent uses to interact — terminal REPL, web console, CLI, Chrome extension |
| **Execution OS** | **AICP** | Every execution — policy evaluation, workflow orchestration, approval gating, audit, session management |

---

## Product Summary

Mammoth is the interaction layer for AICP. AICP is the execution backbone for Mammoth. Neither is complete alone.

- **Mammoth** provides four channels (terminal, web, CLI, extension) through which users and agents issue intent, observe execution, and supervise outcomes.
- **AICP** provides the governed execution substrate — protocol-native policy, stateful workflows, approval lifecycles, immutable audit, multi-agent coordination, and federation.

The combined stack covers 11 architectural planes: signal ingestion, perception, AI reasoning, capability management, workflow orchestration, governance, execution, multi-agent coordination, federation, supervision, and learning.

---

## Problem Statement

Modern AI agents interact with software through ad-hoc tool calling. This fails at scale:

| Problem | Impact |
|---------|--------|
| No governance layer | Agents execute high-risk actions without policy evaluation |
| No workflow state | Agents cannot resume multi-step processes after interruption |
| No approval semantics | No structured way to pause for human judgment |
| No audit trail | No immutable record of agent actions for compliance |
| No side-effect classification | Planners cannot reason about action consequences |
| No continuation guidance | Agents do not know what to do next after each action |
| No unified interaction layer | Every agent tool has a different surface — terminal, UI, API, all disconnected |
| No channel abstraction | Approval routing, rendering, and supervision are hardcoded per tool |

The result: agents can start tasks but cannot safely, reliably, or intelligently finish them — and operators have no unified surface to supervise them.

---

## Target Users

### Primary

| User | Need |
|------|------|
| Terminal power users | Conversational REPL with full AICP governance (Mammoth terminal channel) |
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
| Browser-centric users | Page-aware agent overlay via Mammoth Chrome extension |

---

## Product Stack

| Layer | Name | Purpose | Status |
|-------|------|---------|--------|
| **Interaction OS** | **Mammoth** | Terminal, web, CLI, and extension channels — unified interaction layer | Terminal working; web skeleton; extension planned |
| Protocol | AICP Protocol | JSON schemas: capability, workflow, policy, execution envelope | v0.3.0 (11 schemas) |
| Runtime | AICP Runtime | Execution engine, services, persistence, policy evaluation | v0.3.0 (8 services) |
| Connect | AICP Connect | Adapters importing existing systems as governed capabilities | v0.3.0 (6 adapters) |

> `apps/studio/` is superseded by the Mammoth Web channel. Mammoth Web is the supervision console.

---

## Mammoth Requirements

### Channel Requirements

| Channel | Requirement | Priority |
|---------|------------|---------|
| Terminal | Conversational REPL with streaming, syntax highlighting, tool call rendering | P0 |
| Terminal | Inline approval prompt for AICP-gated actions (--yes, --no-input flags) | P0 |
| Web | Axum HTTP server at configurable port | P0 |
| Web | Studio supervision console: approval queue, audit timeline, session list | P1 |
| Web | Conversational UI — WebSocket or SSE-backed chat interface | P1 |
| Web | Extension bridge endpoint (`GET /ext/events` SSE, `POST /ext/message`) | P1 |
| CLI | `mammoth serve [--port N]` — starts web channel | P0 |
| CLI | `mammoth ext` — starts extension bridge | P1 |
| Extension | Chrome MV3 manifest with `activeTab`, `storage`, `scripting` permissions | P1 |
| Extension | Background service worker connecting to Mammoth Web via SSE | P1 |
| Extension | Content script capturing page context (a11y tree, active element, URL) | P1 |
| Extension | Popup UI — minimal conversational overlay | P2 |

### Channel Abstraction

All channels must share a common `Channel` trait in `crates/runtime/src/channel.rs`:

```rust
pub trait Channel: Send + Sync {
    fn kind(&self) -> ChannelKind;
    fn render_text(&self, text: &str);
    fn render_tool_use(&self, name: &str, input: &serde_json::Value);
    fn render_tool_result(&self, name: &str, result: &str);
    fn prompt_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;
}
```

---

## AICP Requirements

### Functional Requirements

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

### Architecture: 11 Planes

| # | Plane | Purpose | v0.3.0 State |
|---|-------|---------|--------|
| 0 | Signal | Sub-ms event ingestion, dedup, classification, routing | Not started |
| 1 | Perception | a11y tree, DOM observation, screenshots, behavioral signals | Not started |
| 2 | AI | Planner, judge, intent router, memory, cognitive protocols | Complete (L4) |
| 3 | Capability | Registry, schema validation, ranked discovery, semantic search | Complete (L2) |
| 4 | Workflow | Sequential, parallel, fork/join, sagas, event-driven, subflows | Complete (L3) |
| 5 | Governance | Compiled policy engine, trust tiers, risk scoring, approval lifecycle | Complete (L2) |
| 6 | Execution | Realtime (<5ms), transactional (saga), event-driven (wait/resume) | Complete (L2) |
| 7 | Multi-Agent | Orchestrator/specialist/worker/supervisor hierarchy, communication bus | Not started |
| 8 | Federation | `/.well-known/aicp` discovery, CRDT registries, DID auth | Minimal |
| 9 | Supervision | Live feed, approval queue, replay debugger, policy editor | Partial |
| 10 | Learning | Skill mining, policy learning, drift detection, autonomy calibration | Not started |

---

## Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Schema validation success rate | >99.9% |
| Policy evaluation latency | <5ms (L2), <1ms (L5) |
| Workflow state persistence durability | Zero data loss on process restart |
| Audit trail immutability | Append-only, no edits, no deletes |
| Terminal channel startup time | <500ms |
| Web channel cold start | <2s |
| Adapter conformance | 100% schema compliance |
| Test coverage (core packages) | >80% |

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

**Current docs target: complete L3 orchestration plus shipped L4 AI planning components.**

---

## Non-Goals (Current)

| Non-Goal | Reason | Target |
|----------|--------|--------|
| Global identity system | OAuth/OIDC sufficient for now | v0.6.0 |
| Mammoth as LLM provider | AICP is not a provider — it is the execution layer between Mammoth and providers | Never |
| apps/studio/ maintenance | Superseded by Mammoth Web channel | Deprecated |
| Universal wallet/payments | Out of protocol scope | Never |

---

## Success Metrics

### Adoption

| Metric | Target |
|--------|--------|
| Mammoth channels operational | 4 (terminal, web, CLI, extension) |
| Working AICP adapters | 10+ (currently 6) |
| Reference applications | 5+ |
| Agent framework integrations | LangChain, LangGraph, CrewAI |

### Quality

| Metric | Target |
|--------|--------|
| Schema conformance test pass rate | 100% |
| Runtime test coverage | >80% |
| Approval round-trip time (terminal) | <2s |
| Approval round-trip time (web) | <5s |

---

## See Also

- [VISION.md](./VISION.md) — Mammoth + AICP dual OS vision
- [MAMMOTH.md](../guides/MAMMOTH.md) — Mammoth architecture (4 channels, channel trait, extension protocol)
- [/STATUS.md](../../STATUS.md) — Current implementation inventory
- [/ROADMAP.md](../../ROADMAP.md) — 10-phase roadmap to v1.0.0
- [ARCHITECTURE.md](../guides/ARCHITECTURE.md) — Full 11-plane architecture
