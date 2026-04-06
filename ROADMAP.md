# AICP Roadmap

> **Version:** 0.9.10 | **Target:** 1.0.0
> **Last updated:** 2026-04-06

---

## Guiding Principles

1. **Spec before code.** Protocol changes are documented in `/spec` before runtime implementation.
2. **Layers, not chaos.** Each phase delivers a complete, testable capability layer.
3. **Compliance is cumulative.** Each compliance level subsumes all lower levels.
4. **Honest status.** No phase is marked complete without passing tests.
5. **Backward compatibility.** Breaking changes require a version bump.
6. **Mammoth-first.** Operators interact through Mammoth; AICP is the backend.
7. **Studio is embedded.** Supervision UX converges into Mammoth.

---

## Version Map

| Phase | Version | Focus | Compliance | Status |
|-------|---------|-------|------------|--------|
| 0 | 0.1.1-alpha | Foundation | L2 | ✅ Complete |
| 1 | 0.2.0 | AI Core | L4 | ✅ Complete |
| 2 | 0.3.0 | Orchestration | L3+L4 | ✅ Complete |
| 3 | 0.4.0 | Agent Integration | L4 | ✅ Complete |
| 4 | 0.7.0 | Enterprise | L5 | ✅ Complete |
| 5 | 0.8.0 | Federation | L5 | ✅ Complete |
| 6 | 0.9.0 | Production | L5 | ✅ Complete |
| **Current** | **0.9.10** | **SDKs & Integrations** | **L5** | **✅ Complete** |
| Next | 1.0.0 | Agentic Web OS | L5 | Planned |

---

## Phase Roadmap

### Phase 0: Foundation (v0.1.1-alpha) — ✅ COMPLETE

- Capability registry with schema validation
- Session management with persistence
- Basic policy engine

### Phase 1: AI Core (v0.2.0) — ✅ COMPLETE

- Natural language intent routing
- Multi-model provider support
- Context budget management
- Memory system (working, episodic, semantic)

### Phase 2: Orchestration (v0.3.0) — ✅ COMPLETE

- Sequential workflows with approval checkpoints
- Parallel execution (fork/join)
- Event-driven flows (wait/resume)
- Loops (for-each, while, do-while)
- Subflow invocation

### Phase 3: Agent Integration (v0.4.0) — ✅ COMPLETE

- LangChain adapter
- LangGraph adapter
- CrewAI adapter
- MCP server (exposes AICP)
- MCP adapter (consumes external tools)

### Phase 4: Enterprise (v0.7.0) — ✅ COMPLETE

- Multi-tenant isolation
- Audit/replay system
- Approval lifecycle with blast radius
- Trust tiers (0-4)
- Plugin system with sandbox

### Phase 5: Federation (v0.8.0) — ✅ COMPLETE

- `/.well-known/aicp` discovery
- CRDT registries
- DID authentication
- Cross-org capability sharing

### Phase 6: Learning (v0.8.0) — ✅ COMPLETE

- Skill mining from execution logs
- Drift detection
- Autonomy calibration
- Domain packs

### Phase 7: Production (v0.9.x) — ✅ COMPLETE

- SSRF protection
- OpenAI-compatible API (`/v1/chat/completions`)
- DEK credential encryption
- 4-canonical MCP tools
- Web search (Brave, DuckDuckGo, Exa)
- Browser control (Playwright/CDP)
- Scheduler (cron)
- Session compaction
- Docker sandboxing

### Phase 8: SDKs & Platforms (v0.9.10) — ✅ COMPLETE

- **Python SDK** — Full client with all APIs
- **TypeScript SDK** — Core + Runtime + Client packages
- **VS Code Extension** — MammothPanel, GhostTextProvider, ApprovalForwarder
- **macOS Menu Bar** — SwiftUI app
- **Mobile** — Flutter app

### Phase 9: Integrations (v0.9.10) — ✅ COMPLETE

- **GitHub** — Issues, PRs, commits
- **Linear** — Issues, teams
- **Gmail** — Read/send email

---

## Coming Next (v1.0.0)

### Platform Extensions

- [ ] Full VS Code IDE bridge (not just skeleton)
- [ ] Real backend for macOS Menu Bar
- [ ] Real backend for Mobile app
- [ ] Browser extension

### More Integrations

- [ ] Notion
- [ ] Salesforce
- [ ] Stripe
- [ ] Jira
- [ ] Slack (full)

### Polish

- [ ] `often_follows` enforcement semantics
- [ ] Performance optimization
- [ ] More comprehensive test coverage
- [ ] Documentation polish

---

## Release Cadence

| Version | Frequency | Content |
|---------|------------|---------|
| 0.9.x | Monthly | Features, integrations |
| 1.0.x | Quarterly | Major releases |

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.1-alpha | 2025 | Foundation |
| 0.2.0 | 2025 | AI Core |
| 0.3.0 | 2026-04-03 | Orchestration |
| 0.4.0 | 2026-04-04 | Agent Integration |
| 0.7.0 | 2026-04-04 | Enterprise |
| 0.8.0 | 2026-04-04 | Federation + Learning |
| 0.9.9 | 2026-04-05 | Production features |
| **0.9.10** | **2026-04-06** | **SDKs, Platforms, Integrations** |

---

## Contributing

See [CONTRIBUTING.md](governance/CONTRIBUTING.md) for how to contribute.

---

*Last updated: 2026-04-06*