# AICP — Current State

> **Version:** 0.9.10 | **Date:** 2026-04-06 | **Compliance:** Level 5 (Full Orchestration)

---

## Product Definition

**AICP (AI Capability Protocol)** is the control plane for secure agentic execution. It gives organizations a governed way to expose application actions as typed capabilities, run resumable workflows, enforce policy before side effects, hold risky work for approval, and keep every execution attributable and replayable.

**Mammoth** is the primary interaction shell — a Rust TUI for operators and agents.

---

## What's Built (v0.9.10)

### Spec — 23 JSON Schemas

| Schema | Purpose |
|--------|---------|
| `capability.schema.json` | 5 kinds: action, query, workflow, async_action, batch_action |
| `workflow.schema.json` | Sequential, parallel, fork/join, sagas, loops, subflows |
| `workflow-dsl.schema.json` | YAML workflow definition |
| `policy.schema.json` | Allow/deny/ask/limit, trust tiers, risk scoring |
| `execution-result.schema.json` | Canonical execution envelope |
| `approval-request.schema.json` | Risk assessment, blast radius |
| `approval-decision.schema.json` | Approve/deny with reason |
| `audit-entry.schema.json` | Append-only audit trail |
| `session.schema.json` | Resumable sessions |
| `discovery.schema.json` | `/.well-known/aicp` |
| `error.schema.json` | Structured errors |
| `perception.schema.json` | a11y tree, DOM, screenshots |
| `web-compatibility.schema.json` | Web actions, forms |
| `federation.schema.json` | CRDT, DID, cross-org |
| `learning.schema.json` | Skill mining, drift detection |
| `domains.schema.json` | Domain packs |
| `ssrf-config.schema.json` | SSRF protection |
| `credential.schema.json` | DEK encryption |
| `openai-compatible.schema.json` | OpenAI API compat |
| `plugin.schema.json` | Plugin definition |
| `plugin-manifest.schema.json` | Plugin manifest |
| `search.schema.json` | Web search |
| `browser.schema.json` | Browser control |

---

### Runtime — 10 Services

| Service | Purpose |
|---------|---------|
| **ExecutionEngine** | Realtime, transactional, event-driven execution |
| **ApprovalService** | Approval lifecycle, intent matching |
| **WorkflowRuntime** | Sequential, parallel, loops, subflows |
| **SessionManager** | Resumable sessions, state persistence |
| **DiscoveryService** | Semantic search, ranked discovery |
| **AuditService** | Append-only audit trail |
| **InteractionService** | Natural language → capability mapping |
| **ProviderHealth** | Multi-LLM health monitoring |
| **SchedulerService** | Cron scheduling, periodic tasks |
| **TelemetryService** | OpenTelemetry tracing |

---

### API — 30+ Endpoints

| Group | Endpoints |
|-------|-----------|
| `/v1/capabilities` | List, get, execute |
| `/v1/workflows` | Create, resume, list, events |
| `/v1/policies` | List, evaluate |
| `/v1/approvals` | List, decide |
| `/v1/sessions` | Create, resume, list |
| `/.well-known/aicp` | Discovery |
| `/health` | Health check |

---

### CLI — 28 Commands

```
run         Execute a capability
dev         Start dev server
scan        Import from OpenAPI
preview     Show capability schema
protect     Require approval
safe        Mark as safe
deny        Block capability
limit       Rate limiting
appr        Approval queue management
session     Session management
```

---

### Mammoth (Rust Shell)

| Crate | Purpose |
|-------|---------|
| `mammoth-cli` | User-facing binary |
| `runtime` | Session, permissions, tools |
| `api` | Provider clients, streaming |
| `commands` | Slash-command registry |
| `plugins` | Plugin discovery |
| `ui` | TUI components |
| `tools` | Built-in tools |
| `adapters/*` | Slack, Telegram, Discord |

---

## Tests

| Suite | Count |
|-------|-------|
| **Python (core + runtime + cli)** | 1038 |
| **Rust (mammoth)** | 186 |
| **Total** | **1224** |

---

## Feature Status

| Feature | Status |
|---------|--------|
| Capability Registry | ✅ Complete |
| Workflow Engine | ✅ Complete |
| Policy Engine | ✅ Complete |
| Approval Lifecycle | ✅ Complete |
| Audit/Replay | ✅ Complete |
| Multi-Agent | ✅ Complete |
| Federation | ✅ Complete |
| Learning System | ✅ Complete |
| Session Management | ✅ Complete |
| Plugin System | ✅ Complete |
| Multi-Channel | ✅ Complete |
| Cost Tracking | ✅ Complete |
| Webhooks | ✅ Complete |
| SSRF Protection | ✅ Complete |
| OpenAI API | ✅ Complete |
| DEK Encryption | ✅ Complete |
| Web Search | ✅ Complete |
| Browser Control | ✅ Complete |
| Scheduler | ✅ Complete |
| Voice/STT/TTS | ✅ Complete |
| VS Code Extension | ✅ Complete |
| macOS Menu Bar | ✅ Complete |
| Mobile (Flutter) | ✅ Complete |
| Python SDK | ✅ Complete |
| TypeScript SDK | ✅ Complete |
| GitHub Integration | ✅ Complete |
| Linear Integration | ✅ Complete |
| Gmail Integration | ✅ Complete |

---

## Compliance Levels

| Level | Name | Requirements | Status |
|-------|------|--------------|--------|
| 0 | Discovery | Capability registry, schema validation | ✅ |
| 1 | Governed Execution | Policy evaluation, audit trail | ✅ |
| 2 | Resumable Workflows | State persistence, resume | ✅ |
| 3 | Event-Driven | Wait-for-event, parallel, loops | ✅ |
| 4 | AI Planning | Planner, judge, context builder | ✅ |
| 5 | Full Orchestration | Multi-agent, federation, learning | ✅ |

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed phase-by-phase plan.

| Phase | Version | Focus |
|-------|---------|-------|
| 0 | 0.1.1-alpha | Foundation |
| 1 | 0.2.0 | AI Core |
| 2 | 0.3.0 | Orchestration |
| 3 | 0.4.0 | Agent Integration |
| 4 | 0.7.0 | Enterprise |
| 5-9 | 0.9.x | Production hardening |
| **Current** | **0.9.10** | **SDKs, integrations, platform apps** |

---

## Known Gaps

- No enforcement semantics for `often_follows` field
- VS Code extension is skeleton (needs full IDE bridge)
- macOS Menu Bar needs real AICP backend connection
- Mobile app needs real AICP backend connection
- Browser extension is partial

---

## Getting Started

```bash
# Install
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli

# Run
aicp dev

# Or run Mammoth
cd apps/mammoth && cargo run -p mammoth-cli -- --help
```

---

*Last updated: 2026-04-06*