<!--
  AICP - AI Capability Protocol
  Professional README inspired by PyTorch documentation
-->

<div align="center">

# AICP

### AI Capability Protocol

**_The governed action runtime for AI agents_**
</div>

---

## What is AICP?

**AICP (AI Capability Protocol)** is a standard for **capability-aware**, **workflow-aware**, and **policy-aware** AI execution. It transforms APIs, applications, and workflows into **discoverable**, **policy-enforced**, and **stateful capabilities** that AI agents can use safely in production.

AICP is designed so **even small language models** can complete real-world tasks without complex reasoning. Every response tells the AI:

- ✅ **What happened** — explicit execution status
- ✅ **What went wrong** — structured errors with fix hints  
- ✅ **What to do next** — built-in next action suggestions
- ✅ **Where we are** — workflow state tracking
- ✅ **If it's safe to proceed** — explicit policy evaluation

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

## Features

### 🤖 Agentic Execution
- **Agentic-ready responses** — Every response includes `next` with suggested actions
- **Built-in fix hints** — Errors tell AI exactly how to recover
- **Workflow state** — Track multi-step processes automatically

### 🛡️ Governance & Policy
- **Policy evaluation** — Enforce allow/deny/confirmation rules
- **Human-in-the-loop** — Approval workflows for sensitive operations
- **Audit logging** — Complete execution history with cryptographic signing

### 🔌 Multi-Protocol Support
- HTTP / HTTPS
- WebSocket (real-time streaming)
- SSE (Server-Sent Events)
- GraphQL
- MCP (Model Context Protocol)
- OpenAPI / Swagger import
- Postman / HAR / cURL import

### 🏢 Production-Ready
- **Multi-tenancy** — Tenant isolation with quotas
- **Rate limiting** — Per-tenant and per-endpoint limits
- **OAuth2** — Full authN/authZ support
- **Secrets management** — Vault, AWS Secrets Manager integration

### 📊 Observability
- Structured JSON logging
- Prometheus metrics
- Distributed tracing
- Health checks & liveness probes

### ⚡ Reliability
- Retry with exponential backoff
- Circuit breaker pattern
- Graceful shutdown

---

## Quick Start (3-Minutes)

Get your existing application fully AI-ready without writing complex wrapper code. AICP's CLI scans your app, exports governing schemas, and starts a managed capability runtime.

### 1. Installation

```bash
# Install the core runtime, visual CLI, and your framework adapter
pip install "aicp-core[all]" aicp-cli aicp-connect-fastapi
```

### 2. Bootstrap Your App

Use `aicp bootstrap` to instantly scaffold an AICP configuration for an existing application.

```bash
> aicp bootstrap fastapi server.main:app

🚀 Bootstrapping AICP for server.main:app

  ✓ Initialized local AICP environment
  ✓ Scanned 12 Capabilities from routes
  ✓ Extracted input/output schemas & types
  ✓ Auto-detected destructive risk levels
  
✨ Bootstrap complete! Your project is AICP-ready.
```

Every endpoint is converted into a fully documented, governing standard output in `aicp/capabilities/`.

### 3. Review & Govern Capabilities

Inspect a specific capability in the terminal to view its full prompt and enforcement rules—no staring at YAML required.

```bash
> aicp preview payments.transfer

💳 Capability: payments.transfer
─────────────────────────────────
Kind: Action  |  Risk: Critical
Tags: [finance, destructive]

Governing Policy:
  ↳ Effect: requires_approval
  ↳ Reason: "Destructive operations must have Human-in-the-loop sign-off"
```

Is a sensitive action unprotected? Add governance directly from the CLI.

```bash
# Force any AI calling this tool to pause and wait for a human approval hook
aicp protect payments.transfer

# Apply a global rate limit across the entire users module
aicp limit "users.*" --rpm 60
```

### 4. Start the Runtime

```bash
aicp dev
```
The AICP engine mounts securely over your app! Your Agents can now dynamically execute tasks, safely halt for required approvals, and understand exact error states instantly.

---

## Architecture

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
│   ├── protocol/           # HTTP, WS, SSE, GraphQL, MCP
│   ├── framework/          # FastAPI, Express, LangChain
│   └── importers/          # OpenAPI, Postman, HAR
├── sdks/                   # TypeScript SDK
├── mcp/                    # MCP Server
└── examples/              # Example applications
```

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

## Integrations

### FastAPI
```python
from fastapi import FastAPI
from aicp.adapters.framework.fastapi import mount_aicp

app = FastAPI()
mount_aicp(app, capabilities=[...])
```

### LangChain
```python
from langchain.tools import AicpTool

tool = AicpTool(capability_name="payments.transfer")
agent = Agent(tools=[tool])
```

### MCP Server
```bash
npx @aicp/mcp-server --capabilities payments.transfer,users.list
```

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
