# AICP Documentation

<p align="center">
  <img src="https://docs.aicp.ai/img/aicp-logo.svg" width="200" alt="AICP Logo">
</p>

---

Welcome to the **AICP (AI Capability Protocol)** documentation. AICP is the governed action runtime for AI agents — transforming APIs, applications, and workflows into discoverable, policy-enforced, stateful capabilities.

---

## Getting Started

### New to AICP?

Start here to understand the core concepts:

<div class="getting-started-grid">

| Guide | Description |
|-------|-------------|
| [What is AICP?](./overview/index.md) | Product overview and core concepts |
| [Quick Start](./guides/index.md) | Installation and first steps |
| [How-To Guide](./guides/HOW_TO_USE.md) | Complete usage reference |
| [Platform Demo](./examples/PLATFORM_DEMO.md) | End-to-end walkthrough |

</div>

---

## The AICP Stack

AICP consists of four interconnected layers:

```
┌─────────────────────────────────────────────────────────┐
│                    AICP Protocol                        │
│            (JSON Schemas, Capability Kinds)              │
├─────────────────────────────────────────────────────────┤
│                     AICP Runtime                        │
│         (Execution, Workflows, Governance)              │
├─────────────────────────────────────────────────────────┤
│                    AICP Connect                         │
│       (Adapters: HTTP, MCP, OpenAPI, GraphQL)           │
├─────────────────────────────────────────────────────────┤
│                     AICP Studio                        │
│        (Control Plane: Approvals, Audit, UI)            │
└─────────────────────────────────────────────────────────┘
```

### Protocol
- [Action Surface](./overview/ACTION_SURFACE.md) — Agent-facing capability definitions
- [Governance](./overview/GOVERNANCE.md) — Policy, approvals, and audit
- [Spec](./spec/index.md) — Protocol schemas

### Runtime
- Execution engine with policy evaluation
- Workflow orchestration
- Approval workflows

### Connect
- HTTP, WebSocket, SSE, GraphQL transports
- MCP server and client
- OpenAPI, Postman, HAR importers

### Studio
- Approval dashboard
- Audit timeline
- Workflow replay

---

## Core Concepts

<div class="concepts-grid">

### Capabilities

The fundamental unit — a meaningful action with typed inputs/outputs.

```python
Capability(
    name="payments.transfer",
    kind=CapabilityKind.ACTION,
)
```

[Learn more](./overview/ACTION_SURFACE.md) →

### Policy

Govern what actions are allowed, denied, or require approval.

```python
Policy(
    effect=PolicyEffect.ASK,
    condition=amount > 10000,
)
```

[Learn more](./overview/GOVERNANCE.md) →

### Workflows

Multi-step processes with state tracking.

```python
Workflow(
    steps=[step1, step2, step3],
    on_approval="resume",
)
```

[Learn more](./overview/GOVERNANCE.md) →

</div>

---

## How-To Guides

### Basics
- [Installation](./guides/index.md)
- [Your first capability](./guides/HOW_TO_USE.md#quick-start)
- [Execution and streaming](./guides/HOW_TO_USE.md#execution--streaming)

### Authentication & Security
- [API Key, OAuth2, Basic Auth](./guides/HOW_TO_USE.md#authentication)
- [Rate limiting](./guides/HOW_TO_USE.md#security-features)
- [Multi-tenancy](./guides/HOW_TO_USE.md#multi-tenancy)

### Production
- [Observability](./guides/HOW_TO_USE.md#observability)
- [Health checks](./guides/HOW_TO_USE.md#production-api-features)
- [Secrets management](./guides/HOW_TO_USE.md#secrets-management)

### Adapters
- [FastAPI integration](./guides/HOW_TO_USE.md#transport-adapters)
- [MCP server](./guides/HOW_TO_USE.md#transport-adapters)
- [WebSocket & GraphQL](./guides/HOW_TO_USE.md#transport-adapters)

---

## API Reference

Complete API documentation:

- [Core Modules](./reference/index.md)
- [Protocol Schemas](./spec/index.md)
- [CLI Commands](./reference/index.md)

---

## Examples

| Example | Description |
|---------|-------------|
| [Platform Demo](./examples/PLATFORM_DEMO.md) | Full Runtime + Studio |
| [Payment Transfer](https://github.com/aicp-ai/aicp/tree/main/examples/payment-transfer) | Capability example |

---

## Additional Resources

- [Vision](./overview/VISION.md) — Product positioning
- [Roadmap](./overview/ROADMAP.md) — Future plans
- [Comparison](./overview/COMPARISON.md) — AICP vs MCP, OpenAI, LangChain
- [Status](./overview/STATUS.md) — Current implementation state

---

## Support

<p align="center">
  <a href="https://discord.gg/aicp"><img src="https://img.shields.io/discord/123456789?label=Discord&style=for-the-badge" alt="Discord"></a>
  <a href="https://github.com/aicp-ai/aicp/issues"><img src="https://img.shields.io/github/issues/aicp-ai/aicp?label=Issues&style=for-the-badge" alt="GitHub Issues"></a>
  <a href="https://twitter.com/aicp_ai"><img src="https://img.shields.io/twitter/follow/aicp_ai?label=Twitter&style=for-the-badge" alt="Twitter"></a>
</p>

---

<p align="center">
  <em>Built for agents. Governed by design.</em>
</p>
