# AICP Architecture

> **Version:** 0.9.10 | **Target:** 1.0.0

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Mammoth (Shell)                         │
│                  Rust TUI — operator & agent entry               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AICP Control Plane                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Capability│  │Workflow │  │ Policy  │  │Approval │       │
│  │ Registry │  │ Engine  │  │ Engine  │  │ Service │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Session  │  │  Audit   │  │Discovery │  │Learning │       │
│  │ Manager  │  │  Trail   │  │ Service  │  │ System  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Connected Systems                          │
│    APIs • Databases • GitHub • Slack • Linear • Gmail • ...    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Planes (11 Planes)

| # | Plane | Purpose | Key Components |
|---|-------|---------|-----------------|
| 0 | **Signal** | Event ingestion | Event bus, webhooks |
| 1 | **Perception** | a11y, DOM, screenshots | Accessibility tree, state observation |
| 2 | **AI** | Planner, judge, memory | Intent router, context builder |
| 3 | **Capability** | Registry, discovery | Schema validation, semantic search |
| 4 | **Workflow** | Orchestration | Sequential, parallel, loops, subflows |
| 5 | **Governance** | Policy, approvals | Trust tiers, risk scoring |
| 6 | **Execution** | Runtime | Realtime, transactional, event-driven |
| 7 | **Multi-Agent** | Coordination | Orchestrator, specialist, worker |
| 8 | **Federation** | Cross-org | CRDT registries, DID auth |
| 9 | **Supervision** | Human control | Approval queue, replay |
| 10 | **Learning** | Improvement | Skill mining, drift detection |

---

## 3. Key Components

### AICP (Python Control Plane)

| Component | Path | Purpose |
|-----------|------|---------|
| **Core** | `packages/core/` | Domain models, validation |
| **Runtime** | `packages/runtime/` | Execution engine, services |
| **CLI** | `packages/cli/` | 28 CLI commands |

### Mammoth (Rust Shell)

| Crate | Purpose |
|-------|---------|
| `mammoth-cli` | Binary entry point |
| `runtime` | Sessions, permissions, tools |
| `api` | LLM providers, streaming |
| `commands` | Slash commands |
| `ui` | TUI components |
| `plugins` | Plugin system |
| `adapters/*` | Slack, Telegram, Discord |

---

## 4. Data Flow

```
User Input → Mammoth → AICP Request
       ↓
   Policy Check (allow/deny/ask)
       ↓
   Capability Execution
       ↓
   Execution Result + Audit Entry
       ↓
   Response → Mammoth → User
```

---

## 5. Protocol (Source of Truth)

All protocol defined in `/spec/schemas/`:

- 23 JSON schemas
- Version in schema `$schema` field
- Spec-first: code must match spec

---

## 6. Adapters

| Type | Implementations |
|------|-----------------|
| **Framework** | FastAPI, Express, NestJS |
| **Protocol** | MCP Server, MCP Adapter, OpenAPI |
| **Agent** | LangChain, LangGraph, CrewAI |

---

## 7. Security

| Feature | Description |
|---------|-------------|
| **SSRF Protection** | Block private IPs, DNS rebinding |
| **DEK Encryption** | Per-credential encryption |
| **Policy Engine** | Allow/deny/ask/limit |
| **Approval Lifecycle** | Human-in-the-loop |
| **Audit Trail** | Append-only, replayable |

---

## 8. Getting Started

```bash
# Python control plane
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli
aicp dev

# Rust shell
cd apps/mammoth
cargo run -p mammoth-cli -- --help
```

---

## 9. File Structure

```
AICP/
├── spec/schemas/           # 23 JSON schemas (source of truth)
├── packages/
│   ├── core/                # Domain models
│   ├── runtime/             # Execution services
│   └── cli/                 # CLI commands
├── adapters/
│   ├── framework/           # FastAPI, Express, NestJS
│   ├── protocol/            # MCP, OpenAPI
│   └── agent/               # LangChain, LangGraph, CrewAI
├── sdks/
│   ├── python/              # aicp-sdk
│   └── typescript/          # @aicp/core, runtime, client
└── apps/
    └── mammoth/             # Rust TUI shell
```

---

## 10. Key Decisions

1. **Spec-first** — Protocol changes in `/spec` before code
2. **Mammoth-first** — Operators use Mammoth; AICP is backend
3. **Fail-closed** — Unknown policy → deny
4. **Immutable audit** — Append-only, no updates/deletes
5. **Resumable sessions** — Survive restarts

---

*For deep-dive, see [docs/architecture/](docs/guides/)*