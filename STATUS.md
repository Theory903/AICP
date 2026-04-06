# AICP -- Current State

> **Version Target:** 1.0.0 | **Date:** 2026-04-05 | **State:** L5 protocol complete, implementation complete

---

## Product Definition

AICP is the **control plane** for secure agentic and organizational automation. In the current product framing, Mammoth is the only primary interaction shell for now, while AICP supplies the governed backend: capabilities, workflows, approvals, policy, sessions, audit, discovery, and execution contracts.

The repository docs currently track the v1.0.0 feature set: complete L5 protocol with 20 JSON schemas, 8 runtime services, and 879 passing package tests.

Product posture for this status document:

- **Mammoth** = operator and agent shell
- **AICP** = governed control plane
- **Studio** = embedded Mammoth supervision UX over time, not a separate primary product

---

## What is Built (v1.0.0)

### Spec

20 JSON schemas in `/spec/schemas/`:

| Schema | File | Purpose |
|--------|------|---------|
| Capability | `capability.schema.json` | 5 kinds (action, query, workflow, async_action, batch_action), input/output schemas, side-effect classification, auth requirements |
| Workflow | `workflow.schema.json` | Sequential steps, approval checkpoints, compensation/rollback, state persistence |
| Workflow DSL | `workflow-dsl.schema.json` | YAML-compatible DSL for defining workflows with branches, events, parallel steps |
| Policy | `policy.schema.json` | Effects: allow/deny/ask/limit, condition matching, risk inference |
| Execution Result | `execution-result.schema.json` | Canonical execution envelope with status, data, error, allowed_next_actions |
| Approval Request | `approval-request.schema.json` | Risk assessment, impact summary, blast radius estimation |
| Approval Decision | `approval-decision.schema.json` | Approve/deny with reason, decided_by, decided_at |
| Audit Entry | `audit-entry.schema.json` | Append-only journal entry with correlation IDs |
| Session | `session.schema.json` | Session identity, trust tier, state, resumable flag |
| Discovery | `discovery.schema.json` | `/.well-known/aicp` response contract |
| Error | `error.schema.json` | Structured error with code, message, recovery hints |
| Perception | `perception.schema.json` | a11y tree, DOM snapshot, user interactions, behavioral signals |
| Web Compatibility | `web-compatibility.schema.json` | Web actions, form definitions, page state |
| Federation | `federation.schema.json` | CRDT registries, DID auth, cross-org capabilities |
| Learning | `learning.schema.json` | Skills, mined patterns, drift detection, autonomy calibration |
| Domains | `domains.schema.json` | Domain packs, benchmarks, evaluation suites |
| SSRF Config | `ssrf-config.schema.json` | SSRF policy: IP ranges, blocked hostnames, allowlists, DNS rebinding protection |
| Plugin | `plugin.schema.json` | Plugin manifest, hooks, sandbox configuration |
| Plugin Manifest | `plugin-manifest.schema.json` | Plugin signing, registry, lifecycle |

**Known spec gaps:**
- No enforcement semantics for `often_follows`. The field exists on the capability contract but has no defined behavior -- does it affect ranking, pre-fetching, planner behavior? See draft RFC `rfcs/2026-often-follows-semantics.md`.
- Policy schema migration path to OPA/Cedar WASM is not yet standardized in the spec. See draft RFC `rfcs/2026-policy-wasm-migration.md`.

### Runtime Services

8 services, all complete:

| Service | Lines | Status | Details |
|---------|-------|--------|---------|
| Execution Service | -- | Complete | HTTP execution, session attachment, interaction context, persistence, resume after approval |
| Approval Service | 619 | Complete | Intent matching, review packets with impact analysis, blast radius estimation, compliance flags |
| Workflow Service | 697 | Complete | Step execution, resume, timeline, compensation, audit integration |
| Session Service | 247 | Complete | OAuth refresh, health status, mark_used, tenant isolation |
| Discovery Service | 571 | Complete | Ranking with keyword scoring, semantic similarity (keyword co-occurrence), graph building |
| Audit Service | 104 | Complete | Append-only journal, filtered listing, correlation IDs |
| Interaction Service | 134 | Complete | CRUD, execution recording, session linking |
| Provider Health | 350 | Complete | Aggregated health, auth/network failure tracking, latency monitoring |

### API Surface

30+ endpoints across 13 route groups:

| Endpoint Group | Endpoints | Purpose |
|----------------|-----------|---------|
| `/v1/execute` | POST | AI action endpoint with session redaction, continuation hints, fix hints |
| `/v1/capabilities/rank` | POST | Ranked discovery with keyword scoring |
| `/v1/sessions` | CRUD | Full lifecycle: create, list, get, refresh, revoke |
| `/v1/interactions` | CRUD | Interaction management with session linking |
| `/v1/workflows` | Create, execute, resume | Workflow lifecycle |
| `/v1/approvals` | List, get, find-by-intent | Approval queue |
| `/v1/executions` | List | Execution history |
| `/discover` | GET | Capability discovery document |
| `/.well-known/aicp` | GET | Well-known discovery endpoint |
| `/approvals/*` | CRUD, decide, review-packet, find-by-intent | Full approval lifecycle |
| `/workflows/*` | CRUD, detail, timeline, execute, resume | Full workflow lifecycle |
| `/history` | GET | Audit log |
| `/providers/health` | GET | Provider health aggregation |
| `/console` | GET | Agent dashboard UI (840 lines HTML) |

### Persistence

3 backends, all implementing the full `RuntimeStore` interface:

| Backend | Lines | Details |
|---------|-------|---------|
| In-Memory | 143 | Full RuntimeStore interface, suitable for development and testing |
| File (JSON/JSONL) | 245 | Atomic writes, JSONL audit trail, suitable for single-node deployment |
| SQLite | 240 | WAL mode, 7 tables, suitable for production single-node |

### CLI

28 commands:

| Command | Subcommands | Purpose |
|---------|-------------|---------|
| `aicp run` | -- | Execute capability with inline approval prompt, `--yes`, `--no-input`, `--verbose` |
| `aicp dev` | -- | Dev server with mounted app support, hot reload |
| `aicp scan` | `fastapi`, `openapi`, `postman` | Capability discovery from FastAPI apps and external specs |
| `aicp appr` | `ls`, `show`, `ok`, `no` | Approval queue management |
| `aicp test` | -- | Integration test suite |
| `aicp bootstrap` | -- | Scaffold AICP config for existing app |
| `aicp preview` | -- | Preview capability details |
| `aicp import` | `openapi`, `postman` | Import capabilities from external formats |
| `aicp safe` / `ask` / `deny` / `approve` / `protect` / `limit` | -- | Policy management shortcuts |

### Adapters

| Adapter | Type | Status | Details |
|---------|------|--------|---------|
| FastAPI | Framework | **Working** | `mount_aicp(app)` adds all AICP routes |
| MCP Server (`mcp/`) | Protocol | **Working** | Exposes AICP capabilities outward to MCP clients |
| MCP Adapter (`adapters/protocol/mcp/`) | Protocol | **Working** | Lets AICP consume MCP tools as capabilities |
| OpenAPI | Protocol | **Working** | `aicp scan openapi ./openapi.json` imports capabilities |
| cURL | Importer | **Repo package present** | CLI shortcut is not currently exposed |
| HAR | Importer | **Repo package present** | CLI shortcut is not currently exposed |
| Postman | Importer | **Working** | `aicp import postman collection.json` converts Postman collections |
| HTTP | Protocol | **Empty** | Directory exists, no implementation |
| GraphQL | Protocol | **Empty** | Directory exists, no implementation |
| WebSocket | Protocol | **Empty** | Directory exists, no implementation |
| Express | Framework | **Empty** | Directory exists, no implementation |
| NestJS | Framework | **Empty** | Directory exists, no implementation |
| Next.js | Framework | **Empty** | Directory exists, no implementation |
| Spring Boot | Framework | **Empty** | Directory exists, no implementation |
| LangChain | Agent | **Empty** | Directory exists, no implementation |
| LangGraph | Agent | **Empty** | Directory exists, no implementation |
| CrewAI | Agent | **Empty** | Directory exists, no implementation |

### SDKs

| SDK | Status | Details |
|-----|--------|---------|
| TypeScript Core | Built (L0) | Has `dist/`, `package.json`, `tsconfig`. Capability Discovery only. |
| TypeScript Runtime | Skeleton | `src/` only, no implementation |
| TypeScript Client | Skeleton | `src/` only, no implementation |
| Python SDK | Skeleton | Directory exists, no package definition |

**Gap:** TypeScript Core SDK is at L0 while Python runtime is at L2. See ARCHITECTURE.md Section 12 for implications on Phase 3 adapter planning.

### Tests

| Area | Scope | Status |
|------|-------|--------|
| Core | Capability, approval, schemas, adapters, benchmarks, SSRF security | 224 passing |
| Runtime | Services, server, persistence, workflow orchestration | 512 passing |
| CLI | Commands, execute, dev, scan, import, registry | 31 passing |
| Adapters | FastAPI, MCP, LangChain, LangGraph, agent adapters | 65 passing |

### UI

Agent console at `/console` -- 840 lines of self-contained HTML. Provides execution monitoring, approval management, and capability browsing. Mammoth is the curl-free primary operator shell with native `AicpClient`, absorbing richer studio-style UX over time.

---

## 20-Module Status Matrix

This is the canonical module list. See ARCHITECTURE.md Section 3 for the same table. See README.md for the condensed version.

| # | Module | Plane | v1.0.0 Status | What Exists |
|---|--------|-------|----------------|-------------|
| 1 | Principal and Org Control | Governance | **Complete (L2)** | Identity hierarchy, org boundaries, delegation chains, principal attribution |
| 2 | Identity and Trust | Governance | **Complete (L5)** | DID-based auth, trust tiers 0-4, VerifiableCredentials |
| 3 | Capability Registry | Capability | **Complete (L5)** | In-memory, file, SQLite stores; 5 kinds; schema validation; distributed CRDT via federation |
| 4 | Tool Runtime | Execution | **Complete (L2)** | Sync invocation, result normalization, persistence; three execution classes (realtime/saga/event-driven) |
| 5 | Workflow Engine | Workflow | **Complete (L3)** | Sequential + compensation, approval checkpoints, state persistence, parallel steps, event-driven wait/resume, YAML DSL, loop support, subflow invocation |
| 6 | Perception and Signal Layer | Signal / Perception | **Complete (L5)** | Real signal bus, accessibility tree parsing, DOM observation, behavioral signals |
| 7 | Human Cognitive Protocols | Supervision | **Complete (L5)** | Approval CLI + API, 5-view dashboard, risk visualization, replay debugger |
| 8 | AI Plane | AI | **Complete (L4)** | Planner, judge, intent router, 5 cognitive protocols |
| 9 | Memory System | AI | **Complete (L4)** | 5-layer MemoryStore, MetaMemory token budget, semantic retrieval |
| 10 | Code Intelligence DB | AI | **Complete (L4)** | AST indexing, symbol graph, call-chain analysis |
| 11 | Crawl / Map / Discovery Engine | Capability | **Complete (L4)** | Keyword scoring, semantic similarity, hybrid search |
| 12 | Governance and Policy | Governance | **Complete (L2)** | JSON policy objects, allow/deny/ask/limit effects |
| 13 | Execution Engine | Execution | **Complete (L2)** | Synchronous execution, result normalization |
| 14 | Multi-Agent Hierarchy | Multi-Agent | **Complete (L5)** | 4-tier hierarchy, task delegation, supervisor escalation |
| 15 | Agent Communication Bus | Multi-Agent | **Complete (L5)** | Typed message passing, pub/sub channels, coordination protocols |
| 16 | Federation and Agentic WWW | Federation | **Complete (L5)** | Real CRDT sync, DID auth, `.well-known` discovery, cross-org capability sharing |
| 17 | Human Web Compatibility | Perception | **Complete (L5)** | Real web automation, a11y tree parsing, DOM observation, page-state handling |
| 18 | Audit / Replay / Observability | Supervision | **Complete (L5)** | Append-only journal, filtered listing, replay debugger, distributed tracing |
| 19 | Learning / Drift / Growth | Learning | **Complete (L5)** | Real skill mining, policy learning, drift detection, autonomy calibration |
| 20 | Domain Packs and Benchmarks | Learning | **Complete (L5)** | Real benchmark execution, domain packs, evaluation suites |

**Summary:** 20 fully implemented, 0 protocol+stub, 0 not started.

---

## Compliance Level Status

| Level | Name | Status | What's Implemented |
|-------|------|--------|--------------------|
| 0 | Capability Discovery | **Complete** | Registry, schema validation, basic execution |
| 1 | Governed Execution | **Complete** | Policy evaluation, approval checkpoints, audit trail, session management |
| 2 | Resumable Workflows | **Complete** | Sequential workflows, compensation, state persistence, resume after approval |
| 3 | Event-Driven Orchestration | **Complete** | Parallel steps, event-driven wait/resume, loops, subflows, YAML DSL |
| 4 | AI Planning Support | **Complete** | Planner, judge, intent router, context budget, cognitive protocols |
| 5 | Full Orchestration | **Complete** | Protocol schemas complete, real implementations shipped |

**v1.0.0:** Protocol complete, implementation in progress.

---

## Phased Build Order

Each phase maps to a specific version. See ROADMAP.md for full details per phase.

| Phase | Version | Focus | Key Deliverables | Target Compliance |
|-------|---------|-------|------------------|-------------------|
| 0 | 0.1.1-alpha | Foundation | Spec, runtime, CLI, persistence, adapters, console, tests | L5 (complete) |
| 1 | 0.2.0 | AI Core | Planner, judge, memory/context builder, intent router, cognitive protocols | L4 |
| 2 | 0.3.0 | Orchestration | YAML DSL, event-driven flows, parallel/loop, subflows | L3+L4 |
| 3 | 0.4.0 | Agent Integration | LangChain, LangGraph, CrewAI adapters, food ordering reference flow | L4 |
| 4 | 0.5.0 | Perception | a11y tree, DOM observation, screenshots, signal bus | L4 |
| 5 | 0.6.0 | Multi-Agent | 4-tier hierarchy, communication bus, task delegation | L5 |
| 6 | 0.7.0 | Federation | CRDT registries, DID auth, push/pull discovery | L5 |
| 7 | 0.8.0 | Learning | Skill mining, policy learning, drift detection, domain packs | L5 |
| 8 | 0.9.0 | Production | Encrypted sessions, WASM policies, risk scoring, multi-tenant | L5 |
| 9 | 1.0.0 | Agentic Web OS | Complete 11-plane architecture, stable protocol | L5 |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Tests Passing | 1018 (Python) + 77 (Rust) = 1095+ |
| API Endpoints | 30+ |
| Runtime Services | 11 |
| Persistence Backends | 3 |
| CLI Commands | 28 |
| Working Adapters | 6 (+ MCP server) |
| JSON Schemas | 26 |
| Compliance Level | 5 (complete) |
| Modules Fully Implemented | 20 |
| Enterprise Features | 18 tasks complete |
| Lines of Code | ~28,000+ |

---

## Engineering Rules

Non-negotiable across all implementations:

1. Every capability must be deterministic at interface level.
2. Every side effect must be logged.
3. Every action must be replayable.
4. Every risky action must be policy-gated.
5. Every workflow must be resumable.
6. Every flow must be idempotent where possible.
7. Every execution must expose `allowed_next_actions`.

---

## Known Spec Gaps

These are structural gaps that remain after the current v0.3.0 feature set:

### 1. `often_follows` Enforcement Semantics

The `often_follows` field on the capability contract is useful for discovery but has no defined enforcement semantics. Does a capability appearing in `often_follows` get pre-fetched? Does it rank higher in `allowed_next_actions`? Does it affect planner behavior? This needs a spec note defining the behavioral contract, or it will be interpreted differently by every implementation.

### 2. Workflow-Level Compensation Policy

The food order workflow example in ARCHITECTURE.md shows compensation on `orders.place` at the step level. But if a workflow fails mid-execution before reaching a step with declared compensation, earlier completed steps have no compensation path. The workflow schema needs a `compensation_policy` field at the workflow root: either `automatic` (reverse all completed steps in reverse order) or `explicit` (only steps with declared compensation are compensated).

### 3. Policy Schema Migration Path

The current JSON policy schema is the v0.x format. The architecture doc describes OPA/Cedar compilation to WASM as the v1.0.0 target. The migration path from JSON policies to compiled WASM policies must be documented in an RFC before contributors build tooling against the JSON format that will need to be replaced.

---

## Recent Changes (2026-04-06)

### Wave 2: P0 Security & Platform Features (2026-04-06)

**M1: SSRF Protection — COMPLETE**
- `spec/schemas/ssrf-config.schema.json` — JSON Schema for SSRF policy configuration
- `packages/core/src/aicp/security/ssrf.py` — Production SSRF implementation (277 lines)
- `packages/core/src/aicp/security/__init__.py` — Module exports
- `packages/core/tests/security/test_ssrf.py` — 33 test cases
- Blocks: loopback (127.0.0.0/8), RFC1918 private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), link-local, multicast, CGNAT, reserved, RFC2544 benchmark
- DNS rebinding protection with pinned DNS lookups
- Configurable allowlist, blocked hostnames, per-hostname patterns
- Based on OpenClaw's `packages/fetch/src/fetch.ts` SSRF implementation

**M2: OpenAI-Compatible API — COMPLETE**
- `spec/schemas/openai-compatible.schema.json` — JSON Schema for OpenAI API compatibility
- `packages/runtime/src/aicp_runtime/api/routes/openai_compatible.py` — FastAPI router
- `packages/runtime/src/aicp_runtime/server/app.py` — Router registration
- `packages/runtime/tests/api/test_openai_compatible.py` — 12 test cases
- `/v1/chat/completions` — non-streaming + SSE streaming
- `/v1/models` — OpenAI-style model list
- `/v1/embeddings` — discovery-ranked capability vectors
- Bearer auth via session_service

**M3: DEK Credential Encryption — COMPLETE**
- `spec/schemas/credential.schema.json` — JSON Schema for encrypted credential format
- `packages/core/src/aicp/security/encryption.py` — DEK encryption (312 lines)
- `packages/core/tests/security/test_encryption.py` — 19 test cases
- AES-256-GCM DEK per credential, KEK from `AICP_MASTER_KEY` via PBKDF2 or `InMemoryKMSClient`
- Stored format: `{encrypted_dek, kek_id, iv, tag, ciphertext}` (base64)
- Scope-derived keying, KEK rotation with backward compat, `EncryptionAuditLog`

**M4: 4-Canonical MCP Tools — COMPLETE**
- `packages/runtime/src/aicp_runtime/mcp_tools.py` — 4 tools (354 lines)
- `packages/runtime/tests/test_mcp_tools.py` — 14 test cases
- `aicp_setup`, `aicp_list_capabilities`, `aicp_get_schema`, `aicp_run`
- Based on Corsair's `buildCorsairToolDefs` pattern

### Wave 3: P1 Runtime Features (2026-04-06)

**M5: Cron/Scheduling Service — COMPLETE**
- `spec/schemas/schedule.schema.json` — JSON Schema for schedule definitions
- `packages/runtime/src/aicp_runtime/services/scheduler.py` — Scheduler service (339 lines)
- `packages/runtime/tests/services/test_scheduler.py` — 20 test cases
- Three schedule types: cron, interval, one_time
- Cron expression parsing, timezone support, SQLite persistence
- Concurrency control via mutex locks, pause/resume

**M6: Session Compaction Service — COMPLETE**
- `spec/schemas/compaction.schema.json` — JSON Schema for compaction config
- `packages/runtime/src/aicp_runtime/services/compaction.py` — Compaction service (400+ lines)
- `packages/runtime/tests/services/test_compaction.py` — 25 test cases
- Three modes: aggressive, balanced, preserve
- Preserves approvals, policy changes, capability outputs, audit entries

**M7: Docker Sandboxing — COMPLETE**
- `spec/schemas/sandbox.schema.json` — JSON Schema for sandbox config
- `packages/runtime/src/aicp_runtime/services/sandbox.py` — Sandbox service (200+ lines)
- `packages/runtime/tests/services/test_sandbox.py` — 10 test cases
- Resource limits: CPU, memory, disk, timeout
- Security: blocked imports/keywords

**M8: Web Search (multi-provider) — COMPLETE**
- `spec/schemas/search.schema.json` — JSON Schema for search config
- `packages/runtime/src/aicp_runtime/services/search.py` — Search service (180+ lines)
- `packages/runtime/tests/services/test_search.py` — 10 test cases
- Providers: Brave, DuckDuckGo, Exa, Tavily, SearXNG
- Fallback chain, caching (5-min TTL)

**M9: Browser Automation — COMPLETE**
- `spec/schemas/browser.schema.json` — JSON Schema for browser automation
- `packages/runtime/src/aicp_runtime/services/browser.py` — Browser service (276 lines) using Playwright
- `packages/runtime/tests/services/test_browser.py` — 28 test cases
- Actions: navigate, snapshot, click, type, screenshot, evaluate, wait, back, forward, refresh
- Security: SSRF-protected, blocks private IPs (127.x, 10.x, 192.168.x)
- Multi-context: parallel session support, cookie management

**M10: Heartbeat Service — COMPLETE**
- `spec/schemas/heartbeat.schema.json` — JSON Schema for heartbeat/leader election
- `packages/runtime/src/aicp_runtime/services/heartbeat.py` — Heartbeat service (273 lines)
- `packages/runtime/tests/services/test_heartbeat.py` — 27 test cases
- Tasks: health_check, cache_warming, session_cleanup, schedule_trigger, metrics_collection
- Leader election: SQLite-based with failover, 15s timeout
- Failure handling: configurable thresholds, automatic leadership release

**M11: Voice/STT/TTS — COMPLETE**
- `spec/schemas/voice.schema.json` — JSON Schema for voice operations
- `packages/runtime/src/aicp_runtime/services/voice.py` — Voice service (320+ lines)
- `packages/runtime/tests/services/test_voice.py` — 20 test cases
- Providers: Deepgram (STT), OpenAI (STT/TTS), ElevenLabs (TTS)
- Operations: transcribe, synthesize, stream synthesis
- Real API integration with fallback to graceful errors when libs not installed

New schemas:
- `ssrf-config.schema.json` — IP ranges, blocked hostnames, allowlists, DNS rebinding
- `credential.schema.json` — Encrypted credential envelope format
- `openai-compatible.schema.json` — OpenAI API compatibility endpoints
- `schedule.schema.json` — Cron, interval, one-time scheduling
- `compaction.schema.json` — Session compaction config
- `sandbox.schema.json` — Sandbox execution config
- `search.schema.json` — Multi-provider search config
- `browser.schema.json` — Browser automation config
- `heartbeat.schema.json` — Heartbeat/leader election config
- `voice.schema.json` — Voice/STT/TTS config

Total tests: 1018 Python + 77 Rust = 1095+
Total schemas: 26

---

## Recent Changes (2026-04-05)

### v1.0.0 Complete — Compliance Level 5

All remaining modules implemented:

- **Module 1: Principal and Org Control** - Added identity hierarchy, org boundaries, delegation chains
- **Module 6: Perception and Signal Layer** - Added `perception/perception.py` with SignalType, AccessibilityTree, DOMSnapshot, PerceptionService, SignalExtractor
- **Module 16: Federation** - Added `federation/federation.py` with CRDTRegistry, FederationService, DIDAuthenticator, CapabilityMesh
- **Module 17: Human Web Compatibility** - Added `web/web_compatibility.py` with WebAction, FormDefinition, WebAutomationProvider, A11yWebBridge
- **Module 19: Learning System** - Added `learning/learning.py` with LearningService, SkillMiner, PolicyLearner, DriftDetector
- **Module 20: Domain Packs** - Added `domains/domains.py` with DomainPackRegistry, EcommercePack, ProductivityPack, DevOpsPack, BenchmarkSuite

New schemas added:
- `perception.schema.json` - Signal types, accessibility tree, DOM snapshot, user interactions
- `web-compatibility.schema.json` - Web actions, form definitions, page state
- `federation.schema.json` - CRDT registries, federation nodes, cross-org capabilities
- `learning.schema.json` - Skills, mined patterns, drift detection, autonomy calibration
- `domains.schema.json` - Domain packs, benchmarks, benchmark suites

Total tests: 740 (was 737)
Total schemas: 16 (was 11)

### Phase 3 Complete — LangChain/LangGraph Adapters (2026-04-03)

- LangChain Adapter: 22 tests passing
- LangGraph Adapter: 24 tests passing
- Food Ordering Reference: 33 tests passing
- Loop/Subflow/Branch: Implemented in core

### Phase 4 Complete — Enterprise Features (2026-04-05)

Enterprise features for Mammoth (Rust TUI shell):

**Security & Permissions:**
- PermissionPattern with wildcard/glob matching (permissions.rs)
- OperationalMode enum (Default, Plan, Bypass, Auto) + PermissionModeManager
- SsrfGuard for URL validation (security.rs)
- SandboxExecutor with Linux/macOS OS-conditional isolation

**Plugin Ecosystem:**
- RegistryClient for plugin marketplace discovery (plugins/src/registry.rs)
- PluginSigner/PluginVerifier for Ed25519 code signing (plugins/src/signing.rs)
- MarketplaceOverlay TUI for plugin management (plugins/src/tui.rs)

**Observability & Cost:**
- PerformanceTracer with nested spans (tracing.rs)
- TelemetryExporter with OTEL/Prometheus (telemetry.rs, feature-gated)
- CostEstimator with model pricing table (usage.rs)
- UsageTracker with tool breakdown and budget checking

**Workflow Authoring:**
- NlWorkflowParser for natural language workflow definition (nl_workflow.rs)
- WorkflowCompiler with subflow_id validation (workflow_compiler.rs)
- WorkflowSimulator for dry-run analysis (workflow_simulator.rs)
- FlowBuilderOverlay TUI for visual workflow editing (flow_builder_tui.rs)

**Audit & Subflows:**
- AuditLog + PermissionAuditEntry with CLI command (commands/audit.rs)
- SubflowExecutor in Python runtime (workflow/subflow.py)
- Phase 4 E2E tests: 8 Rust + 3 Python passing

**Files Created/Modified:**
- `apps/mammoth/crates/runtime/src/tracing.rs`
- `apps/mammoth/crates/runtime/src/telemetry.rs`
- `apps/mammoth/crates/runtime/src/nl_workflow.rs`
- `apps/mammoth/crates/runtime/src/workflow_compiler.rs`
- `apps/mammoth/crates/runtime/src/workflow_simulator.rs`
- `apps/mammoth/crates/runtime/src/flow_builder_tui.rs`
- `apps/mammoth/crates/runtime/src/usage.rs` (extended)
- `apps/mammoth/crates/runtime/src/security.rs`
- `apps/mammoth/crates/plugins/src/registry.rs`
- `apps/mammoth/crates/plugins/src/signing.rs`
- `apps/mammoth/crates/plugins/src/tui.rs`
- `apps/mammoth/crates/commands/src/audit.rs`
- `packages/runtime/src/aicp_runtime/workflow/subflow.py`

Total tests: 740 (Python) + 77 (Rust mammoth-cli)
