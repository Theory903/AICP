<!--
  AICP Core - Professional Package README
-->

<div align="center">

# AICP Core

### Python Implementation of the AI Capability Protocol
</div>

---

## Overview

**AICP Core** provides the foundational types, interfaces, and implementations for the AI Capability Protocol. It includes:

- 📦 **Capability models** — Typed definitions for actions, queries, workflows
- ⚙️ **Executor** — Policy-aware execution with result normalization
- 🗂️ **Registry** — Capability discovery and tag-based search
- 🛡️ **Policy engine** — Allow/deny/confirmation evaluation
- 🔄 **Workflow runtime** — Multi-step execution with state management

---

## Installation

```bash
pip install aicp-core
```

### With Optional Dependencies

```bash
# Full dependencies
pip install aicp-core[all]

# Individual extras
pip install aicp-core[fastapi]    # FastAPI adapter
pip install aicp-core[redis]      # Redis caching
pip install aicp-core[prometheus]  # Metrics
pip install aicp-core[vault]       # HashiCorp Vault secrets
pip install aicp-core[aws]         # AWS Secrets Manager
```

---

## Core Concepts

### Capability

The fundamental unit of AICP — a meaningful action with typed inputs/outputs:

```python
from aicp import Capability, CapabilityKind

cap = Capability(
    name="payments.transfer",
    description="Transfer funds between accounts",
    kind=CapabilityKind.ACTION,
    input_schema={...},
    output_schema={...},
    tags=["finance", "payments"],
)
```

### Executor

Policy-aware execution with normalized results:

```python
from aicp import AicpExecutor

executor = AicpExecutor(capability_provider, policy_engine)
result = await executor.execute("tool.name", {"arg": "value"})
```

### Registry & Search

Tag-based capability discovery:

```python
from aicp import AicpRegistry

registry = AicpRegistry()
registry.register_capability(cap)

results = registry.search_capabilities(
    query="payment",
    tags=["finance"],
    limit=10,
)
```

---

## Complete Example

```python
import asyncio
from aicp import (
    Capability,
    CapabilityKind,
    AicpExecutor,
    InMemoryCapabilityRepository,
)

# 1. Define capabilities
transfer = Capability(
    name="payments.transfer",
    description="Transfer funds between accounts",
    kind=CapabilityKind.ACTION,
    tags=["finance"],
)

list_transactions = Capability(
    name="payments.list",
    description="List all transactions",
    kind=CapabilityKind.QUERY,
    tags=["finance", "read"],
)

# 2. Register
repo = InMemoryCapabilityRepository()
repo.register(transfer)
repo.register(list_transactions)

# 3. Execute
async def main():
    executor = AicpExecutor(repo)
    
    # Query
    result = await executor.execute("payments.list", {})
    print(result.status)  # "success"
    
    # Action
    result = await executor.execute("payments.transfer", {
        "from": "acc_123",
        "to": "acc_456", 
        "amount": 100
    })
    print(result.status)  # "success"

asyncio.run(main())
```

---

## API Reference

| Module | Description |
|--------|-------------|
| `aicp.capability` | Capability models and kinds |
| `aicp.executor` | Execution engine |
| `aicp.registry` | Capability registry & search |
| `aicp.policy` | Policy definitions & engine |
| `aicp.workflow` | Workflow runtime |
| `aicp.auth` | Authentication (API Key, OAuth2, etc.) |
| `aicp.security` | Rate limiting, audit signing |
| `aicp.tenancy` | Multi-tenant isolation |
| `aicp.reliability` | Retry, circuit breaker |
| `aicp.observability` | Logging, metrics, tracing |
| `aicp.notifications` | Webhooks, Slack, Email |
| `aicp.secrets` | Secrets management |
| `aicp.cache` | Redis caching |
| `aicp.plugins` | Plugin system |

---

## Development

```bash
# Clone and install
git clone https://github.com/aicp-ai/aicp.git
cd aicp/packages/core

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
ruff format .
```

---

## License

Apache 2.0 - See [LICENSE](https://github.com/aicp-ai/aicp/blob/main/LICENSE)
