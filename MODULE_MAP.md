# Module Map — Feature-to-Module Mapping

> **Version:** 0.9.10 | **Last updated:** 2026-04-06

This document maps control-plane responsibilities to their owning modules.

---

## Module Index

| # | Module | Plane | Package | Status |
|---|--------|-------|---------|--------|
| 1 | Principal and Org Control | Governance | `packages/core` | ✅ |
| 2 | Identity and Trust | Governance | `packages/runtime` | ✅ |
| 3 | Capability Registry | Capability | `packages/core` + `packages/runtime` | ✅ |
| 4 | Tool Runtime | Execution | `packages/runtime` | ✅ |
| 5 | Workflow Engine | Workflow | `packages/runtime` | ✅ |
| 6 | Perception and Signal Layer | Perception/Signal | `packages/core` | ✅ |
| 7 | Human Cognitive Protocols | Supervision | `packages/runtime` | ✅ |
| 8 | AI Plane | AI | `packages/runtime` | ✅ |
| 9 | Memory System | AI | `packages/runtime` | ✅ |
| 10 | Code Intelligence DB | AI | `packages/core` | ✅ |
| 11 | Discovery Engine | Capability | `packages/runtime` | ✅ |
| 12 | Governance and Policy | Governance | `packages/core` | ✅ |
| 13 | Execution Engine | Execution | `packages/runtime` | ✅ |
| 14 | Multi-Agent Hierarchy | Multi-Agent | `packages/core` | ✅ |
| 15 | Agent Communication Bus | Multi-Agent | `packages/core` | ✅ |
| 16 | Federation | Federation | `packages/core` | ✅ |
| 17 | Human Web Compatibility | Perception | `packages/core` | ✅ |
| 18 | Audit/Replay/Observability | Supervision | `packages/runtime` | ✅ |
| 19 | Learning System | Learning | `packages/core` | ✅ |
| 20 | Domain Packs | Learning | `packages/core` | ✅ |

---

## Feature Mapping

### Capability & Execution

| Feature | Module | Files |
|---------|--------|-------|
| Capability Registry | #3 | `core/src/aicp/capability/` |
| Schema Validation | #3 | `core/src/aicp/validation/` |
| Capability Execution | #4 | `runtime/src/aicp_runtime/services/execution.py` |
| Capability Discovery | #11 | `runtime/src/aicp_runtime/services/discovery.py` |

### Workflow

| Feature | Module | Files |
|---------|--------|-------|
| Sequential Steps | #5 | `runtime/src/aicp_runtime/services/workflow.py` |
| Parallel Execution | #5 | `runtime/src/aicp_runtime/services/workflow.py` |
| Loops | #5 | `runtime/src/aicp_runtime/services/workflow.py` |
| Subflows | #5 | `runtime/src/aicp_runtime/services/workflow.py` |
| Event-Driven | #5 | `runtime/src/aicp_runtime/services/workflow.py` |

### Governance

| Feature | Module | Files |
|---------|--------|-------|
| Policy Engine | #12 | `core/src/aicp/policy/` |
| Trust Tiers | #12 | `core/src/aicp/trust.py` |
| Approval Lifecycle | #7 | `runtime/src/aicp_runtime/services/approval.py` |
| Audit Trail | #18 | `runtime/src/aicp_runtime/services/audit.py` |

### Multi-Agent

| Feature | Module | Files |
|---------|--------|-------|
| Orchestrator | #14 | `core/src/aicp/multi_agent/` |
| Specialist | #14 | `core/src/aicp/multi_agent/` |
| Worker | #14 | `core/src/aicp/multi_agent/` |
| Communication Bus | #15 | `core/src/aicp/multi_agent/` |

### Platform Apps

| Feature | Module | Files |
|---------|--------|-------|
| VS Code Extension | — | `apps/mammoth/vscode-extension/` |
| macOS Menu Bar | — | `apps/mammoth/macos-menu-bar/` |
| Mobile | — | `apps/mammoth/mobile/` |

### Integrations

| Feature | Module | Files |
|---------|--------|-------|
| GitHub | — | `core/src/aicp/plugins/integrations/github.py` |
| Linear | — | `core/src/aicp/plugins/integrations/linear.py` |
| Gmail | — | `core/src/aicp/plugins/integrations/gmail.py` |
| FastAPI | — | `adapters/framework/fastapi/` |
| Express | — | `adapters/framework/express/` |
| NestJS | — | `adapters/framework/nestjs/` |
| LangChain | — | `adapters/agent/langchain/` |
| LangGraph | — | `adapters/agent/langgraph/` |
| CrewAI | — | `adapters/agent/crewai/` |
| MCP Server | — | `mcp/` |
| MCP Adapter | — | `adapters/protocol/mcp/` |

---

## SDKs

| SDK | Location | Status |
|-----|----------|--------|
| Python | `sdks/python/` | ✅ Complete |
| TypeScript Core | `sdks/typescript/packages/core/` | ✅ Complete |
| TypeScript Runtime | `sdks/typescript/packages/runtime/` | ✅ Complete |
| TypeScript Client | `sdks/typescript/packages/client/` | ✅ Complete |

---

*Last updated: 2026-04-06*
