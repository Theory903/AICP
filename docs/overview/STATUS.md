# AICP Status

**Version:** 0.1.2  
**Last Updated:** 2025-03-30  
**Milestone:** CI + FastAPI Hardening

## What Exists

### Core Protocol
- 6 JSON schemas (capability, policy, workflow, execution-result, error, discovery)
- Python reference runtime with registry, executor, policy engine, workflow runtime
- Pydantic-based models with JSON Schema 2020-12 validation

### Adapters
- **FastAPI**: Auto-discovers routes, infers capability names, extracts schemas from Pydantic models, supports overlays
- **HTTP**: Basic HTTP adapter
- **MCP**: MCP protocol adapter
- **OpenAPI**: OpenAPI to capability mapping

### Tests
- **Total:** 84 tests
- **Conformance:** 30 tests (valid/invalid fixtures + schema structure)
- **FastAPI adapter:** 28 tests
- **Unit/other:** 26 tests

### Canonical Fixtures
- `spec/tests/valid/` - 17 valid fixtures across 5 protocol objects
- `spec/tests/invalid/` - 5 invalid fixtures for rejection testing
- Fixtures are language-agnostic and can be reused by future TS/Go/Rust runtimes

### CI
- GitHub workflows: `lint.yml`, `test.yml`, `conformance.yml`, `benchmarks.yml`, `examples.yml`, `ci.yml`
- All CI jobs pass

### Examples
- `examples/food-ordering/` - Food ordering workflow demo
- `examples/payment-transfer/` - Payment transfer demo
- `examples/fastapi-demo/` - FastAPI adapter demo

## What Passes

- `make lint` - Ruff checks
- `make test` - 84 unit tests
- `make test-conformance` - 30 conformance tests
- `make test-bench` - 11 benchmark tests
- `make ci` - Full CI pipeline

## Known Limitations

1. **Benchmark tests** - Still threshold-based guards, not full statistical benchmarks
2. **Workflow runtime** - Basic step execution, no complex branching/loops yet
3. **Policy engine** - Simple pattern matching, no advanced conditions
4. **Discovery** - Minimal metadata, no capability grouping
5. **Error handling** - Basic fix hints, no structured remediation paths

## Next Milestone

**Sprint 4E: Extended Adapters + Protocol Maturity**

- Add more invalid fixtures (edge cases)
- Split benchmark guards from real benchmarks
- Add more adapter tests (HTTP, MCP)
- Expand discovery metadata support

## Architecture Principles

- Spec-first: `/spec` is source of truth
- Capability over raw tool
- Workflow awareness over isolated calls
- Policy is first-class
- Adapter-friendly adoption
