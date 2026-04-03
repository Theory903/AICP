# Guides

> Step-by-step guides for using and contributing to AICP — the Agentic Web Operating System.

---

## Getting Started

1. **Installation**
   ```bash
   pip install -e ./packages/core
   ```

2. **Quick Start**
   - Register a capability
   - Execute it via the executor

3. **Run an Example**
   ```bash
   make demo-food
   ```

4. **Run the current platform stack**
   - [Run Runtime + Studio](RUN_RUNTIME_STUDIO.md)

---

## Core Guides

| Guide | Description |
|-------|-------------|
| [Architecture](ARCHITECTURE.md) | Technical architecture for contributors — 11 planes, 20 modules |
| [How to Use AICP](HOW_TO_USE.md) | Complete usage reference — CLI, programmatic API, production patterns |
| [CLI Reference](CLI_REFERENCE.md) | 28 CLI commands — bootstrap, preview, protect, serve, etc. |
| [Runtime and Studio](RUN_RUNTIME_STUDIO.md) | Running the runtime, CLI, and Studio locally |
| [Technical Specification](TECH_SPEC.md) | Protocol technical specification — data models, contracts |

---

## Adapters

| Adapter | Description |
|----------|-------------|
| **FastAPI** | Auto-discover routes from FastAPI apps |
| **HTTP** | Execute capabilities over HTTP |
| **OpenAPI** | Import OpenAPI specs as governed capabilities |
| **MCP** | Bridge to MCP servers (Model Context Protocol) |
| **Postman** | Import Postman collections |
| **HAR** | Import HTTP Archives |
| **cURL** | Import cURL commands |
| **WebSocket** | Real-time streaming execution (planned) |
| **GraphQL** | GraphQL-based execution (planned) |

---

## What Is Implemented (v0.1.1)

- 9 JSON schemas in `/spec/schemas/`
- 8 runtime services (execution, approvals, workflows, sessions, discovery, audit, interactions, provider health)
- 30+ API endpoints across 13 route groups
- 3 persistence backends (memory, file, sqlite)
- 28 CLI commands
- 6 working adapters
- 172 passing tests
- Agent console UI at `/console`
- TypeScript Core SDK built

---

## What Is Planned (v0.2.0+)

- YAML Workflow DSL
- Parallel workflow steps and loop support
- Wait-for-event primitives and timeout branching
- AI Planner and Judge integration
- Semantic capability discovery with embeddings
- Session encryption
- LangChain and LangGraph adapters

---

## See Also

- [/overview/index.md](../overview/index.md) — Overview documents
- [/ARCHITECTURE.md](../../ARCHITECTURE.md) — 11-plane system architecture
- [/STATUS.md](../../STATUS.md) — Current implementation state
- [/governance/CONTRIBUTING.md](../../governance/CONTRIBUTING.md) — How to contribute