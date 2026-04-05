# Historical Milestone: v0.2.0

> Historical planning snapshot preserved for context. The repository has since moved on to the v1.0.0 feature set (Compliance Level 5).

---

## Current State: v1.0.0 Feature Set

AICP's current docs track the v1.0.0 feature set: complete L5 (Full Orchestration). See [STATUS.md](../../STATUS.md) for the complete inventory of what exists.

**Key metrics:**
- 16 JSON schemas in `/spec/schemas/`
- 8 runtime services (all complete)
- 30+ API endpoints across 13 route groups
- 698 passing core/runtime/cli tests
- 6 working adapters
- 28 CLI commands

---

## Original v0.2.0 Scope

v0.2.0 is the next real release target. It must prove that AICP can handle event-driven orchestration, richer workflow patterns, and the first AI reasoning layer.

### Must Ship

| Feature | Module | Rationale |
|---------|--------|-----------|
| YAML Workflow DSL | Workflow Engine (5) | JSON workflows are too verbose for real use |
| Parallel workflow steps | Workflow Engine (5) | Sequential-only is too limiting |
| Loop support (for-each, while) | Workflow Engine (5) | Cannot model real workflows without iteration |
| Wait-for-event primitive | Workflow Engine (5) | Cannot do async flows without event triggers |
| Timeout branching | Workflow Engine (5) | Events must have deadlines |
| AI Planner (basic) | AI Plane (8) | Core value prop -- agents that plan, not just execute |
| AI Judge (basic) | AI Plane (8) | Validate planner output before execution |
| Semantic capability discovery | Crawl/Map/Discovery (11) | Keyword scoring is not sufficient |
| Session encryption | Identity and Trust (2) | Plaintext session storage is not acceptable |
| LangChain adapter | Agent Adapters | Largest agent framework ecosystem |

### Should Ship

| Feature | Module | Rationale |
|---------|--------|-----------|
| AI Memory Builder | Memory System (9) | Enable cross-session learning |
| Dynamic workflow routing | Workflow Engine (5) | Conditional branching based on runtime data |
| Subflow invocation | Workflow Engine (5) | Workflows calling other workflows |
| Multi-dimensional risk scoring | Governance (12) | Currently policy is rule-based only |
| HTTP adapter | Protocol Adapters | For non-framework direct integration |
| Idempotency key enforcement | Execution Engine (13) | Retry safety |

### May Ship

| Feature | Module | Rationale |
|---------|--------|-----------|
| LangGraph adapter | Agent Adapters | Growing ecosystem |
| Threshold auto-approval | Human Cognitive Protocols (7) | Reduce approval fatigue |
| Live session view | Audit/Replay/Observability (18) | Developer experience |
| Food ordering reference flow | Domain Packs (20) | End-to-end demo |

---

## Exit Criteria

v0.2.0 is shippable when all of the following are true:

| Criterion | Verification |
|-----------|-------------|
| All "Must Ship" features implemented | Feature tests pass |
| YAML workflow DSL can express parallel + loop + event patterns | DSL conformance tests |
| AI Planner can decompose a 3-step goal into capability calls | Planner integration test |
| AI Judge can reject an invalid plan | Judge integration test |
| Semantic search returns relevant capabilities by description | Search relevance benchmark |
| Session data encrypted at rest | Encryption unit test |
| LangChain adapter exposes capabilities as LangChain tools | Adapter integration test |
| All existing 172+ tests still pass | `pytest` green |
| No regression in existing L2 compliance | Compliance level test suite |

---

## What v0.2.0 Must Demonstrate

### Demo 1: Event-Driven Food Ordering

Agent places order, waits for delivery event, auto-tracks. Demonstrates: wait-for-event, timeout branching, parallel steps (payment + notification).

### Demo 2: AI-Planned Payment Transfer

User says "send money to Rahul." AI Planner decomposes into capability calls. AI Judge validates the plan. Agent executes with approval checkpoint. Demonstrates: planner, judge, HITL, risk scoring.

### Demo 3: LangChain Integration

LangChain agent discovers AICP capabilities via semantic search, builds a tool list, executes a multi-step workflow with governance. Demonstrates: adapter, discovery, policy.

---

## What Is Explicitly Excluded from v0.2.0

| Feature | Reason | Target |
|---------|--------|--------|
| Multi-agent hierarchy | Requires stable planner/judge first | v0.5.0 |
| Federation (`/.well-known/aicp`) | Requires stable capability registry | v0.6.0 |
| Perception layer (a11y tree, screenshots) | Requires browser integration | v0.7.0 |
| Signal plane (sub-ms event ingestion) | Requires perception first | v0.7.0 |
| Learning plane (skill mining, drift detection) | Requires multi-agent + memory | v0.8.0 |
| Studio supervision console | Nice-to-have, not critical path | v0.4.0 |
| WASM policy modules | JSON policies sufficient for now | v0.6.0 |
| GraphQL/WebSocket adapters | HTTP + MCP sufficient for now | v0.5.0 |
| Cross-organization federation | Single-org first | v0.7.0 |

---

## Timeline Estimate

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 (2 weeks) | Workflow DSL + parallel + loops | Core orchestration |
| Phase 2 (2 weeks) | Wait-for-event + timeout + AI Planner stub | Event-driven + reasoning |
| Phase 3 (2 weeks) | AI Judge + semantic discovery + session encryption | Safety + search |
| Phase 4 (1 week) | LangChain adapter + demos + testing | Integration + polish |
| Phase 5 (1 week) | Documentation + compliance verification | Ship prep |

**Total: ~8 weeks from start of focused development.**

---

## Success Criteria

v0.2.0 is successful if:

1. A LangChain agent can discover, plan, and execute a 5-step governed workflow end-to-end.
2. The AI Planner produces valid capability call sequences that the Judge accepts.
3. Event-driven workflows can wait for external events with timeout fallback.
4. Session data is encrypted at rest.
5. All compliance level 2 tests continue to pass (no regression).
6. At least one new reference application demonstrates the full v0.2.0 feature set.

---

## See Also

- [/STATUS.md](../../STATUS.md) -- Current v0.3.0 feature-set implementation inventory
- [/ROADMAP.md](../../ROADMAP.md) -- Full 10-phase roadmap to v1.0.0
- [VISION.md](./VISION.md) -- Where this is all heading
- [USE_CASES.md](./USE_CASES.md) -- Scenarios that v0.2.0 must support
