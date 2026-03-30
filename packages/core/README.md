<!--
  AICP Core - Professional Package README
-->

<div align="center">

# AICP Core

### Python foundation for the AI Capability Protocol

Protocol models, execution contracts, policy evaluation, workflow orchestration,
and local runtime primitives for governed agent actions.

</div>

---

## Overview

**AICP Core** provides the foundational models, interfaces, and default local implementations for the AI Capability Protocol.

It includes:

- **Capability models** for actions, queries, workflows, and async operations
- **Executor** with policy-aware execution and normalized results
- **Registry** for capability discovery and tag-based search
- **Policy engines** for allow, deny, ask, and limit decisions
- **Workflow runtime** for multi-step execution and continuation
- **Approval primitives** for human-in-the-loop execution
- **Validation** against AICP protocol schemas
- **Observability helpers** for logging, tracing, and metrics
- **Reliability utilities** such as retry and circuit breaker patterns

---

## Installation

### Base install

```bash
pip install aicp-core
```

### Optional dependencies

```bash
# Everything
pip install "aicp-core[all]"

# HTTP execution support
pip install "aicp-core[http]"

# Redis-backed caching / rate limiting
pip install "aicp-core[cache]"

# FastAPI integration helpers
pip install "aicp-core[fastapi]"

# WebSocket transport helpers
pip install "aicp-core[websocket]"

# HashiCorp Vault integration
pip install "aicp-core[vault]"

# AWS Secrets Manager integration
pip install "aicp-core[aws]"

# Google Cloud Storage integration
pip install "aicp-core[gcp]"

# YAML project/config support
pip install "aicp-core[yaml]"
```

---

## Quick start

```python
import asyncio

from aicp import (
    AicpExecutor,
    Capability,
    CapabilityKind,
    ConfigPolicyEngine,
    InMemoryCapabilityRepository,
    load_project_config,
)


async def main() -> None:
    capability = Capability(
        name="notes.list",
        description="List notes",
        kind=CapabilityKind.QUERY,
        tags=["notes", "read", "risk:low"],
    )

    repo = InMemoryCapabilityRepository(name="local")
    repo.add_capability(capability)

    config = load_project_config()  # loads aicp.yaml if present, or defaults
    policy_engine = ConfigPolicyEngine(config)

    executor = AicpExecutor(
        capability_provider=repo,
        policy_engine=policy_engine,
    )

    result = await executor.execute("notes.list", {})
    print(result.model_dump(exclude_none=True))


asyncio.run(main())
```

---

## Core concepts

### Capability

A capability is the core unit of AICP. It describes a meaningful action or query with metadata that agents can discover, reason about, and execute.

```python
from aicp import Capability, CapabilityKind, InputSchema, OutputSchema

capability = Capability(
    name="payments.transfer",
    description="Transfer funds between accounts",
    kind=CapabilityKind.ACTION,
    input_schema=InputSchema(
        type="object",
        properties={
            "from_account": {"type": "string"},
            "to_account": {"type": "string"},
            "amount": {"type": "number"},
        },
        required=["from_account", "to_account", "amount"],
    ),
    output_schema=OutputSchema(
        type="object",
        properties={
            "transfer_id": {"type": "string"},
            "status": {"type": "string"},
        },
    ),
    tags=["finance", "payments", "risk:high"],
)
```

### Executor

The executor is the governed runtime entry point. It resolves a capability, evaluates policy, optionally triggers approval, executes the provider, and returns a normalized result.

```python
from aicp import AicpExecutor

executor = AicpExecutor(capability_provider=repo, policy_engine=policy_engine)
result = await executor.execute("payments.transfer", {"amount": 100})
```

### Policy

Policies decide whether a capability should be allowed, denied, limited, or require confirmation/approval.

```python
from aicp import DefaultPolicyEngine, Policy, PolicyCondition, PolicyEffect, PolicySubject

policy_engine = DefaultPolicyEngine()

await policy_engine.add_policy(
    Policy(
        name="protect-transfers",
        description="Transfers require confirmation",
        effect=PolicyEffect.ASK,
        subject=PolicySubject(capability_name="payments.transfer"),
        condition=PolicyCondition(require_confirmation=True),
        priority=100,
    )
)
```

### Workflow runtime

The workflow runtime coordinates multi-step execution with state tracking, confirmation checkpoints, and pause/resume semantics.

```python
from aicp import DefaultWorkflowRuntime

runtime = DefaultWorkflowRuntime(
    capability_provider=repo,
    policy_engine=policy_engine,
)

workflow = await runtime.create_workflow(
    name="payment-flow",
    steps=[
        {"capability_name": "payments.transfer", "arguments": {"amount": 100}},
        {"capability_name": "notifications.send", "arguments": {"channel": "email"}},
    ],
)

result = await runtime.execute_step(workflow.id)
print(result.model_dump(exclude_none=True))
```

### Approval / HITL

AICP includes first-class approval objects and services for human-in-the-loop execution.

```python
from aicp import ApprovalService

approval_service = ApprovalService()
executor = AicpExecutor(
    capability_provider=repo,
    policy_engine=policy_engine,
    approval_service=approval_service,
)
```

When policy requires approval, execution returns a structured result with `approval_request_id` and `approval_status`.

---

## Project-driven loading

AICP can load a local project from `aicp.yaml` plus capability YAML files.

```python
from aicp import load_project

project = load_project(".")
print(project.config)
print([cap.name for cap in project.capabilities])
```

This is the basis for CLI workflows such as:

- `aicp init`
- `aicp scan`
- `aicp ls`
- `aicp preview`
- `aicp run`

---

## Result model

Every execution returns a normalized `ExecutionResult`.

```python
{
  "status": "success",
  "data": {...},
  "execution_time_ms": 2.41,
  "next": {
    "action": "complete"
  },
  "can_continue": true
}
```

This gives agents a stable contract instead of raw tool output chaos.

---

## Package surface

Common public imports:

```python
from aicp import (
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    AicpExecutor,
    AicpRegistry,
    AicpValidator,
    DefaultPolicyEngine,
    ConfigPolicyEngine,
    DefaultWorkflowRuntime,
    ApprovalRequest,
    ApprovalService,
    load_project,
    load_project_config,
)
```

---

## Package layout

| Module | Purpose |
|---|---|
| `aicp.capability` | Capability models and metadata |
| `aicp.executor` | Governed execution |
| `aicp.registry` | Capability registration and search |
| `aicp.validator` | Schema validation |
| `aicp.project_loader` | Load local AICP project state |
| `aicp.approval` | Approval protocol objects |
| `aicp.approval_service` | HITL approval service and store |
| `aicp.interfaces.*` | Core runtime contracts |
| `aicp.implementations.policy` | Default and config-backed policy engines |
| `aicp.implementations.workflow` | Default in-memory workflow runtime |
| `aicp.observability` | Logging, tracing, metrics |
| `aicp.reliability` | Retry and circuit breaker helpers |
| `aicp.security` | Rate limiting and audit signing |
| `aicp.secrets` | Secret storage integrations |
| `aicp.cache` | Redis-backed cache helpers |
| `aicp.plugins` | Plugin registration and transport/source abstractions |

---

## Development

### Install for development

```bash
git clone https://github.com/aicp-ai/aicp.git
cd aicp/packages/core
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Lint and type-check

```bash
ruff check .
mypy src
```

---

## Status

AICP Core is currently **alpha**.

The public surface is stabilizing around:

- capability contracts
- policy evaluation
- workflow state models
- approval primitives
- local project loading

Adapters and higher-level runtime integrations may evolve more quickly.

---

## License

Apache 2.0. See `LICENSE`.
