# AICP Schema Index

`/spec/schemas/` is the authoritative protocol surface for AICP.

In the current product framing:

- **Mammoth** is the primary interaction shell
- **AICP** is the governed control plane
- these schemas define the contracts Mammoth and other clients interact with

## Schemas

| File | Purpose |
|------|---------|
| `capability.schema.json` | Capability contract and side-effect metadata |
| `workflow.schema.json` | Workflow object model |
| `workflow-dsl.schema.json` | YAML-friendly workflow authoring DSL |
| `policy.schema.json` | Policy effects and conditions |
| `execution-result.schema.json` | Canonical execution envelope |
| `approval-request.schema.json` | Approval packet contract |
| `approval-decision.schema.json` | Approval resolution contract |
| `audit-entry.schema.json` | Append-only audit record |
| `session.schema.json` | Resumable session state |
| `discovery.schema.json` | Discovery document contract |
| `error.schema.json` | Structured error contract |

## v1 Direction

Schema evolution toward v1 should preserve four rules:

1. Governance and approval semantics stay explicit.
2. Workflow and event-resume behavior stays replayable.
3. Mammoth-facing contracts stay stable enough for a shell-first product.
4. Breaking changes require an RFC and migration path.
