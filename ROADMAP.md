# AICP Roadmap

> **Version:** 0.3.0-dev | **Target:** 1.0.0
> **Last updated:** 2026-04-03

---

## Guiding Principles

1. **Spec before code.** Protocol changes are documented in `/spec` before runtime implementation.
2. **Layers, not chaos.** Each phase delivers a complete, testable capability layer.
3. **Compliance is cumulative.** Each compliance level subsumes all lower levels.
4. **Honest status.** No phase is marked complete without passing tests and working examples.
5. **Backward compatibility.** Breaking changes require a version bump and migration path.

---

## Version Map

| Phase | Version | Focus | Compliance Level | Status |
|-------|---------|-------|------------------|--------|
| 0 | **0.1.1-alpha** | Foundation | L2 (Resumable Workflows) | **Complete** |
| 1 | 0.2.0 | AI Core | L4 (AI Planning Support) | **Complete** |
| 2 | 0.3.0 | Orchestration | L3+L4 | **In Progress** |
| 3 | 0.4.0 | Agent Integration | L4 | Not started |
| 4 | 0.5.0 | Perception | L4 | Not started |
| 5 | 0.6.0 | Multi-Agent | L5 (Full Orchestration) | Not started |
| 6 | 0.7.0 | Federation | L5 | Not started |
| 7 | 0.8.0 | Learning | L5 | Not started |
| 8 | 0.9.0 | Production | L5 | Not started |
| 9 | **1.0.0** | Agentic Web OS | L5 | Not started |

**Note on compliance ordering:** L3 (Event-Driven Orchestration) ships in v0.3.0, but L4 (AI Planning Support) is reached in v0.2.0. The AI planning layer does not depend on event-driven workflow primitives. L5 requires all of L0-L4.

---

## Phase 0: Foundation (v0.1.1-alpha) -- COMPLETE

**Goal:** Prove that the protocol works end-to-end. Deliver a reference implementation covering capability discovery, governance, and resumable workflows.

### Delivered

- [x] 11 JSON schemas in `spec/schemas/` (including `session.schema.json` and `workflow-dsl.schema.json`)
- [x] Full fixture coverage for all 11 schemas (valid + invalid in `spec/tests/`)
- [x] 8 runtime services (execution, approvals, workflows, sessions, discovery, audit, interactions, provider health)
- [x] 30+ API endpoints across 13 route groups
- [x] 3 persistence backends (in-memory, file, SQLite)
- [x] 28 CLI commands with inline approval prompt
- [x] 6 working adapters (FastAPI, MCP, OpenAPI, cURL, HAR, Postman)
- [x] MCP server exposing AICP capabilities to MCP clients
- [x] 445 passing tests
- [x] Agent console UI at `/console` (840 lines HTML)
- [x] TypeScript Core SDK (built, distributable)
- [x] Approval auto-resume with intent matching
- [x] Dev server that mounts AICP routes on user apps

### Known Gaps

- No workflow-level `compensation_policy` -- compensation is step-level only
- No `often_follows` enforcement semantics
- No policy schema migration path (JSON to WASM)

See STATUS.md "Known Spec Gaps" for full details.

---

## Phase 1: AI Core (v0.2.0)

**Goal:** Give agents a brain. Deliver the planner, judge, memory system, and context builder that let an AI agent reason about multi-step operations, evaluate its own results, and carry context across sessions.

### Modules

| Module | Deliverables |
|--------|-------------|
| **AI Plane (#8)** | Intent router, multi-step planner with constraint satisfaction, executor with rollback, judge (success/failure/unsafe/ambiguous evaluation) |
| **Memory System (#9)** | Working memory, episodic store, semantic index, skill library, environmental memory; token-aware context budget manager |
| **Cognitive Protocols** | Five protocol families: UX (user experience), SWE (software engineering), Ops (operations), Research (information gathering), Finance (transaction handling) |

### Key Decisions

- **Planner architecture:** Constraint-satisfaction planner backed by LLM reasoning. The planner proposes a plan; the judge evaluates it; the executor runs it. All three are separate components.
- **Memory backend:** Pluggable interface. Default: SQLite for episodic/semantic, in-memory for working memory.
- **Candidate local model:** Gemma 4 31B for local planner/judge reasoning (tau2-bench 86.4%). E4B for edge worker agents.

### Exit Criteria

- [x] Planner can generate a multi-step plan from a natural language goal
- [x] Judge can evaluate plan quality and execution results
- [x] Memory system persists across sessions
- [x] Context budget manager stays within token limits
- [x] At least 2 cognitive protocols implemented (UX and SWE)
- [x] Compliance Level 4 conformance tests pass

---

## Phase 2: Orchestration (v0.3.0) -- IN PROGRESS

**Goal:** Upgrade the workflow engine from sequential-only to full orchestration: parallel steps, loops, event-driven wait/resume, subflows, and a YAML DSL for workflow authoring.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Workflow Engine (#5)** | Parallel steps, fork/join, loops, event-driven flows with wait-for-event and timeout branching, subflow invocation, saga patterns |
| **YAML Workflow DSL** | Human-readable workflow definitions compiled to AICP workflow objects |

### Exit Criteria

- [x] Parallel step execution with configurable join strategies (all, any, n-of-m)
- [x] Event-driven flows with wait-for-event and timeout
- [ ] Loop support (for-each, while, repeat-until)
- [x] YAML DSL can express all workflow patterns
- [ ] `compensation_policy` added at workflow level in spec
- [ ] Compliance Level 3 conformance tests pass

---

## Phase 3: Agent Integration (v0.4.0)

**Goal:** Let existing agent frameworks (LangChain, LangGraph, CrewAI) use AICP as their execution backend. Deliver the food ordering reference flow that demonstrates the full stack.

### Modules

| Module | Deliverables |
|--------|-------------|
| **LangChain Adapter** | AICP capabilities as LangChain tools, policy/approval integration |
| **LangGraph Adapter** | AICP workflows as LangGraph graphs, state persistence bridge |
| **CrewAI Adapter** | AICP capabilities as CrewAI tools |
| **Food Ordering Reference** | End-to-end example: menu browse, cart management, order placement, payment, tracking, cancellation with compensation |

### Exit Criteria

- [ ] LangChain agent can discover and execute AICP capabilities
- [ ] LangGraph agent can run AICP workflows with state persistence
- [ ] Food ordering example works end-to-end with approval gates
- [ ] Python SDK published (L2)
- [ ] TypeScript Runtime SDK published (L2)

---

## Phase 4: Perception (v0.5.0)

**Goal:** Give agents eyes and ears. Build the perception layer that extracts structured state from any application surface -- accessibility trees, DOM state, screenshots, behavioral signals.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Perception and Signal Layer (#6)** | a11y tree parser, DOM state extractor, screenshot analyzer, behavioral signal collector |
| **Human Web Compatibility (#17)** | Browser automation fallback, form filling, navigation, legacy app support |
| **Signal Plane** | Event bus, dedup engine, signal classifier, sub-ms routing |

### Exit Criteria

- [ ] a11y tree extraction works on 3+ web frameworks (React, Vue, Angular)
- [ ] Screenshot-to-action pipeline produces actionable elements
- [ ] Browser automation can fill forms and navigate multi-step flows
- [ ] Signal latency from ingestion to classification <5ms at p99

---

## Phase 5: Multi-Agent (v0.6.0)

**Goal:** Build the coordination layer for multiple agents working together. Deliver the 4-tier hierarchy (orchestrator, specialist, worker, supervisor) and communication bus.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Multi-Agent Hierarchy (#14)** | Role definitions, task delegation protocol, result aggregation, supervisor escalation |
| **Agent Communication Bus (#15)** | Typed message passing, pub/sub channels, coordination protocols, conflict resolution |

### Exit Criteria

- [ ] Orchestrator agent can delegate to 3+ specialist agents
- [ ] Worker agents report results through the communication bus
- [ ] Supervisor agent can intervene and override
- [ ] Conflict resolution protocol handles resource contention
- [ ] Compliance Level 5 conformance tests pass (first L5 phase)

---

## Phase 6: Federation (v0.7.0)

**Goal:** Connect AICP instances across organizational boundaries. Build the agentic WWW.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Federation and Agentic WWW (#16)** | `/.well-known/aicp` discovery protocol (already partial), CRDT-based registry sync, DID authentication, cross-org capability sharing |
| **Identity and Trust (#2)** | DID-based authentication (upgrade from session tokens), trust tiers 0-4, credential verification, trust decay |

### Exit Criteria

- [ ] Two AICP instances can discover each other's capabilities
- [ ] CRDT-based registry sync handles split-brain
- [ ] DID authentication works across organizations
- [ ] Trust tiers enforce capability access boundaries
- [ ] `often_follows` enforcement semantics defined in spec

---

## Phase 7: Learning (v0.8.0)

**Goal:** Make the system get smarter over time. Deliver skill mining, policy learning, drift detection, and domain packs.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Learning / Drift / Growth (#19)** | Skill extraction from execution history, policy refinement from approval patterns, performance drift detection, autonomy calibration |
| **Domain Packs and Benchmarks (#20)** | Pre-built capability sets (e-commerce, fintech, healthcare, devops, CRM, ERP), evaluation suites, regression testing |
| **Code Intelligence DB (#10)** | AST indexing, symbol graph, call-chain analysis, code-aware context building |

### Exit Criteria

- [ ] Skill mining extracts reusable patterns from execution logs
- [ ] Policy learning suggests policy updates from approval history
- [ ] At least 3 domain packs published with benchmarks
- [ ] Drift detection alerts on performance degradation

---

## Phase 8: Production (v0.9.0)

**Goal:** Harden everything for production deployment. Encrypted sessions, compiled WASM policies, risk scoring, multi-tenant isolation, and the remaining framework adapters.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Governance and Policy (#12)** | Compiled WASM policies (OPA/Cedar), risk scoring formula, anomaly detection, compliance layers |
| **Principal and Org Control (#1)** | Identity hierarchy, org boundaries, delegation chains, principal attribution |
| **Execution Engine (#13)** | Three execution classes (realtime <5ms, transactional/saga, event-driven/wait), idempotency engine, resource locks |
| **Framework Adapters** | Express, NestJS, Next.js, Spring Boot |
| **Protocol Adapters** | HTTP, GraphQL, WebSocket |
| **Encrypted Sessions** | At-rest encryption for session state, encrypted JSONL audit trail |

### Exit Criteria

- [ ] Policy migration path from JSON to WASM documented and tooled
- [ ] Risk scoring formula operational with financial/irreversibility/privacy dimensions
- [ ] Multi-tenant isolation enforced at session, capability, and data level
- [ ] Encrypted sessions pass security audit
- [ ] All framework adapters pass conformance tests

---

## Phase 9: Agentic Web OS (v1.0.0)

**Goal:** Complete the 11-plane architecture. Ship the stable protocol. The agentic web operating system is production-ready.

### Modules

| Module | Deliverables |
|--------|-------------|
| **Audit / Replay / Observability (#18)** | Full replay debugger, distributed tracing, live execution feed, streaming audit |
| **Human Cognitive Protocols (#7)** | 5-view supervision dashboard, risk visualization, replay debugger UI, policy editor UI |
| **Crawl / Map / Discovery Engine (#11)** | Semantic retrieval with embeddings, web crawler, capability graph construction, 800k+ service scanner |
| **AICP Studio** | Full supervision console -- the control tower for human operators |

### Exit Criteria

- [ ] All 20 modules implemented to specification
- [ ] All 11 planes operational
- [ ] Compliance Level 5 conformance tests pass
- [ ] 3+ domain packs with benchmarks
- [ ] Federation working across 2+ organizations
- [ ] Supervision console operational
- [ ] Protocol specification stable (no breaking changes without v2.0.0)
- [ ] Security audit passed

---

## Success Criteria (All Phases)

Each phase is considered successful when:

1. All exit criteria for the phase are met.
2. New spec schemas are added to `spec/schemas/` before runtime implementation.
3. Conformance tests pass at the target compliance level.
4. At least one working example demonstrates the new capabilities.
5. Documentation is updated across all affected docs.
6. No regressions in existing tests.

---

## Open Questions

These are architectural decisions that need resolution before or during the indicated phase:

| Question | Phase | Impact |
|----------|-------|--------|
| Should the planner be a single LLM call or a constraint-satisfaction loop? | 1 | Planner architecture, latency, cost |
| How should memory layers interact? Can episodic memory feed semantic indexing? | 1 | Memory system design |
| Should YAML DSL compile to JSON workflow objects or be a runtime format? | 2 | Tooling, debugging, portability |
| Should federation use pull-only or push/pull discovery? | 6 | Network topology, latency |
| Should WASM policies replace JSON policies or coexist indefinitely? | 8 | Migration complexity |
| What is the governance model for domain packs? Who publishes? Who reviews? | 7 | Community, quality |

---

## Contributing to Roadmap Items

See [governance/CONTRIBUTING.md](governance/CONTRIBUTING.md) for the full process. To work on a roadmap item:

1. Check the phase status in STATUS.md.
2. Find the module in the 20-Module Status Matrix.
3. If the module has no spec schema yet, start with the spec (RFC if needed).
4. If the module has a spec, start with conformance tests.
5. Then implement against the tests.

Roadmap changes require an RFC in `rfcs/`.
