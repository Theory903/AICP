# AGENTS.md — AICP Development Guide

> **Version:** 0.9.10 | **Last updated:** 2026-04-06

This file provides guidance to AI coding agents working in the AICP repository.

---

## 1. Project Overview

**AICP (AI Capability Protocol)** is the control plane for secure agentic and organizational automation.

**Current version:** 0.9.10 — SDKs, Platforms, and Integrations

**Current product framing:**
- **AICP** provides the governed backend: capabilities, workflows, policy, approvals, sessions, audit, discovery, and execution contracts.
- **Mammoth** is the primary interaction shell (Rust TUI).
- **Studio** should be treated as embedded into Mammoth, not as a separate app.

---

## 2. Architecture: 11 Planes

| # | Plane | Purpose |
|---|-------|---------|
| 0 | Signal | Event ingestion, routing |
| 1 | Perception | a11y tree, DOM, screenshots |
| 2 | AI | Planner, judge, memory |
| 3 | Capability | Registry, schema, discovery |
| 4 | Workflow | Sequential, parallel, loops, subflows |
| 5 | Governance | Policy, trust tiers, approvals |
| 6 | Execution | Realtime, transactional, event-driven |
| 7 | Multi-Agent | Orchestrator/specialist/worker |
| 8 | Federation | CRDT, DID, cross-org |
| 9 | Supervision | Approval queue, replay |
| 10 | Learning | Skill mining, drift detection |

---

## 3. The 20 Modules

| # | Module | Plane | Status |
|---|--------|-------|--------|
| 1 | Principal and Org Control | Governance | ✅ Complete |
| 2 | Identity and Trust | Governance | ✅ Complete |
| 3 | Capability Registry | Capability | ✅ Complete |
| 4 | Tool Runtime | Execution | ✅ Complete |
| 5 | Workflow Engine | Workflow | ✅ Complete |
| 6 | Perception/Signal | Perception | ✅ Complete |
| 7 | Human Cognitive Protocols | Supervision | ✅ Complete |
| 8 | AI Plane | AI | ✅ Complete |
| 9 | Memory System | AI | ✅ Complete |
| 10 | Code Intelligence DB | AI | ✅ Complete |
| 11 | Discovery Engine | Capability | ✅ Complete |
| 12 | Governance/Policy | Governance | ✅ Complete |
| 13 | Execution Engine | Execution | ✅ Complete |
| 14 | Multi-Agent Hierarchy | Multi-Agent | ✅ Complete |
| 15 | Agent Communication Bus | Multi-Agent | ✅ Complete |
| 16 | Federation | Federation | ✅ Complete |
| 17 | Human Web Compatibility | Perception | ✅ Complete |
| 18 | Audit/Replay | Supervision | ✅ Complete |
| 19 | Learning | Learning | ✅ Complete |
| 20 | Domain Packs | Learning | ✅ Complete |

---

## 4. Build Commands

### Python (packages/*, sdks/python)

```bash
# Install all packages
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli

# Run tests
pytest packages/core/tests/ -v
pytest packages/runtime/tests/ -v

# Run all Python tests
pytest packages/ -v

# Lint
ruff check . && ruff format --check .

# Type check
ruff check --select=typecheck .
```

### Rust (apps/mammoth)

```bash
cd apps/mammoth

# Build
cargo build -p mammoth-cli

# Run
cargo run -p mammoth-cli -- --help

# Test (individual crates)
cargo test -p mammoth-runtime --lib
cargo test -p api --lib
cargo test -p commands --lib
```

### TypeScript (sdks/typescript)

```bash
cd sdks/typescript/packages/core
npm install && npm run build
```

---

## 5. Test Counts

| Suite | Count |
|-------|-------|
| Python (core + runtime + cli) | 1038 |
| Rust (mammoth) | 186 |
| **Total** | **1224** |

---

## 6. Coding Standards

### Python

- Follow PEP 8
- Use type hints everywhere
- Use `Optional[X]` over `X | None`
- No `as any`, `@ts-ignore`, empty catch blocks
- Custom exceptions inheriting from `AicpError`

### TypeScript

- Follow Google TypeScript Style Guide
- Use explicit return types for public functions
- Use interfaces over type aliases for objects

---

## 7. Spec-First Development

**Critical rule:** `/spec` is the source of truth. If runtime behavior and spec disagree, spec wins.

When adding new functionality:
1. Define schema in `/spec/schemas/<name>.schema.json`
2. Add valid/invalid examples in `/spec/examples/`
3. Add conformance tests in `/spec/tests/`
4. Implement in `packages/core` or `packages/runtime`
5. Add tests in `packages/*/tests/`

---

## 8. Key Files Reference

| Path | Purpose |
|------|---------|
| `spec/schemas/*.schema.json` | Protocol schemas |
| `packages/core/src/aicp/` | Domain models |
| `packages/runtime/src/aicp_runtime/` | Execution services |
| `packages/cli/src/aicp_cli/` | CLI commands |
| `adapters/framework/` | Framework adapters |
| `adapters/protocol/` | Protocol adapters |
| `apps/mammoth/` | Rust TUI shell |

---

## 9. Important Notes for Agents

### Never Do

- Never suppress type errors (`as any`, `@ts-ignore`)
- Never swallow exceptions silently (empty catch blocks)
- Never bypass policy evaluation for side-effecting capabilities
- Never commit without verification

### Always Do

- Always run tests after changes
- Always update schemas in `/spec` before code
- Always add tests for new features (min 3)
- Always verify build/lint before claiming completion

---

## 10. Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.1-alpha | 2025 | Foundation |
| 0.3.0 | 2026-04-03 | Orchestration |
| 0.4.0 | 2026-04-04 | Agent Integration |
| 0.9.9 | 2026-04-05 | Production features |
| **0.9.10** | **2026-04-06** | **SDKs, Platforms, Integrations** |

---

*For more, see [README.md](README.md), [STATUS.md](STATUS.md), [ROADMAP.md](ROADMAP.md)*