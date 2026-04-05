# MODULE_MAP.md -- Feature-to-Module Mapping

> **Version Target:** 1.0.0 | **Last updated:** 2026-04-05

This document maps control-plane responsibilities to their owning modules. Use it to answer two practical questions:

1. Where does this behavior belong in AICP?
2. What supports Mammoth-first interaction and secure org automation?

Read this map with the current product framing in mind:

- **AICP** owns control-plane concerns: policy, workflow, execution, approvals, sessions, audit, discovery, trust, and org boundaries.
- **Mammoth** owns the primary interaction shell.
- **Studio** UX belongs inside Mammoth rather than as an independent front door.

---

## Module Index

| # | Module | Plane | Owner Package |
|---|--------|-------|---------------|
| 1 | Principal and Org Control | Governance | `packages/core` |
| 2 | Identity and Trust | Governance | `packages/runtime` |
| 3 | Capability Registry | Capability | `packages/core` + `packages/runtime` |
| 4 | Tool Runtime | Execution | `packages/runtime` |
| 5 | Workflow Engine | Workflow | `packages/runtime` |
| 6 | Perception and Signal Layer | Perception / Signal | `packages/core` |
| 7 | Human Cognitive Protocols | Supervision | `packages/runtime` + `packages/cli` |
| 8 | AI Plane | AI | `packages/runtime` |
| 9 | Memory System | AI | `packages/runtime` |
| 10 | Code Intelligence DB | AI | Not started |
| 11 | Crawl / Map / Discovery Engine | Capability | `packages/runtime` |
| 12 | Governance and Policy | Governance | `packages/core` + `packages/runtime` |
| 13 | Execution Engine | Execution | `packages/runtime` |
| 14 | Multi-Agent Hierarchy | Multi-Agent | `packages/core` |
| 15 | Agent Communication Bus | Multi-Agent | `packages/core` |
| 16 | Federation and Agentic WWW | Federation | `packages/core` |
| 17 | Human Web Compatibility | Perception | `packages/core` |
| 18 | Audit / Replay / Observability | Supervision | `packages/runtime` |
| 19 | Learning / Drift / Growth | Learning | `packages/core` |
| 20 | Domain Packs and Benchmarks | Learning | `packages/core` |

---

## 1. Principal and Org Control

**Plane:** Governance | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Identity hierarchy | Principal > org > team > agent tree | None | Full hierarchy with delegation |
| Org boundaries | Isolation between organizations | None | Multi-tenant enforcement |
| Delegation chains | Principal delegates authority to agents | None | Auditable delegation with revocation |
| Principal attribution | Every action traced to a principal | None | Full attribution in audit trail |

---

## 2. Identity and Trust

**Plane:** Governance | **Status:** Complete (L5) | **Phase:** 6 (v0.7.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Authentication | Agent/user identity verification | Session tokens, basic auth | DID-based auth |
| Trust tiers | 0-4 trust levels | Referenced but not enforced | Full tier enforcement |
| Session management | Resumable execution context | Working (session service) | Encrypted, cross-node |
| Credential verification | Validate agent credentials | Basic | Certificate chain validation |
| Trust decay | Trust degrades without re-verification | None | Configurable decay curves |

**Trust tier definitions:**

| Tier | Name | Default Policy Effect |
|------|------|-----------------------|
| 0 | Anonymous | Deny all side effects |
| 1 | Authenticated | Allow queries, ask for actions |
| 2 | Verified | Allow most actions, ask for risky |
| 3 | Trusted | Allow all except critical |
| 4 | Autonomous | Allow all (human override available) |

---

## 3. Capability Registry

**Plane:** Capability | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Registration | Register capabilities with schemas | Working | Same + versioning |
| 5 capability kinds | action, query, workflow, async_action, batch_action | Working | Same |
| Schema validation | Input/output JSON Schema enforcement | Working | Same + semantic coercion |
| Side-effect classification | Classify capability side effects | Working | Same |
| Dependency tracking | Capability dependency graph | None | Full graph with cycle detection |
| Versioning | Capability version management | None | SemVer with deprecation |
| Distributed registry | CRDT-based cross-node sync | None | CRDT with conflict resolution |

**Capability families (v1.0.0 target -- not implemented):**

| Family | Example Capabilities | Count |
|--------|---------------------|-------|
| Commerce | `cart.*`, `orders.*`, `payments.*`, `inventory.*` | ~15 |
| Identity | `auth.*`, `users.*`, `sessions.*` | ~10 |
| Content | `content.*`, `media.*`, `search.*` | ~10 |
| Communication | `email.*`, `notifications.*`, `messaging.*` | ~8 |
| Infrastructure | `deploy.*`, `monitoring.*`, `config.*` | ~10 |
| Finance | `accounts.*`, `transfers.*`, `reporting.*` | ~10 |

---

## 4. Tool Runtime

**Plane:** Execution | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Synchronous invocation | Execute and return | Working | Same |
| Result normalization | Canonical execution envelope | Working | Full envelope with all fields |
| Persistence | Store execution results | Working (3 backends) | Same |
| Timeout enforcement | Kill long-running executions | Basic | Configurable per capability |
| Sandboxing | Isolate capability execution | None | Process-level isolation |
| Resource locks | Prevent concurrent mutation | None | Distributed locks |

---

## 5. Workflow Engine

**Plane:** Workflow | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1), expanded Phase 2 (v0.3.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Sequential steps | Execute steps in order | Working | Same |
| Compensation | Rollback completed steps | Working (step-level) | Workflow-level + step-level |
| State persistence | Save workflow state | Working | Same |
| Resume after approval | Resume workflow after human approval | Working | Same |
| Parallel steps | Execute steps concurrently | None | Fork/join with configurable join |
| Loops | Repeat steps | None | for-each, while, repeat-until |
| Event-driven | Wait for external events | None | wait-for-event, timeout branching |
| Subflows | Invoke workflow from workflow | None | Full subflow with state isolation |
| YAML DSL | Human-readable workflow definitions | None | Compiled to JSON workflow objects |
| Saga patterns | Long-running distributed transactions | None | Full saga with compensation |

---

## 6. Perception and Signal Layer

**Plane:** Perception / Signal | **Status:** Protocol + Stub | **Phase:** 4 (v0.5.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| a11y tree extraction | Parse accessibility tree | Schema + Stub | Cross-framework (React, Vue, Angular) |
| DOM observation | Watch DOM changes | Schema + Stub | MutationObserver + virtual DOM diffing |
| Screenshot capture | Take and analyze screenshots | Schema + Stub | Screenshot-to-action pipeline |
| Behavioral signals | User intent, attention, interaction velocity | Schema + Stub | Cognitive signal processor |
| Event bus | Sub-ms event ingestion and routing | Schema + Stub | Stream ingestion (HTTP/2, WS, gRPC, SSE) |
| Signal classification | Classify events by intent/urgency/risk | Schema + Stub | ML classifier |
| Deduplication | Collapse duplicate signals | Schema + Stub | Content-hash dedup with bloom filters |

---

## 7. Human Cognitive Protocols

**Plane:** Supervision | **Status:** Partial | **Phase:** 0 (v0.1.1), expanded Phase 9 (v1.0.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Approval CLI | Approve/deny from command line | Working (`aicp appr`) | Same |
| Approval API | REST endpoints for approval lifecycle | Working | Same |
| Review packets | Impact analysis, blast radius estimation | Working | Enhanced with risk visualization |
| Intent matching | Find approval by intent | Working | Same + semantic matching |
| Supervision dashboard | Web UI for monitoring | Console (`/console`, 840 lines) | Full 5-view dashboard |
| Replay debugger | Step through execution history | None | Full replay with diff view |
| Policy editor | Edit policies from UI | None | Visual policy builder |

---

## 8. AI Plane

**Plane:** AI | **Status:** Complete (L4) | **Phase:** 1 (v0.2.0)

| Feature | Description | Current (v0.3.0) | v1.0.0 Target |
|---------|-------------|------------------|---------------|
| Intent router | Route natural language to capabilities | Working (`IntentRouter`) | Richer multimodal and org-aware routing |
| Planner | Generate multi-step plans from goals | Working (`AICPlanner`) | Constraint-satisfaction planner with broader domain packs |
| Executor | Run plans with rollback | Working | Speculative execution and parallel path optimization |
| Judge | Evaluate execution results | Working (`AICJudge`) | Success/failure/unsafe/ambiguous plus deeper policy-aware judgment |
| Context budget | Token-aware context management | Working (`MetaMemory`) | Larger-scale truncation, prioritization, and code-intelligence integration |
| Cognitive protocols | Domain-specific reasoning patterns | Working (UX, SWE, Ops, Research, Finance) | Expanded protocol library and stronger domain packs |

**Cognitive protocol families (v1.0.0 target):**

| Protocol | Purpose | Example Patterns |
|----------|---------|-----------------|
| UX | User experience operations | Form filling, navigation, preference inference |
| SWE | Software engineering | Code review, deployment, debugging |
| Ops | Operations | Monitoring, incident response, scaling |
| Research | Information gathering | Search, summarize, compare, synthesize |
| Finance | Transaction handling | Transfer validation, compliance checks, reconciliation |

---

## 9. Memory System

**Plane:** AI | **Status:** Complete (L4) | **Phase:** 1 (v0.2.0)

| Feature | Description | Current (v0.3.0) | v1.0.0 Target |
|---------|-------------|------------------|---------------|
| Working memory | Current session state | Working | Stronger token-bounded working memory and richer context assembly |
| Episodic memory | Execution history | Working | Cross-session retrieval and replay-aware summarization |
| Semantic memory | Facts and knowledge | Working structure, limited retrieval | Embedding-indexed knowledge store |
| Skill memory | Learned procedures | Working structure | Extracted execution patterns and adaptive strategy memory |
| Environmental memory | World state snapshots | Working structure | Perception-backed deployment and topology memory |

---

## 10. Code Intelligence DB

**Plane:** AI | **Status:** Not started | **Phase:** 7 (v0.8.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| AST indexing | Parse and index source code | None | Multi-language AST parser |
| Symbol graph | Function/class/variable relationships | None | Cross-file symbol resolution |
| Call-chain analysis | Trace execution paths | None | Static + dynamic analysis |
| Code-aware context | Build context from code structure | None | Token-budget-aware code snippets |

---

## 11. Crawl / Map / Discovery Engine

**Plane:** Capability | **Status:** Partial | **Phase:** 0 (v0.1.1), expanded Phase 9 (v1.0.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Keyword scoring | Rank capabilities by keyword match | Working | Same |
| Co-occurrence similarity | Similarity via keyword overlap | Working | Replaced by embeddings |
| Semantic retrieval | Embedding-based search | None | Vector search with re-ranking |
| Web crawler | Discover capabilities from websites | None | Respectful crawling with robots.txt |
| Capability graph | Build dependency/relationship graph | None | Full graph with traversal |
| Site scanner | Scan for AICP-compatible services | None | 800k+ service scanner |

---

## 12. Governance and Policy

**Plane:** Governance | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1), expanded Phase 8 (v0.9.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Policy effects | allow, deny, ask, limit | Working | Same |
| Condition matching | Match policies to capabilities | Working | Same + regex, glob patterns |
| Risk inference | Basic risk classification | Working | Full risk scoring formula |
| Policy evaluation | Evaluate policy per execution | Working | Same |
| Compiled policies | Policy compiled to native code | None | OPA/Cedar compiled to WASM |
| Trust tier enforcement | Policy varies by trust level | None | Full tier-based policy resolution |
| Anomaly detection | Detect unusual execution patterns | None | Statistical anomaly detection |
| Compliance layers | Industry/regulatory compliance | None | HIPAA, SOC2, GDPR policy templates |

**Risk scoring formula (v1.0.0 target):**

```
risk_score = {
  financial: <0.0-1.0>,       # monetary impact
  irreversibility: <0.0-1.0>, # can this be undone?
  privacy: <0.0-1.0>          # PII/sensitive data exposure
}
composite_risk = max(financial, irreversibility, privacy)
```

---

## 13. Execution Engine

**Plane:** Execution | **Status:** Complete (L2) | **Phase:** 0 (v0.1.1), expanded Phase 8 (v0.9.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Synchronous execution | Execute and wait | Working | Same |
| Result normalization | Canonical envelope | Working | Full envelope |
| Idempotency keys | Prevent duplicate execution | Schema field exists | Full idempotency engine |
| Three execution classes | Realtime, transactional, event-driven | Sync only | All three classes |
| Saga coordinator | Distributed transaction management | None | Full saga with compensation |
| Resource locks | Prevent concurrent mutation | None | Distributed locks |
| Failure recovery | Automatic retry with backoff | None | Configurable retry policies |

**Execution classes (v1.0.0 target):**

| Class | Latency | Use Case | Pattern |
|-------|---------|----------|---------|
| Realtime | <5ms | Queries, lookups, reads | Direct invocation |
| Transactional | <30s | Mutations, multi-step operations | Saga with compensation |
| Event-driven | Minutes to days | Approvals, external events | Wait/resume with timeout |

---

## 14. Multi-Agent Hierarchy

**Plane:** Multi-Agent | **Status:** Complete (L5) | **Phase:** 5 (v0.6.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Role definitions | Agent roles and responsibilities | None | Orchestrator, specialist, worker, supervisor |
| Task delegation | Assign work to agents | None | Protocol with capability matching |
| Result aggregation | Combine results from workers | None | Configurable aggregation strategies |
| Supervisor escalation | Escalate to human supervisor | None | Risk-based escalation |
| Conflict resolution | Handle resource contention | None | Priority-based resolution |

**Agent hierarchy (v1.0.0 target):**

| Tier | Role | Responsibility |
|------|------|---------------|
| 1 | Orchestrator | Plan decomposition, task assignment, result synthesis |
| 2 | Specialist | Domain-specific reasoning (e.g., finance, UX, SWE) |
| 3 | Worker | Execute individual capabilities |
| 4 | Supervisor | Monitor, intervene, override |

---

## 15. Agent Communication Bus

**Plane:** Multi-Agent | **Status:** Complete (L5) | **Phase:** 5 (v0.6.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Typed messages | Structured inter-agent messages | None | Message schema with validation |
| Pub/sub channels | Topic-based message routing | None | Channel management with ACLs |
| Coordination protocols | Consensus, leader election | None | Pluggable protocol library |
| Message persistence | Durable message store | None | At-least-once delivery |

---

## 16. Federation and Agentic WWW

**Plane:** Federation | **Status:** Protocol + Stub | **Phase:** 6 (v0.7.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Well-known endpoint | `/.well-known/aicp` | Working | Same + richer metadata |
| Cross-org discovery | Find capabilities across orgs | None | Push/pull discovery protocol |
| CRDT registries | Conflict-free registry sync | None | CRDT with merge semantics |
| DID authentication | Decentralized identity | None | DID resolution and verification |
| Capability routing | Route to best provider | None | Latency/cost/trust-aware routing |

---

## 17. Human Web Compatibility

**Plane:** Perception | **Status:** Protocol + Stub | **Phase:** 4 (v0.5.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Browser automation | Control browsers programmatically | None | Playwright/Puppeteer integration |
| Form filling | Fill web forms | None | Schema-to-form mapping |
| Navigation | Navigate multi-page flows | None | State-aware navigation |
| Legacy app support | Work with non-AICP apps | None | Fallback automation layer |

---

## 18. Audit / Replay / Observability

**Plane:** Supervision | **Status:** Complete (L5) | **Phase:** 0 (v0.1.1)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Append-only journal | Immutable audit log | Working | Same |
| Filtered listing | Query audit entries | Working | Same + full-text search |
| Correlation IDs | Link related entries | Working | Same + distributed tracing |
| Replay debugger | Step through past executions | None | Full replay with state diffing |
| Live feed | Real-time execution monitoring | None | Streaming with backpressure |
| Distributed tracing | Cross-service request tracing | None | OpenTelemetry integration |

---

## 19. Learning / Drift / Growth

**Plane:** Learning | **Status:** Protocol + Stub | **Phase:** 7 (v0.8.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| Skill mining | Extract reusable patterns | None | Pattern detection from execution logs |
| Policy learning | Suggest policy updates | None | Learn from approval patterns |
| Drift detection | Detect performance degradation | None | Statistical drift monitoring |
| Autonomy calibration | Adjust trust/autonomy over time | None | Performance-based tier adjustment |

---

## 20. Domain Packs and Benchmarks

**Plane:** Learning | **Status:** Protocol + Stub | **Phase:** 7 (v0.8.0)

| Feature | Description | v0.1.1 | v1.0.0 Target |
|---------|-------------|--------|---------------|
| E-commerce pack | Shopping, orders, payments, inventory | None | 15+ capabilities |
| Fintech pack | Accounts, transfers, compliance | None | 10+ capabilities |
| Healthcare pack | Records, appointments, prescriptions | None | 10+ capabilities |
| DevOps pack | Deployment, monitoring, config | None | 10+ capabilities |
| CRM pack | Contacts, deals, pipelines | None | 10+ capabilities |
| Evaluation suites | Benchmark tests per domain | None | Correctness, latency, governance |
| Regression testing | Detect capability degradation | None | Automated regression suite |

---

## Cross-Cutting Concerns

These features span multiple modules:

| Concern | Owning Modules | Description |
|---------|---------------|-------------|
| Execution envelope | 4, 13 | Canonical response format consumed by all planes |
| `allowed_next_actions` | 3, 8, 13 | Next action suggestions from registry, planner, and executor |
| Policy evaluation | 12, 13 | Policy checked before every side-effecting execution |
| Audit trail | 18, all | Every module produces audit entries |
| Session context | 2, 9 | Identity + memory combined in session |
| Schema validation | 3, all | Every protocol object validated against JSON Schema |

---

## File Locations

Quick reference for finding module implementations:

| Module | Spec | Core | Runtime | CLI |
|--------|------|------|---------|-----|
| Capability Registry | `spec/schemas/capability.schema.json` | `packages/core/src/aicp/capability/` | `packages/runtime/src/aicp_runtime/services/discovery.py` | `aicp scan`, `aicp preview` |
| Workflow Engine | `spec/schemas/workflow.schema.json` | `packages/core/src/aicp/workflow/` | `packages/runtime/src/aicp_runtime/services/workflow.py` | -- |
| Governance | `spec/schemas/policy.schema.json` | `packages/core/src/aicp/policy/` | `packages/runtime/src/aicp_runtime/services/execution.py` | `aicp policy` |
| Execution | `spec/schemas/execution-result.schema.json` | `packages/core/src/aicp/execution/` | `packages/runtime/src/aicp_runtime/services/execution.py` | `aicp run` |
| Approvals | `spec/schemas/approval-*.schema.json` | -- | `packages/runtime/src/aicp_runtime/services/approvals.py` | `aicp appr` |
| Audit | `spec/schemas/audit-entry.schema.json` | -- | `packages/runtime/src/aicp_runtime/services/audit.py` | -- |
| Discovery | `spec/schemas/discovery.schema.json` | -- | `packages/runtime/src/aicp_runtime/services/discovery.py` | `aicp scan` |
| Sessions | -- (gap) | -- | `packages/runtime/src/aicp_runtime/services/sessions.py` | -- |
