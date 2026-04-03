# API Reference

> Complete API reference for AICP — Python SDK, JSON schemas, and CLI commands.

---

## Python SDK

### Core Models

| Class | Description |
|-------|-------------|
| `Capability` | Main capability model with typed I/O, side effects, risk metadata |
| `CapabilityKind` | Enum: `query`, `action`, `confirm`, `notify`, `batch` |
| `Workflow` | Multi-step stateful process with branching and compensation |
| `Policy` | Access control rules with effects and conditions |
| `PolicyEffect` | Enum: `allow`, `deny`, `ask`, `require_approval`, `limit` |
| `ExecutionEnvelope` | Canonical response from every capability execution |

### Registry & Executor

| Class | Description |
|-------|-------------|
| `CapabilityRegistry` | Store, validate, discover capabilities |
| `AicpExecutor` | Execute capabilities with policy enforcement |
| `PolicyEngine` | Evaluate policies before execution |
| `WorkflowRuntime` | Execute workflows with state management |
| `ApprovalService` | Manage approval lifecycle |
| `AuditService` | Immutable audit trail |

### Adapters

| Class | Description |
|-------|-------------|
| `HTTPAdapter` | Execute capabilities over HTTP |
| `MCPAdapter` | Consume external MCP tools as AICP capabilities |
| `FastAPIAdapter` | Auto-discover routes from FastAPI apps |
| `OpenAPIImporter` | Import OpenAPI specs as capabilities |

---

## JSON Schemas

All protocol objects are defined in `/spec/schemas/`:

| Schema | Description |
|--------|-------------|
| `capability.schema.json` | Capability definition |
| `workflow.schema.json` | Workflow definition |
| `policy.schema.json` | Policy rules |
| `execution-result.schema.json` | Execution envelope |
| `approval-request.schema.json` | Approval request |
| `approval-decision.schema.json` | Approval decision |
| `audit-entry.schema.json` | Audit record |
| `discovery.schema.json` | Discovery manifest |
| `error.schema.json` | Error definitions |

---

## CLI Commands

```bash
# Bootstrap an application
aicp bootstrap fastapi src.main:app

# Preview capability
aicp preview payments.transfer

# Protect a capability
aicp protect payments.transfer

# Run runtime
aicp serve --store-path ./.aicp-runtime

# Execute capability
aicp execute payments.transfer --args '{"amount": 100}'

# List capabilities
aicp discover

# List approvals
aicp approvals list

# Decide approval
aicp approvals decide apr_123 --decision approve
```

See [CLI_REFERENCE.md](../guides/CLI_REFERENCE.md) for full command documentation.

---

## Execution Envelope

Every capability execution returns this structure:

```json
{
  "execution_id": "exec_...",
  "capability_name": "...",
  "status": "success|failure|pending_approval",
  "data": { ... },
  "policy_result": { "effect": "allow", "trust_tier": 2 },
  "allowed_next_actions": [...],
  "rendered": "...",
  "execution_time_ms": 234
}
```

---

## See Also

- [CLI_REFERENCE.md](../guides/CLI_REFERENCE.md) — 28 CLI commands
- [TECH_SPEC.md](../guides/TECH_SPEC.md) — Protocol technical specification
- [/spec/schemas/](../../spec/schemas/) — JSON schema source of truth