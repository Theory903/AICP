# Protocol Specification

> The AICP protocol is defined by JSON schemas in `/spec/schemas/`. This is the source of truth for all protocol objects.

---

## Schemas

| Schema | Description | Current |
|--------|-------------|---------|
| `capability.schema.json` | Capability definition with typed I/O, 5 kinds | Implemented |
| `workflow.schema.json` | Workflow definition with steps and transitions | Implemented |
| `workflow-dsl.schema.json` | YAML-friendly workflow DSL | Implemented |
| `policy.schema.json` | Policy rules with effects and conditions | Implemented |
| `execution-result.schema.json` | Execution envelope (canonical response) | Implemented |
| `discovery.schema.json` | Discovery endpoint response | Implemented |
| `error.schema.json` | Error definitions with codes and fix hints | Implemented |
| `approval-request.schema.json` | Approval request for HITL | Implemented |
| `approval-decision.schema.json` | Approval decision (approve/reject/modify) | Implemented |
| `audit-entry.schema.json` | Immutable audit record | Implemented |
| `session.schema.json` | Session identity and resumable state | Implemented |
| `perception.schema.json` | a11y tree, DOM snapshot, behavioral signals | Protocol |
| `web-compatibility.schema.json` | Web actions, form definitions | Protocol |
| `federation.schema.json` | CRDT registries, DID auth | Protocol |
| `learning.schema.json` | Skills, drift detection, autonomy | Protocol |
| `domains.schema.json` | Domain packs, benchmarks | Protocol |

---

## Validation

All protocol objects must validate against these schemas.

```bash
# Run conformance tests
pytest spec/tests/

# Run schema-focused core tests
pytest -q packages/core/tests/conformance
```

---

## Test Fixtures

Valid and invalid examples are in `/spec/examples/`:
- `valid/` — Valid protocol objects that should validate
- `invalid/` — Invalid objects that should be rejected

---

## Protocol Invariants

These are immovable rules — violating any breaks the protocol:

1. `/spec` is authoritative for protocol structure
2. Schema changes must maintain backward compatibility within major version
3. All implementations must validate protocol objects against JSON schemas
4. Policy evaluation must happen before every side-effecting execution
5. Workflow state must be persisted before transition
6. Every execution must produce the canonical execution envelope

---

## TOON Format

AICP supports TOON (Token-Oriented Object Notation) as an AI-optimized alternative to JSON:

- [AICP_TOON](AICP_TOON.md) — TOON format specification with examples

---

## Versioning

| Version | Protocol Changes | Compliance Level |
|---------|-----------------|-------------------|
| v0.1.1-alpha | 11 schemas, resumable workflows baseline | L2 (Resumable Workflows) |
| v0.2.0 | Planner, judge, memory, intent router | L4 (AI Planning Support) |
| v0.3.0 | Orchestration primitives, YAML DSL, subflows, loops | L3 + shipped L4 components |
| v1.0.0 | 16 schemas, 20 modules, full orchestration | L5 (Protocol Ready) |

**Note:** v1.0.0 protocol is complete. Modules 6, 11, 16-20 have schemas and stub interfaces; real implementations are in progress.

---

## See Also

- [/spec/schemas/](../../spec/schemas/) — JSON schema files
- [TECH_SPEC.md](../guides/TECH_SPEC.md) — Technical specification
- [ACTION_SURFACE.md](../overview/ACTION_SURFACE.md) — Capability model
- [GOVERNANCE.md](../overview/GOVERNANCE.md) — Policy and approval details
