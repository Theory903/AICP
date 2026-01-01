# AICP Protocol Specification

This directory contains the JSON schemas that define the AICP protocol.

## Schemas

| Schema | Description |
|--------|-------------|
| `capability.schema.json` | Capability definition |
| `workflow.schema.json` | Workflow definition |
| `policy.schema.json` | Policy rules |
| `execution.schema.json` | Execution request/result |
| `result.schema.json` | Execution result |
| `error.schema.json` | Error definitions |
| `render.schema.json` | Render hints |
| `pagination.schema.json` | Pagination |
| `async.schema.json` | Async job handling |

## Validation

All protocol objects must validate against these schemas.

```bash
# Validate all schemas
pytest spec/tests/
```
