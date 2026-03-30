# AICP Status

**Version:** 0.2.0
**Last Updated:** 2026-03-30
**Milestone:** Governed Action Runtime Reframe

## What Exists

### Core Protocol
- 9 shipped JSON schemas:
  - capability
  - policy
  - workflow
  - execution-result
  - error
  - discovery
  - approval-request
  - approval-decision
  - audit-entry
- Python reference runtime with registry, executor, policy engine, workflow runtime
- Pydantic-based models with JSON Schema 2020-12 validation

### Adapters
- **FastAPI**: auto-discovers routes, infers capability names, extracts schemas from Pydantic models
- **HTTP**: basic HTTP adapter
- **MCP**: MCP protocol adapter
- **OpenAPI**: OpenAPI to capability mapping
- **Postman / HAR / cURL**: importer-based Connect paths now exist

### Examples
- `examples/food-ordering/` - workflow demo
- `examples/payment-transfer/` - governance + approval demo, plus runtime-backed platform demo
- `examples/fastapi-demo/` - FastAPI adapter demo

### CLI
- CLI supports modular commands for `map`, `serve`, `discover`, `execute`, `approvals`, and `history`

## What Passes

- `make lint` - Ruff checks
- `make test` - core unit tests
- `make test-conformance` - schema conformance tests

## Known Limitations

1. workflow runtime is still basic
2. persistence is file-backed today, not database-backed
3. approval flow works through runtime services but still needs production hardening
4. render/pagination/async protocol areas are still roadmap items, not shipped schemas
5. Studio exists as a thin seed, not a full control-plane application yet

## Next Milestone

**Phase 2: Make It Safe**

- approval-request, approval-decision, audit-entry schemas
- pause/resume lifecycle
- approval endpoints
- immutable audit journal
- session-level execution journal

## Architecture Principles

- AICP is the governed action runtime for AI agents
- governance is protocol-native
- workflow state is mandatory
- HITL is a protocol checkpoint
- AICP Connect is the adoption wedge
- Studio is the control plane, not the core runtime
