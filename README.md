<!--
  AICP - AI Capability Protocol
  Professional README inspired by PyTorch documentation
-->

<div align="center">

# AICP

### AI Capability Protocol

**_An AI-first application control plane that lets agents operate real apps_**
</div>

---

## What is AICP?

**AICP (AI Capability Protocol)** is a protocol and runtime model for turning applications into governed action spaces that AI agents can operate through structured capabilities, stateful workflows, policy enforcement, and human supervision.

Instead of humans clicking through apps, AICP turns applications into **structured action spaces** that AI agents can safely operate end-to-end.

AICP sits between:
1. **LLM / agent** — the "user" of the app
2. **Application capabilities** — structured, AI-safe actions
3. **Workflow engine** — multi-step orchestration
4. **State/session store** — resumable execution context
5. **Human approval layer** — governance, not friction
6. **UX plane** — monitoring, intervention, replay, debugging

The frontend is not "for humans to do the task." It is **"for humans to supervise the AI doing the task."**

> **Note:** AICP is the protocol and runtime model. The Python runtime in this repository is the reference implementation, not the full boundary of the architecture. See [STATUS.md](STATUS.md) for current implementation status.

---

## Why AICP?

| Traditional Tool Calling | AICP Agentic Experience |
|:----------------------:|:----------------------:|
| AI must infer what to do | AI gets explicit next steps |
| Errors are vague | Errors include `fix_hint` |
| AI tracks workflow manually | State is in every response |
| AI guesses if safe | Policy is explicit |
| No governance | Built-in approval workflows |

---

## Quick Start

### Available Today

```bash
# Install from source (or PyPI when published)
cd AICP
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi
```

```bash
# Bootstrap your app
aicp bootstrap fastapi server.main:app

# Scan capabilities from OpenAPI
aicp scan --openapi http://localhost:8000/openapi.json

# Preview a capability
aicp preview payments.transfer

# Add governance
aicp protect payments.transfer
aicp limit "users.*" --rpm 60

# Start the runtime
aicp dev

# Execute a capability (with inline approval prompt)
aicp run notes.create -i '{"title": "Hello"}'
aicp run notes.create -i '{"title": "Hello"}' --yes  # auto-approve
aicp run notes.create -i '{"title": "Hello"}' --no-input  # non-interactive
```

### Coming Next

- Richer workflow DSL (YAML/JSON)
- AI Planner and Judge integration
- LangChain / LangGraph adapters
- Event-driven async flows
- Visual workflow builder

See [STATUS.md](STATUS.md) for the full roadmap.

---

## Architecture Planes

| Plane | Purpose | Key Components |
|-------|---------|----------------|
| **Control Plane** | Registry, policy, orchestration | Capability registry, workflow registry, policy engine, approval service, execution orchestrator, session manager |
| **Data Plane** | Actual backend services | REST APIs, databases, external services |
| **AI Plane** | Agent reasoning | Planner, executor, judge, memory/context builder, tool selection layer |
| **UX Plane** | Human supervision | Operator dashboard, approval UI, replay debugger, workflow builder, audit logs |

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Action Surface** | Agent-facing surface of software — structured, typed, policy-governed actions |
| **Capability** | Governed action with strict I/O schema, side-effect classification, approval metadata, retry policy, error codes |
| **Workflow** | Stateful, resumable, multi-step process with branching, retries, approval checkpoints, compensation |
| **Policy** | Rules defining what is allowed, denied, or requires approval — evaluated per capability call |
| **Execution** | Capability invocation with result normalization, persistence, and audit |
| **Session** | Resumable execution context with state, memory, and approval history |
| **ApprovalRequest** | Governance checkpoint with risk assessment, impact summary, decision lifecycle |
| **AuditEntry** | Immutable record of every execution, policy evaluation, and approval event |

---

## Compliance Levels

Implementations declare their conformance level:

| Level | Name | Requirements |
|-------|------|-------------|
| **0** | Capability Discovery | Capability registry, input/output schema validation, basic execution |
| **1** | Governed Execution | Level 0 + policy evaluation, approval checkpoints, audit trail, session management |
| **2** | Resumable Workflows | Level 1 + sequential workflows, compensation, state persistence, resume after approval |
| **3** | Event-Driven Orchestration | Level 2 + wait-for-event, timeout branching, parallel steps, loops |
| **4** | AI Planning Support | Level 3 + planner, judge, context builder, allowed-next-actions schema |
| **5** | Full Orchestration | Level 4 + multi-flow orchestration, subflows, cross-flow events, supervision console |

**Current reference implementation: Level 2**

---

## Repository Structure

```
aicp/
├── spec/                     # Protocol source of truth (JSON schemas)
├── docs/                    # Documentation
│   ├── guides/             # How-to guides & tutorials
│   ├── overview/           # Product & concept docs
│   ├── handbook/           # Advanced topics
│   └── reference/          # API reference
├── packages/
│   ├── core/               # Protocol core (Python)
│   └── runtime/            # Execution runtime
├── adapters/
│   ├── protocol/           # HTTP, MCP, OpenAPI, GraphQL, mappers
│   ├── framework/          # FastAPI, Express, NestJS
│   └── importers/          # OpenAPI, Postman, HAR
├── sdks/                   # TypeScript SDK
├── mcp/                    # MCP Server
└── examples/              # Example applications
```

---

## Integrations

### FastAPI ✅ Available

```python
from fastapi import FastAPI
from aicp_connect_fastapi import mount_aicp

app = FastAPI()
mount_aicp(app)
```

### MCP ✅ Available

```bash
# MCP server implementation in /mcp/
```

### OpenAPI ✅ Available

```bash
aicp scan --openapi http://localhost:8000/openapi.json
```

### LangChain 🔜 Planned (illustrative, not yet shipped)

```python
# Planned integration — API shape subject to change
from langchain.tools import AicpTool

tool = AicpTool(capability_name="payments.transfer")
agent = Agent(tools=[tool])
```

### Express / NestJS / Next.js / Spring Boot 🔜 Planned

Adapter directories exist; implementations not yet started.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Getting Started](https://docs.aicp.ai/guides) | Installation & quick start |
| [How-To Guides](https://docs.aicp.ai/guides/HOW_TO_USE) | Complete usage guide |
| [Concepts](https://docs.aicp.ai/overview) | Architecture & design |
| [API Reference](https://docs.aicp.ai/reference) | Full API documentation |
| [Examples](https://github.com/aicp-ai/aicp/tree/main/examples) | Runnable examples |

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/aicp-ai/aicp/blob/main/governance/CONTRIBUTING.md) for details.

- 📖 [Code of Conduct](https://github.com/aicp-ai/aicp/blob/main/governance/CODE_OF_CONDUCT.md)
- 🐛 [Issue Tracker](https://github.com/aicp-ai/aicp/issues)

---

## License

<p align="center">
  <a href="https://github.com/aicp-ai/aicp/blob/main/LICENSE">
    <img src="https://img.shields.io/pypi/l/aicp-core?color=orange&style=for-the-badge" alt="License: Apache 2.0">
  </a>
</p>

AICP is licensed under the [Apache 2.0 License](https://github.com/aicp-ai/aicp/blob/main/LICENSE).

---

<p align="center">
  <strong>Built for agents. Governed by design.</strong>
</p>
