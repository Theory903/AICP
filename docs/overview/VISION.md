# AICP + Mammoth Vision

Two operating systems. One stack.

---

## The Thesis

Software has three native surfaces:

| Surface | Optimized For | Primary Consumer |
|---------|---------------|-----------------|
| API | Developer integration | Backend services |
| UI | Human interaction | End users |
| **Action Surface** | **Agent operation** | **AI agents** |

AICP defines the third surface. Mammoth is the first-class interface to it.

---

## Two Operating Systems, One Stack

| OS | Name | Role |
|----|------|------|
| **Interaction OS** | Mammoth | Every way a human or agent touches the system — terminal REPL, web console, CLI, Chrome extension |
| **Execution OS** | AICP | Every execution — policy evaluation, workflow orchestration, approval gating, audit, session management |

Neither is complete without the other. Mammoth without AICP is a chatbot. AICP without Mammoth is an API that nobody can see.

---

## Mammoth: The Interaction OS

Mammoth is not a UI. It is the **interaction layer** — the unified, omni-channel surface through which humans and agents issue intent, observe execution, and supervise outcomes.

### Four Channels

| Channel | Description | Entry Point |
|---------|-------------|-------------|
| **Terminal** | Conversational REPL — full-capability, keyboard-driven, streaming | `mammoth` |
| **Web** | Studio console + conversational interface — approvals, audit, workflow replay | `mammoth serve` |
| **CLI** | Multi-channel dispatcher and programmatic interface | `mammoth <subcommand>` |
| **Extension** | Chrome MV3 — page-aware agent overlay with AICP-backed execution | `mammoth ext` |

Every channel is a different rendering surface for the same underlying thing: a governed, stateful, policy-evaluated agent session backed by AICP.

### What Mammoth Is Not

- Not an LLM provider
- Not an AI model
- Not a standalone chatbot
- Not a thin wrapper around Claude/GPT

Mammoth is the **interaction OS**. It routes user intent through AICP before any AI model sees it, and renders AICP's governed execution envelope back to the user.

---

## AICP: The Execution OS

AICP is the protocol and runtime that governs every action Mammoth takes.

```
Mammoth Channel (terminal / web / cli / extension)
    ↓ user intent / tool calls
AICP Execution Layer
    (policy eval, audit, approval gating, session, allowed_next_actions)
    ↓ governed AI requests
Provider Registry
    (Anthropic, OpenAI, Gemini, Ollama, OpenRouter, Groq, Mistral, xAI)
    ↓
AI Model Response
    ↑
AICP wraps response in ExecutionEnvelope
    ↑
Mammoth renders to user via appropriate channel
```

### What AICP Solves

| Failure | Symptom | AICP Solution |
|---------|---------|---------------|
| **Governance gap** | No policy, no approval, no audit | Protocol-native policy engine with trust tiers, risk scoring, approval lifecycle |
| **State gap** | No workflow memory, no resumable execution | Stateful workflows with persistence, compensation, and resume-after-approval |
| **Signal gap** | Weak errors, no repair hints, no next-step guidance | Structured execution envelopes with `allowed_next_actions`, `fix_hint`, error taxonomy |

### Architecture: 11 Planes

AICP is organized into 11 architectural planes:

| # | Plane | Purpose |
|---|-------|---------|
| 0 | Signal | Sub-ms event ingestion, dedup, classification, routing |
| 1 | Perception | a11y tree, DOM observation, screenshots, behavioral signals |
| 2 | AI | Planner, judge, intent router, memory, cognitive protocols |
| 3 | Capability | Registry, schema validation, ranked discovery, semantic search |
| 4 | Workflow | Sequential, parallel, fork/join, sagas, event-driven, subflows |
| 5 | Governance | Compiled policy engine, trust tiers, risk scoring, approval lifecycle |
| 6 | Execution | Realtime (<5ms), transactional (saga), event-driven (wait/resume) |
| 7 | Multi-Agent | Orchestrator/specialist/worker/supervisor hierarchy, communication bus |
| 8 | Federation | `/.well-known/aicp` discovery, CRDT registries, DID auth |
| 9 | Supervision | Live feed, approval queue, replay debugger, policy editor |
| 10 | Learning | Skill mining, policy learning, drift detection, autonomy calibration |

---

## Product Stack

| Layer | Name | Purpose |
|-------|------|---------|
| **Interaction OS** | **Mammoth** | The unified interaction layer — terminal, web, CLI, extension |
| Protocol | AICP Protocol | The open contract — JSON schemas, capability kinds, execution envelope, compliance levels |
| Runtime | AICP Runtime | The execution engine — policy evaluation, workflow orchestration, persistence, session management |
| Connect | AICP Connect | The adoption wedge — adapters for HTTP, MCP, OpenAPI, FastAPI, cURL, HAR, Postman, LangChain |

> **Note:** `apps/studio/` is superseded by Mammoth's Web channel. Mammoth Web is the supervision console.

---

## Design Principles

| Principle | Meaning |
|-----------|---------|
| **Mammoth is the interaction OS** | Every human and agent interaction goes through Mammoth channels |
| **AICP is the execution OS** | No side effect executes without AICP policy evaluation |
| Governance is protocol-native | Not middleware, not afterthought — policy evaluation happens before every side effect |
| Execution is stateful | Every workflow is resumable across process restarts, approval pauses, and failures |
| Errors are actionable | Every failure includes structured codes, fix hints, and retry guidance |
| Signals are structured | Every execution produces the canonical envelope consumed by planner, judge, UI, and audit |
| Adoption is incremental | Zero-code onramp via `aicp scan` and `aicp dev` on existing FastAPI apps |
| Spec is source of truth | If runtime behavior and schema disagree, schema wins |
| Adapters translate only | No business logic in adapters — they map between AICP and external protocols |

---

## Adoption Path

### For Operators (Mammoth users)

```
mammoth           # terminal channel — full REPL
mammoth serve     # web channel — Studio + conversational UI at localhost:3000
mammoth ext       # extension channel — Chrome overlay bridge
```

### For Developers (AICP integration)

```
OpenAPI spec  ---->  aicp map openapi api.json         ---->  Governed capabilities
FastAPI app   ---->  aicp scan fastapi app:app          ---->  Governed capabilities
Postman       ---->  aicp map postman collection.json   ---->  Governed capabilities
HAR file      ---->  aicp map har session.har           ---->  Governed capabilities
cURL command  ---->  aicp map curl "curl ..."           ---->  Governed capabilities
MCP server    ---->  MCP adapter auto-discovery         ---->  Governed capabilities
```

---

## Current State

**v0.3.0 feature set** — Complete L3 orchestration plus shipped L4 AI planning components. See [STATUS.md](../../STATUS.md) for the full inventory.

Mammoth: L1 complete (AICP middleware layer in `crates/aicp/`). Terminal channel operational. Web channel skeleton exists (`crates/server/`). Extension channel planned.

## Target State

**v1.0.0** — Compliance Level 5 (Protocol Ready). 16 JSON schemas complete. 9 modules fully implemented, 6 with protocol+stub interfaces. Multi-agent coordination, federation, perception, learning schemas ready. See [ROADMAP.md](../../ROADMAP.md) for the phased build order.

---

## The Long-Term Outcome

If this stack succeeds, every application on the internet exposes three surfaces:

- **APIs** for developers
- **UIs** for humans
- **AICP Action Surfaces** for agents

And every agent-operable application is reachable through Mammoth — the interaction OS that makes those surfaces visible.

---

## See Also

- [MAMMOTH.md](../guides/MAMMOTH.md) — Mammoth architecture (4 channels, channel trait, extension protocol)
- [ACTION_SURFACE.md](ACTION_SURFACE.md) — The agent-facing surface of software
- [GOVERNANCE.md](GOVERNANCE.md) — Policy, trust, and approval
- [COMPARISON.md](COMPARISON.md) — AICP vs MCP, OpenAPI, tool calling, Claude Code, Cursor
- [ARCHITECTURE.md](../guides/ARCHITECTURE.md) — 11-plane system architecture
- [STATUS.md](../../STATUS.md) — Current implementation state
- [ROADMAP.md](../../ROADMAP.md) — Phased roadmap to v1.0.0
