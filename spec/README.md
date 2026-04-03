<!--
  AICP Protocol Specification - Professional Documentation
-->

<div align="center">

# AICP Protocol Specification

> The canonical source of truth for the Agentic Web Operating System — JSON schemas defining the 11-plane architecture and 20-module system.

</div>

---

## Overview

This directory contains the **JSON Schema** definitions that define the AICP protocol. These schemas are the **authoritative source** — if documentation and implementation disagree with these schemas, the schemas win.

---

## Core Schemas

| Schema | Description | Status |
|--------|-------------|--------|
| [capability.schema.json](./schemas/capability.schema.json) | Capability definition | ✅ Stable |
| [workflow.schema.json](./schemas/workflow.schema.json) | Workflow execution state | ✅ Stable |
| [policy.schema.json](./schemas/policy.schema.json) | Policy rules | ✅ Stable |
| [execution-result.schema.json](./schemas/execution-result.schema.json) | Normalized execution result | ✅ Stable |
| [error.schema.json](./schemas/error.schema.json) | Structured error definition | ✅ Stable |
| [discovery.schema.json](./schemas/discovery.schema.json) | Capability discovery response | ✅ Stable |
| [approval-request.schema.json](./schemas/approval-request.schema.json) | Human approval request | ✅ Stable |
| [approval-decision.schema.json](./schemas/approval-decision.schema.json) | Human approval decision | ✅ Stable |
| [audit-entry.schema.json](./schemas/audit-entry.schema.json) | Immutable audit journal entry | ✅ Stable |

---

## Schema Categories

### Capability Definition

```json
{
  "name": "payments.transfer",
  "description": "Transfer funds between accounts",
  "kind": "action",
  "input_schema": {...},
  "output_schema": {...}
}
```

### Policy

```json
{
  "name": "high-value-transfer",
  "effect": "ask",
  "condition": {
    "field": "arguments.amount",
    "operator": ">",
    "value": 10000
  }
}
```

### Execution Result

```json
{
  "status": "success",
  "data": {...},
  "next": {
    "action": "continue",
    "capability": "notifications.send",
    "hint": "Transfer complete, notify user"
  }
}
```

---

## Validation

All protocol objects **must** validate against these schemas.

```bash
# Validate all schemas
pytest spec/tests/

# Validate a specific schema
jsonschema --instance data.json spec/schemas/capability.schema.json
```

---

## Examples

See [`./examples/`](./examples/) for valid and invalid examples:

```
examples/
├── valid/
│   ├── capability-action.json
│   ├── capability-query.json
│   ├── policy-ask.json
│   └── workflow-simple.json
└── invalid/
    ├── capability-missing-name.json
    ├── policy-invalid-condition.json
    └── workflow-broken-steps.json
```

---

## Deferred Areas

The following protocol areas are defined in implementation but **not yet** shipped as standalone source-of-truth schemas:

- **Render hints** — UI formatting instructions
- **Pagination** — List/collection handling
- **Async jobs** — Long-running task semantics

---

## Contributing

To propose changes to the protocol:

1. **Create an RFC** — See [/rfcs/README.md](../rfcs/README.md)
2. **Update schemas** — Modify the relevant JSON schema
3. **Add examples** — Include valid/invalid examples
4. **Update tests** — Add validation tests

---

## References

- [JSON Schema](https://json-schema.org/)
- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)

---

<p align="center">
  <em>Schema is the source of truth.</em>
</p>
