# SUPER-PLAN: AICP (Control Plane + Mammoth Shell) vs OpenClaw vs Corsair

## Goal
Fill every gap between AICP+Mammoth and the best of OpenClaw/Corsair, making AICP the undisputed best platform — superior to both combined.

## Architecture Clarification

```
AICP Platform
├── AICP (Control Plane)     ← Core protocol, schemas, runtime services
│   ├── 20 modules (L5 complete)
│   ├── 18 JSON schemas
│   ├── 740+ tests
│   └── Governance, Workflow, Federation, Learning, etc.
│
└── Mammoth (Primary Shell)  ← NOT a reference repo, IS part of AICP
    ├── 12 Rust crates
    ├── TTY UI, Design System
    ├── Slack/Telegram/Discord adapters
    ├── VS Code Extension (skeleton)
    ├── Browser Extension (partial)
    └── 5K-line tools, 2.6K-line commands
```

**Reference repos (for learning only):**
- **OpenClaw**: `/apps/openclaw` — 12,086 TypeScript files, 93 extensions
- **Corsair**: `/apps/corsair` — 38 integration plugins, 4-canonical MCP tools

---

## Definitive Feature Matrix

| # | Feature | AICP+Mammoth | OpenClaw | Corsair | Winner | AICP Gap |
|---|---------|:------------:|:--------:|:-------:|:------:|:--------:|
| **CORE PROTOCOL** |
| 1 | Capability Registry + Schema | ✅ | ✅ | ✅ | **AICP** | None — spec-first, strongest |
| 2 | Workflow Engine (sequential/parallel/event-driven/loops/subflows) | ✅ | ❌ | ❌ | **AICP** | None — OpenClaw has zero workflow engine |
| 3 | Policy Engine (compiled, trust tiers, risk scoring) | ✅ | ❌ | ❌ | **AICP** | None |
| 4 | Approval Lifecycle (intent matching, blast radius) | ✅ | ❌ | ❌ | **AICP** | None |
| 5 | Audit/Replay (append-only, correlation IDs) | ✅ | Partial | ✅ | **AICP** | None — AICP's is deeper |
| 6 | Multi-Agent Hierarchy (orchestrator/specialist/worker/supervisor) | ✅ | ✅ | ❌ | **AICP** | OpenClaw has flat agent loop only |
| 7 | Federation (CRDT, DID auth, .well-known discovery) | ✅ | ❌ | ❌ | **AICP** | None |
| 8 | Learning System (skill mining, drift detection) | ✅ | ❌ | ❌ | **AICP** | None |
| 9 | Perception/Signal Layer (a11y, DOM, screenshots) | ✅ | ❌ | ❌ | **AICP** | None |
| 10 | Execution Engine (realtime/transactional/event-driven) | ✅ | ❌ | ❌ | **AICP** | OpenClaw has no real execution engine |
| 11 | Session Management (resumable, multi-tenancy) | ✅ | ✅ | ✅ | **AICP** | OpenClaw's session compaction is more advanced |
| 12 | Discovery (semantic search, ranked, graph traversal) | ✅ | ✅ | ❌ | **TIE** | — |
| 13 | MCP Server (exposes AICP outward) | ✅ | ❌ | ❌ | **AICP** | OpenClaw has no MCP server |
| 14 | MCP Adapter (consume external tools) | ✅ | ❌ | ❌ | **AICP** | None |
| 15 | TTY UI (ratatui, full-screen shell) | ✅ | ❌ | ❌ | **AICP** | Mammoth has this |
| 16 | Design System (components, themes, dialogs) | ✅ | ❌ | ❌ | **AICP** | Mammoth has this |
| 17 | OAuth (refresh, token management) | ✅ | ✅ | ❌ | **TIE** | — |
| 18 | Code Intelligence (AST, symbol graph, call chains) | ✅ | ❌ | ❌ | **AICP** | Unique to AICP |
| **PLUGIN & PROVIDER** |
| 19 | Plugin System (manifest, loader, registry, hooks, sandbox) | ✅ | ✅ | ❌ | **AICP** | **Wave 1 DONE** |
| 20 | Provider Routing (multi-LLM, fallback chains) | ✅ | ✅ | ❌ | **AICP** | **Wave 1 DONE** |
| 21 | Multi-Channel (26+ messaging platforms) | ✅ | ✅ | ❌ | **AICP** | **Wave 1 DONE** |
| 22 | Cost/Token Tracking (budget, reporting) | ✅ | ✅ | ❌ | **AICP** | **Wave 1 DONE** |
| 23 | Webhook System (signature verification, routing) | ✅ | ✅ | ✅ | **AICP** | **Wave 1 DONE** |
| 24 | 38 Integration Plugins (Slack, GitHub, Linear, Gmail, etc.) | Slack/TG/Discord | ❌ | ✅ | **Corsair** | 🔴 **MISSING** — only 3 of 38 |
| 25 | Credential Encryption (DEK-based, rotation) | ❌ | ✅ | ✅ | **Corsair** | 🔴 **MISSING** |
| 26 | Zod Schema ORM (Kysely, SQLite + PostgreSQL) | ❌ | ❌ | ✅ | **Corsair** | 🔴 **MISSING** (if ORM approach chosen) |
| 27 | 4-Canonical MCP Tools (setup, list_ops, get_schema, run) | ❌ | ❌ | ✅ | **Corsair** | 🔴 **MISSING** |
| **AGENT CAPABILITIES** |
| 28 | SSRF Protection | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 29 | Cron/Scheduling Service | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 30 | Session Compaction (advanced context management) | Basic | ✅ | ❌ | **OpenClaw** | ⚠️ **PARTIAL** — Mammoth has 25K-line compact.rs |
| 31 | Docker Sandboxing | Partial | ✅ | ❌ | **OpenClaw** | ⚠️ **PARTIAL** — Mammoth has 13K-line sandbox.rs |
| 32 | OpenAI-Compatible API (/v1/chat/completions) | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** — all three lack this |
| 33 | Web Search (Brave, DuckDuckGo, Exa, Tavily) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 34 | Browser Control (CDP, snapshots, actions) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 35 | Voice/STT/TTS (Deepgram, ElevenLabs) | Basic | ✅ | ❌ | **OpenClaw** | ⚠️ **PARTIAL** — Mammoth has 7.8K-line voice.rs |
| 36 | Image/Video Generation (FAL, Runway) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 37 | Heartbeat Service (proactive wake-up) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 38 | Dream Consolidation (memory optimization) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 39 | IDE Bridge (VS Code, JetBrains) | VS Code skeleton | ✅ | ❌ | **OpenClaw** | ⚠️ **PARTIAL** — VS Code ext is skeleton only |
| **SECURITY** |
| 40 | Permission Audit Trail | ✅ | ❌ | ✅ | **AICP** | Mammoth has audit.rs |
| 41 | Multi-Tenancy (org isolation) | ✅ | ✅ | ✅ | **TIE** | AICP's is governance-native |
| **PLATFORM** |
| 42 | macOS Menu Bar App | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 43 | Mobile (iOS/Android) | ❌ | ✅ | ❌ | **OpenClaw** | 🔴 **MISSING** |
| 44 | Observability (OpenTelemetry, structured logging) | Basic | ✅ | ❌ | **OpenClaw** | ⚠️ **PARTIAL** — Mammoth has telemetry.rs, tracing.rs |
| **SDK & INTEGRATION** |
| 45 | TypeScript SDK (core built, runtime/client skeleton) | Core only | ✅ | ✅ | **OpenClaw** | ⚠️ **PARTIAL** — TS runtime/client missing |
| 46 | Python SDK (skeleton) | Skeleton | ❌ | ❌ | **AICP** | ⚠️ **PARTIAL** — Python SDK skeleton only |
| 47 | Express Framework Adapter | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** |
| 48 | NestJS Framework Adapter | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** |
| 49 | LangChain Agent Adapter | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** |
| 50 | LangGraph Agent Adapter | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** |
| 51 | CrewAI Agent Adapter | ❌ | ❌ | ❌ | **NONE** | 🔴 **MISSING** |

---

## What AICP Already Wins

AICP+Mammoth is the **only** platform with:
1. **Spec-first protocol** — 18 JSON schemas as source of truth
2. **Complete workflow engine** — OpenClaw has zero workflows
3. **Compiled policy engine** — trust tiers, risk scoring, approval lifecycle
4. **Federation** — CRDT registries, DID auth, .well-known discovery
5. **Learning system** — skill mining, drift detection, autonomy calibration
6. **Perception layer** — a11y, DOM, screenshots, behavioral signals
7. **MCP bidirectional** — server (exposes outward) AND adapter (consumes inward)
8. **Multi-agent hierarchy** — orchestrator/specialist/worker/supervisor (OpenClaw is flat)
9. **6-type memory** — working/episodic/semantic/skill/environmental/shared
10. **Code intelligence** — AST indexing, symbol graph, call chains
11. **TTY shell** — full-screen ratatui interface (OpenClaw and Corsair have none)
12. **Design system** — Mammoth UI components, themes, dialogs
13. **Mammoth** — the primary shell, not a reference repo

---

## Missing Features: Priority Classification

### 🔴 CRITICAL (P0) — Security & Platform Must-Haves
| # | Feature | Reference | Why It Matters |
|---|---------|-----------|----------------|
| M1 | **SSRF Protection** | OpenClaw `packages/fetch/` | Security baseline — block private IPs, DNS rebinding |
| M2 | **OpenAI-Compatible API** | Unique gap | `/v1/chat/completions` — enables all OpenAI-compatible clients |
| M3 | **DEK Credential Encryption** | Corsair `crypto.ts` | Secure storage of API keys, rotation support |
| M4 | **4-Canonical MCP Tools** | Corsair server | Standardize AICP's MCP tool interface |

### 🟡 HIGH (P1) — Runtime & Agent Capabilities
| # | Feature | Reference | Mammoth Has |
|---|---------|-----------|-------------|
| M5 | **Cron/Scheduling Service** | OpenClaw `packages/scheduler/` | ❌ |
| M6 | **Advanced Session Compaction** | OpenClaw + Mammoth | ✅ `compact.rs` (25K lines) — needs porting to AICP |
| M7 | **Docker Sandboxing** | OpenClaw + Mammoth | ✅ `sandbox.rs` (13K lines) — needs AICP integration |
| M8 | **Web Search (multi-provider)** | OpenClaw `packages/search/` | ❌ |
| M9 | **Browser Control (CDP)** | OpenClaw `packages/browser/` | ❌ |
| M10 | **Heartbeat Service** | OpenClaw `packages/heartbeat/` | ❌ |

### 🟢 MEDIUM (P2) — Advanced Features
| # | Feature | Reference | Mammoth Has |
|---|---------|-----------|-------------|
| M11 | **Voice/STT/TTS (full)** | OpenClaw `packages/voice/` | ✅ `voice.rs` (7.8K) — needs AICP integration |
| M12 | **Dream Consolidation** | OpenClaw `packages/dream/` | ❌ |
| M13 | **Image/Video Generation** | OpenClaw `packages/media/` | ❌ |
| M14 | **VS Code Extension (full)** | OpenClaw IDE bridge | ⚠️ Skeleton only |
| M15 | **macOS Menu Bar App** | OpenClaw `packages/macos/` | ❌ |
| M16 | **Mobile (iOS/Android)** | OpenClaw | ❌ |
| M17 | **OpenTelemetry (full)** | OpenClaw | ⚠️ Basic tracing only |

### ⚪ LOW (P3) — SDK & Framework Adapters
| # | Feature | Reference |
|---|---------|-----------|
| M18 | **TypeScript Runtime/Client SDK** | OpenClaw, Corsair |
| M19 | **Python SDK (full)** | AICP skeleton |
| M20 | **Express Framework Adapter** | — |
| M21 | **NestJS Framework Adapter** | — |
| M22 | **LangChain Agent Adapter** | — |
| M23 | **LangGraph Agent Adapter** | — |
| M24 | **CrewAI Agent Adapter** | — |

---

## Integration Gap: 38 Plugins

Corsair has **38 integration plugins** that AICP lacks:

| Category | Plugins | AICP Status |
|----------|---------|-------------|
| **Communication** | Slack, Teams, Discord, SMS | ✅ Slack/TG/Discord (Mammoth) |
| **Code** | GitHub, GitLab, Bitbucket | ❌ MISSING |
| **Project** | Linear, Asana, Jira, Notion | ❌ MISSING |
| **CRM** | Salesforce, HubSpot | ❌ MISSING |
| **Communication** | Gmail, SendGrid, Mailchimp | ❌ MISSING |
| **Storage** | Google Drive, Dropbox, S3 | ❌ MISSING |
| **Analytics** | Mixpanel, Amplitude, PagerDuty | ❌ MISSING |
| **Payments** | Stripe, Braintree | ❌ MISSING |
| **Support** | Zendesk, Intercom | ❌ MISSING |

**Priority**: Start with GitHub, Linear, Gmail — the most common agentic use cases.

---

## Implementation Plan

### Wave 0: Fix Blockers (IMMEDIATE)
**Goal**: Get mammoth development unblocked

1. Fix `crates/commands/src/audit.rs` — `PermissionMode` vs `PermissionOutcome` type mismatch
2. Fix duplicate `PermissionMode` definition (test vs lib scope collision)
3. Run `cargo test` clean — restore 77 passing tests
4. Update `PermissionAuditEntry` schema if it changed

### Wave 1: DONE ✓ (Completed This Session)
**Goal**: Already integrated into AICP core

- ✅ Plugin System — manifest, loader, registry, hooks, sandbox, SDK
- ✅ Provider Routing — multi-LLM, fallback chains, health checks
- ✅ Multi-Channel Architecture — 26+ platforms, routing, priority
- ✅ Cost/Token Tracking — budget management, reporting
- ✅ Webhook System — signature verification, routing

### Wave 2: CRITICAL Security & Platform (P0)
**Goal**: Close the biggest gaps — security and compatibility

#### M1: SSRF Protection
- **Reference**: OpenClaw `packages/fetch/src/fetch.ts`
- **Files**: `aicp/core/src/aicp/security/ssrf.py`
- **Spec**: `spec/schemas/ssrf-config.schema.json`
- **Implementation**:
  - Block private IP ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `0.0.0.0/8`
  - Block IPv6: `::1`, `fc00::/7`, `fe80::/10`
  - DNS rebinding protection: resolve → validate → re-validate on connect
  - Block schemes: `file://`, `ftp://`, `gopher://`
  - Allowlist mode: configurable domains/IPs
  - Max redirect depth (default: 5)
- **Tests**: block private IP, allow public IP, redirect limit, DNS rebinding, scheme block

#### M2: OpenAI-Compatible API
- **Reference**: Unique gap — no competitor has this
- **Files**: `aicp_runtime/src/aicp_runtime/api/routes/openai_compatible.py`
- **Spec**: `spec/schemas/openai-compatible.schema.json`
- **Implementation**:
  - `POST /v1/chat/completions` → map to AICP capability execution
  - `GET /v1/models` → return available capability models
  - `POST /v1/embeddings` → map to AICP memory/embedding service
  - Auth: `Authorization: Bearer <api_key>`
  - Streaming via Server-Sent Events
  - Map OpenAI error codes → AICP error schema
- **CLI**: `aicp dev --openai-compatible --port 8080`
- **Tests**: completions, streaming, embeddings, error mapping, auth

#### M3: DEK-Based Credential Encryption
- **Reference**: Corsair `apps/api/src/crypto.ts`, `packages/crypto/src/`
- **Files**: `aicp/core/src/aicp/security/encryption.py`
- **Spec**: `spec/schemas/credential.schema.json`
- **Implementation**:
  - Data Encryption Key (DEK): AES-256-GCM per credential
  - Key Encryption Key (KEK): from `AICP_MASTER_KEY` env var or KMS
  - DEK rotation: re-wrap with new KEK, preserve old KEK for decryption
  - Stored format: `{encrypted_dek, kek_id, iv, tag}`
  - Scoping: per-tenant, per-user, per-capability
  - Audit log for key rotations
- **Tests**: encrypt/decrypt, rotation, scoping, audit

#### M4: 4-Canonical MCP Tools Pattern
- **Reference**: Corsair `apps/api/src/mcp/` server
- **Files**: `aicp/mcp/src/tools.py`
- **Implementation**:
  - `setup` — initialize MCP session with capabilities
  - `list_operations` — enumerate available operations
  - `get_schema` — return typed input/output schema for operation
  - `aicp_run` — execute capability with validated input
  - Dynamic schema generation from AICP capability schemas
- **Tests**: each tool, dynamic schema, error cases

### Wave 3: HIGH Runtime & Agent (P1)
**Goal**: Enable cron, sandbox, search, browser, compaction

#### M5: Cron/Scheduling Service
- **Reference**: OpenClaw `packages/scheduler/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/scheduler.py`
- **Spec**: `spec/schemas/schedule.schema.json`
- **Implementation**:
  - Cron expression parsing (min/hr/day/mo/dow)
  - Timezone-aware (per-tenant configurable)
  - Types: one-shot, recurring, interval
  - Persist to SQLite — resume after restart
  - Wake triggers: HTTP webhook, capability execution, signal event
  - Concurrency control: mutex locks per schedule
  - Missed execution: skip, catch-up, or alert
- **CLI**: `aicp schedule "0 9 * * MON-FRI" capability.execute --name daily-report`
- **API**: `/v1/schedules` CRUD

#### M6: Advanced Session Compaction (Port from Mammoth)
- **Reference**: Mammoth `crates/runtime/src/compact.rs` (25K lines — richest impl)
- **Files**: `aicp_runtime/src/aicp_runtime/services/compaction.py`
- **Spec**: `spec/schemas/compaction.schema.json`
- **Implementation**:
  - Port Mammoth's compaction logic to AICP runtime
  - Context budget management: configurable token limits per session
  - Three modes: aggressive, balanced, preserve
  - Relevance scoring: keep high-signal, compress low-signal
  - Preserve invariant: never compact approvals, policy changes, capability outputs
  - Compaction events: log before/after sizes, token counts
  - Auto-compact on budget threshold
- **CLI**: `aicp session compact sess_abc123 --mode aggressive`
- **Tests**: each mode, preserve invariants, token budgets

#### M7: Docker Sandboxing (Port from Mammoth + OpenClaw)
- **Reference**: Mammoth `crates/runtime/src/sandbox.rs` (13K), OpenClaw `packages/sandbox/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/sandbox.py`
- **Spec**: `spec/schemas/sandbox.schema.json`
- **Implementation**:
  - Port Mammoth sandbox to AICP runtime
  - Docker image: `aicp-sandbox:latest` (Alpine-based, no network)
  - Sandboxed capabilities: code execution, regex, eval, dynamic import
  - Resource limits: CPU (0.5 cores), Memory (256MB), Disk (50MB), Time (30s)
  - IPC: stdio only, no filesystem outside `/tmp/sandbox/`
  - Image pull: lazy, cache, fallback
  - Capability marking: `sandbox: true` in manifest → auto-sandbox
  - Policy integration: high-risk capabilities → auto-sandbox
- **CLI**: `aicp sandbox run --image aicp-sandbox -- ls /`
- **Tests**: resource limits, network isolation, IPC

#### M8: Multi-Provider Web Search
- **Reference**: OpenClaw `packages/search/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/search.py`
- **Spec**: `spec/schemas/search.schema.json`
- **Implementation**:
  - Providers: Brave (default), DuckDuckGo, Exa, Tavily, SearXNG
  - Unified interface: `SearchResult = {title, url, snippet, provider, score}`
  - Fallback chain: Brave → DuckDuckGo → Exa
  - Rate limiting per provider (via cost tracking)
  - Caching: 5-min TTL for identical queries
  - Safe search filtering
  - Add as capability: `web.search(query, provider?, num_results?)`
- **CLI**: `aicp search "AI news" --provider brave --num 10`
- **Tests**: each provider, fallback, caching, rate limit

#### M9: Browser Control (CDP)
- **Reference**: OpenClaw `packages/browser/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/browser.py`
- **Spec**: `spec/schemas/browser.schema.json`
- **Implementation**:
  - Use Playwright MCP or CDP via `playwright`
  - Capabilities: `browser.navigate`, `browser.snapshot`, `browser.click`, `browser.type`, `browser.screenshot`
  - Session persistence: reuse browser context across calls
  - Cookie management: import/export, per-session isolation
  - Headless by default, headed for debugging
  - SSRF integration: block navigation to private IPs
- **Add to capability registry**: `browser.*` namespace

#### M10: Heartbeat Service
- **Reference**: OpenClaw `packages/heartbeat/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/heartbeat.py`
- **Implementation**:
  - Periodic task execution (30s–1hr interval)
  - Use cases: health checks, cache warming, session cleanup, schedule trigger
  - Distributed heartbeat: leader election via SQLite lock
  - Failover: if leader dies, another instance takes over
- **CLI**: `aicp heartbeat configure --interval 60s --task health-check`

### Wave 4: MEDIUM Advanced Features (P2)
**Goal**: Complete the feature set

#### M11: Voice/STT/TTS (Full, integrate Mammoth)
- **Reference**: Mammoth `crates/runtime/src/voice.rs` (7.8K lines)
- **Files**: `aicp_runtime/src/aicp_runtime/services/voice.py`
- **Implementation**: Port Mammoth voice to AICP as `media.voice` capability

#### M12: Dream Consolidation
- **Reference**: OpenClaw `packages/dream/`
- **Files**: `aicp/core/src/aicp/memory/consolidation.py`
- **Implementation**: Memory triage, forgetting curve, batch embedding

#### M13: Image/Video Generation
- **Reference**: OpenClaw `packages/media/`
- **Files**: `aicp_runtime/src/aicp_runtime/services/media.py`
- **Implementation**: FAL AI, Replicate, Runway providers as `media.*` capability

#### M14: VS Code Extension (Full)
- **Reference**: Mammoth `vscode-extension/` (skeleton)
- **Implementation**: Expand to full IDE bridge with AICP connection

#### M15-M16: macOS Menu Bar + Mobile
- **Reference**: OpenClaw `packages/macos/`, `packages/ios/`, `packages/android/`
- **Lower priority** — platform-specific, lower ROI

#### M17: OpenTelemetry (Full)
- **Reference**: OpenClaw observability
- **Files**: `aicp_runtime/src/aicp_runtime/telemetry.py`
- **Implementation**: Full OpenTelemetry with traces, metrics, logs

### Wave 5: SDK & Framework Adapters (P3)
**Goal**: Fill remaining adapter gaps

- M18: TypeScript Runtime/Client SDK → `sdks/typescript/`
- M19: Python SDK (full) → `sdks/python/`
- M20: Express Framework Adapter → `adapters/framework/express/`
- M21: NestJS Framework Adapter → `adapters/framework/nestjs/`
- M22-M24: LangChain, LangGraph, CrewAI Agent Adapters → `adapters/agent/`

### Wave 6: Integration Plugins (Long-term)
**Goal**: Match Corsair's 38 plugins

Priority order:
1. **GitHub** — code, PRs, issues, actions
2. **Linear** — projects, issues, sprints
3. **Gmail** — email read/send
4. **Notion** — pages, databases
5. **Stripe** — payments, subscriptions
6. Remaining: Salesforce, Jira, Asana, Slack (full), etc.

Each plugin: create adapter pattern, add to capability registry, write tests.

---

## Quick Wins (Before Wave 2)

| # | Task | Time | Impact |
|---|------|------|--------|
| QW1 | **Fix mammoth tests** | 30 min | Unblocks all mammoth development |
| QW2 | **`aicp dev --openai-compatible`** | 2 hrs | Biggest "wow" factor — enables all OpenAI clients |
| QW3 | **SSRF guard on HTTP execution** | 2 hrs | Security baseline from OpenClaw's blocklist |
| QW4 | **Port Mammoth compact.rs → AICP** | 4 hrs | Most advanced compaction across all three repos |
| QW5 | **4-canonical MCP tools on AICP MCP server** | 3 hrs | Corsair's best pattern on AICP's MCP server |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Feature parity with OpenClaw | ~65% | 95%+ |
| Feature parity with Corsair | ~55% | 90%+ |
| Mammoth Rust tests | 0 (blocked) | 77 |
| AICP Python tests | 251 | 400+ |
| Critical gaps (P0) | 4 | 0 |
| High gaps (P1) | 6 | 0 |
| Medium gaps (P2) | 7 | 0 |
| OpenAI-compatible API | ❌ | ✅ |
| SSRF Protection | ❌ | ✅ |
| DEK Encryption | ❌ | ✅ |
| Cron/Scheduling | ❌ | ✅ |
| Docker Sandboxing | ✅ partial | ✅ full |
| Session Compaction | ✅ basic | ✅ advanced |
| Web Search | ❌ | ✅ |
| Browser Control | ❌ | ✅ |
| Integration Plugins | 3 | 38 |

---

## Execution Rules
- Spec-first: document in `/spec` before implementing
- Wave 0 MUST complete before anything else (fix mammoth tests first)
- Every feature needs tests (min 3: happy path, error, edge case)
- No `as any`, `@ts-ignore`, empty catch blocks
- Mammoth and AICP stay in sync — Mammoth is the primary shell
- Append learnings: `.sisyphus/notepads/openclaw-features/learnings.md`

## Notepad References
- `.sisyphus/notepads/openclaw-features/learnings.md` — implementation learnings
- `.sisyphus/notepads/openclaw-features/issues.md` — blockers and workarounds
- `.sisyphus/notepads/openclaw-features/decisions.md` — architectural decisions
