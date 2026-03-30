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

## Quick Start

### Installation

```bash
# Core package
pip install aicp-core

# With all features
pip install aicp-core[all]

# Development version
pip install git+https://github.com/aicp-ai/aicp.git
```

### Your First Capability

```python
from aicp import (
    Capability,
    CapabilityKind,
    AicpExecutor,
    InMemoryCapabilityRepository,
)

# 1. Define a capability
transfer = Capability(
    name="payments.transfer",
    description="Transfer funds between accounts",
    kind=CapabilityKind.ACTION,
    input_schema={
        "type": "object",
        "properties": {
            "from_account": {"type": "string"},
            "to_account": {"type": "string"},
            "amount": {"type": "number"}
        },
        "required": ["from_account", "to_account", "amount"]
    },
    tags=["finance", "payments"],
)

# 2. Register it
repo = InMemoryCapabilityRepository()
repo.register(transfer)

# 3. Execute
executor = AicpExecutor(repo)
result = await executor.execute("payments.transfer", {
    "from_account": "acc_123",
    "to_account": "acc_456",
    "amount": 100.00
})

print(result.status)           # "success"
print(result.data)             # {"transfer_id": "txn_789", ...}
print(result.next)             # {"action": "complete", "hint": None}
```

### With Policy Governance

```python
from aicp import Policy, PolicyCondition, PolicyEffect

# Require approval for transfers over $10,000
policy = Policy(
    name="transfer-approval",
    effect=PolicyEffect.ASK,
    condition=PolicyCondition(
        field="arguments.amount",
        operator=">",
        value=10000,
    ),
    reason="Transfers over $10,000 require manager approval",
)

# Add to executor
executor = AicpExecutor(repo, policy_engine)
result = await executor.execute("payments.transfer", {...})

# If amount > 10000, returns approval-required response:
# {
#   "status": "failure",
#   "error_code": "requires_confirmation",
#   "next": {"action": "confirm", "hint": "..."}
# }
```

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
