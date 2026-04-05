# Reference

> Protocol, API, and shell reference for the Mammoth-first AICP stack.

---

## Product Boundary

- **Mammoth** is the operator and agent shell.
- **AICP** is the control plane.
- **Studio-style supervision** should be treated as embedded Mammoth UX.

This reference section focuses on the contracts and surfaces that connect those layers.

---

## Protocol Schemas

The protocol source of truth lives in `/spec/schemas/`.

| Schema | Purpose |
|--------|---------|
| `capability.schema.json` | Capability contract and side-effect metadata |
| `workflow.schema.json` | Workflow object model |
| `workflow-dsl.schema.json` | YAML-friendly workflow authoring DSL |
| `policy.schema.json` | Policy effects and conditions |
| `execution-result.schema.json` | Canonical execution envelope |
| `approval-request.schema.json` | Approval packet contract |
| `approval-decision.schema.json` | Approval resolution contract |
| `audit-entry.schema.json` | Append-only audit entry |
| `session.schema.json` | Session identity and resumable state |
| `discovery.schema.json` | Discovery document for `/.well-known/aicp` |
| `error.schema.json` | Structured errors and recovery hints |

Current capability kinds: `query`, `action`, `workflow`, `async_action`, `batch_action`.

Current policy effects: `allow`, `deny`, `ask`, `limit`.

---

## Runtime / API Surface

Key runtime surfaces:

| Surface | Purpose |
|---------|---------|
| `/v1/execute` | AI-facing governed execution endpoint |
| `/v1/workflows/*` | Workflow create, execute, resume, publish-event |
| `/v1/approvals/*` | Approval queue and decisions |
| `/history` | Audit log and replay-oriented history |
| `/.well-known/aicp` | Discovery document |
| `/console` | Transitional debug/supervision surface |

---

## Shell / Operator Surfaces

Mammoth is the primary shell for now.

| Surface | Purpose |
|---------|---------|
| `apps/mammoth` | Mammoth Rust TUI/CLI shell |
| `apps/mammoth/crates/commands` | Slash-command registry and command metadata |
| `apps/mammoth/crates/tools` | Mammoth tool registry and execution layer |
| `apps/mammoth/crates/server` | Supporting bridge/server surfaces used by Mammoth |

---

## See Also

- [Overview](../overview/index.md)
- [Guides](../guides/index.md)
- [Spec schemas](../../spec/schemas/)
- [Status](../../STATUS.md)
