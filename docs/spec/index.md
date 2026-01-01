# Protocol Specification

The AICP protocol is defined by JSON schemas in `/spec/schemas/`.

## Schemas

| Schema | Description |
|--------|-------------|
| `capability.schema.json` | Capability definition |
| `workflow.schema.json` | Workflow definition |
| `policy.schema.json` | Policy rules |
| `execution-result.schema.json` | Execution result |
| `discovery.schema.json` | Discovery endpoint |
| `error.schema.json` | Error definitions |

## Validation

All protocol objects must validate against these schemas.

```bash
# Run conformance tests
make test-conformance
```

## Test Fixtures

Valid and invalid examples are in `/spec/tests/`:
- `valid/` - Valid protocol objects
- `invalid/` - Invalid objects that should be rejected

## Research

- [AICP_TOON](AICP_TOON.md) - Direction for capability extraction
