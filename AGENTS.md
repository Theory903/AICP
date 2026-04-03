# AGENTS.md -- AICP Development Guide

This file provides guidance to AI coding agents working in the AICP repository.

---

## 1. Project Overview

**AICP (AI Capability Protocol)** is the Agentic Web Operating System -- the protocol, runtime, memory, governance, perception, execution, and federation layer that turns the human web into an agent-operable web.

**Current state:** v0.1.1-alpha, a Python reference implementation at Compliance Level 2 (Resumable Workflows). See STATUS.md for the full current-state inventory.

**Target state:** v1.0.0, the complete Agentic Web OS with 11 architectural planes and 20 modules at Compliance Level 5 (Full Orchestration). See ROADMAP.md for the phased build order.

### Architecture: 11 Planes

| # | Plane | Purpose |
|---|-------|---------|
| 0 | Signal | Sub-ms event ingestion, dedup, classification, routing |
| 1 | Perception | a11y tree, DOM observation, screenshots, behavioral signals |
| 2 | AI | Planner, judge, intent router, memory, cognitive protocols |
| 3 | Capability | Registry, schema validation, ranked discovery, semantic search |
| 4 | Workflow | Sequential, parallel, fork/join, sagas, event-driven, subflows |
| 5 | Governance | Compiled policy engine, trust tiers, risk scoring, approval lifecycle |
| 6 | Execution | Realtime (<5ms), transactional (saga), event-driven (wait/resume) |
| 7 | Multi-Agent | Orchestrator/specialist/worker/supervisor hierarchy, communication bus |
| 8 | Federation | `/.well-known/aicp` discovery, CRDT registries, DID auth |
| 9 | Supervision | Live feed, approval queue, replay debugger, policy editor |
| 10 | Learning | Skill mining, policy learning, drift detection, autonomy calibration |

### The 20 Modules

| # | Module | Plane | v0.1.1 Status |
|---|--------|-------|---------------|
| 1 | Principal and Org Control | Governance | Not started |
| 2 | Identity and Trust | Governance | Partial (session tokens, basic auth) |
| 3 | Capability Registry | Capability | Complete (L2) |
| 4 | Tool Runtime | Execution | Complete (L2) |
| 5 | Workflow Engine | Workflow | Complete (L2) |
| 6 | Perception and Signal Layer | Perception/Signal | Not started |
| 7 | Human Cognitive Protocols | Supervision | Partial (approval CLI + API) |
| 8 | AI Plane | AI | Not started |
| 9 | Memory System | AI | Minimal (session state only) |
| 10 | Code Intelligence DB | AI | Not started |
| 11 | Crawl / Map / Discovery Engine | Capability | Partial (keyword scoring) |
| 12 | Governance and Policy | Governance | Complete (L2) |
| 13 | Execution Engine | Execution | Complete (L2) |
| 14 | Multi-Agent Hierarchy | Multi-Agent | Not started |
| 15 | Agent Communication Bus | Multi-Agent | Not started |
| 16 | Federation and Agentic WWW | Federation | Minimal (well-known endpoint) |
| 17 | Human Web Compatibility | Perception | Not started |
| 18 | Audit / Replay / Observability | Supervision | Partial (append-only journal) |
| 19 | Learning / Drift / Growth | Learning | Not started |
| 20 | Domain Packs and Benchmarks | Learning | Not started |

### Core Concepts

- **Action Surface**: The agent-facing surface of software -- structured, typed, policy-governed actions.
- **Capability**: A governed action with strict input/output schema, side-effect classification, approval metadata, retry policy, and error codes.
- **Workflow**: A stateful, resumable, multi-step process with branching, retries, approval checkpoints, and compensation.
- **Policy**: Rules defining what is allowed, denied, or requires approval -- evaluated per capability call.
- **Execution Envelope**: The canonical response object that every capability execution produces. All planes consume it.
- **Session**: Resumable execution context with state, memory, and approval history.
- **Trust Tier**: 0 (anonymous) to 4 (fully autonomous). Determines default policy effects.
- **Compliance Level**: 0 (Discovery) to 5 (Full Orchestration). Implementations declare their level.

### Non-Negotiable Engineering Rules

1. Every capability must be deterministic at interface level.
2. Every side effect must be logged.
3. Every action must be replayable.
4. Every risky action must be policy-gated.
5. Every workflow must be resumable.
6. Every flow must be idempotent where possible.
7. Every execution must expose `allowed_next_actions`.

---

## 2. Repository Structure

```
aicp/
├── spec/                          # Protocol source of truth (JSON schemas)
│   ├── schemas/                   # 9 schema definitions (v0.1.1)
│   ├── examples/                  # Valid/invalid examples
│   └── tests/                     # Schema validation tests
├── packages/
│   ├── core/                      # Protocol domain model (Python)
│   ├── runtime/                   # Execution engine, services, persistence
│   └── cli/                       # 28 CLI commands
├── adapters/
│   ├── protocol/                  # HTTP, MCP adapter, OpenAPI, GraphQL, WebSocket
│   ├── framework/                 # FastAPI, Express, NestJS, Next.js, Spring Boot
│   ├── agent/                     # LangChain, LangGraph, CrewAI
│   └── importers/                 # cURL, HAR, Postman importers
├── sdks/
│   ├── typescript/                # TypeScript SDK (core built, runtime/client skeleton)
│   └── python/                    # Python SDK (skeleton)
├── mcp/                           # MCP server (exposes AICP outward to MCP clients)
├── apps/
│   └── studio/                    # AICP Studio (control plane UI, minimal)
├── examples/                      # Reference applications
├── docs/                          # Human-readable documentation
│   ├── overview/                  # Vision, status, comparisons, use cases
│   ├── guides/                    # Architecture, CLI, runtime, tech spec
│   ├── handbook/                  # Concept deep-dives (agentic experience)
│   ├── spec/                      # Protocol spec prose (complements /spec JSON)
│   ├── reference/                 # API reference (index)
│   └── examples/                  # Example walkthroughs
├── rfcs/                          # Protocol change proposals
└── governance/                    # CONTRIBUTING.md, CODE_OF_CONDUCT.md
```

**Key rule:** `/spec` is the source of truth. If runtime behavior and spec disagree, spec wins.

**MCP disambiguation:** `mcp/` is the MCP server (exposes AICP capabilities outward to MCP clients). `adapters/protocol/mcp/` is the MCP adapter (lets AICP consume external MCP tools as capabilities). Both are working. They solve opposite problems.

---

## 3. Build Commands

### Python (packages/*, sdks/python)

```bash
# Install all packages (editable)
pip install -e "packages/core[dev]" -e packages/runtime -e packages/cli -e adapters/framework/fastapi

# Run linter
ruff check .

# Run formatter
ruff format .

# Run type checker
ruff check --select=typecheck .
# OR: mypy src/

# Run all tests
pytest

# Run single test file
pytest path/to/test_file.py

# Run single test function
pytest path/to/test_file.py::test_function_name

# Run tests with coverage
pytest --cov=src --cov-report=xml

# Run package-specific tests
pytest packages/core/tests/
pytest packages/runtime/tests/
pytest packages/cli/tests/
```

### TypeScript/Node.js (sdks/typescript/*, mcp/*)

```bash
cd sdks/typescript && npm install
cd sdks/typescript && npm run build
npm run lint
npm run typecheck
npm run format
npm test
npm test -- path/to/test-file.test.ts
npm test -- --coverage
```

### Monorepo (if using pnpm + turbo)

```bash
pnpm install
pnpm build
pnpm test
pnpm lint
pnpm typecheck
```

---

## 4. Code Style

### General Principles

- **Spec-first**: Define protocol in `/spec` before implementing runtime behavior.
- **Reference implementation**: Keep adapters thin, core clean.
- **Single responsibility**: Each module does one thing.
- **KISS**: Prefer obvious over clever, explicit over implicit.
- **Dependency inversion**: Core depends on abstractions, not implementations.

### Python Style

Follow PEP 8 with these additions:

**Imports (order):**
```python
import asyncio                              # stdlib
from typing import Optional, Protocol

from pydantic import BaseModel, Field       # third-party

from aicp.core.capability import Capability # local
from aicp.core.errors import AicpError
```

**Naming:** `snake_case` for functions/variables/modules, `PascalCase` for classes/types, `SCREAMING_SNAKE_CASE` for constants. Prefix private methods with `_`.

**Types:** Use type hints everywhere. Prefer `Optional[X]` over `X | None`. Use `Protocol` for structural subtyping.

**Errors:** Define custom exceptions inheriting from `AicpError`. Use result objects for expected failures. Never swallow exceptions silently.

```python
class AicpError(Exception):
    """Base exception for all AICP errors."""
    pass

class ValidationError(AicpError):
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")
```

### TypeScript Style

Follow Google TypeScript Style Guide:

**Imports:** External first, then internal.

**Naming:** `camelCase` for functions/variables, `PascalCase` for classes/interfaces/types, `SCREAMING_SNAKE_CASE` for constants.

**Types:** Use explicit return types for public functions. Prefer interfaces over type aliases for objects. Use `readonly` for immutable data.

**Errors:**
```typescript
export class AicpError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: ErrorStatus
  ) {
    super(message);
    this.name = 'AicpError';
  }
}

export type ErrorStatus =
  | 'invalid_input'
  | 'unavailable'
  | 'rate_limited'
  | 'timeout'
  | 'failed';
```

### Coding Patterns (from Reference Architecture)

The `ref/` directory contains reference architecture patterns that inform AICP's implementation style:

- **`buildTool()` factory**: Capabilities are constructed through factory functions, not raw constructors.
- **Branded types**: Use TypeScript branded types for IDs (`SessionId`, `ExecutionId`) to prevent mix-ups at compile time.
- **Discriminated unions**: Use discriminated unions for status types, execution modes, and error categories.
- **Zod schemas with semantic coercion**: Input validation via Zod with coercion for common type mismatches.
- **Fail-closed defaults**: If policy evaluation fails, deny. If schema validation fails, reject.
- **Custom error hierarchy**: All errors extend `AicpError` with structured `code` and `status` fields.
- **Head limits with pagination**: All list endpoints return bounded results with pagination cursors.
- **Defense-in-depth permissions**: Permission checks at API boundary, service layer, and data layer.
- **Lazy schema construction**: Schemas are built on first use, not at import time.
- **`satisfies` keyword**: Use `satisfies` for compile-time type checking without widening.
- **`DeepImmutable` wrappers**: Execution results and audit entries are immutable after creation.
- **LRU-cached safe JSON parsing**: Parse once, cache the result, handle malformed input gracefully.

---

## 5. Testing Guidelines

### Organization

- Tests live in `tests/` or `__tests__/` adjacent to source.
- File naming: `test_*.py` (Python), `*.test.ts` (TypeScript).
- Use descriptive names: `test_capability_validation_rejects_invalid_input`.

### Structure

```python
# Python: pytest
import pytest
from aicp.core.capability import Capability, validate_capability

class TestCapabilityValidation:
    def test_valid_capability_passes(self):
        cap = Capability(name="test.action", description="Test", kind="action",
                         input_schema={"type": "object"}, output_schema={"type": "object"})
        assert validate_capability(cap).is_valid

    def test_missing_name_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            Capability(kind="action", ...)
        assert exc_info.value.code == "missing_required_field"
```

```typescript
// TypeScript: Vitest
import { describe, it, expect } from 'vitest';
import { validateCapability } from './capability';

describe('CapabilityValidation', () => {
  it('passes for valid capability', () => {
    const cap = { name: 'test.action', description: 'Test', kind: 'action',
                  inputSchema: { type: 'object' }, outputSchema: { type: 'object' } };
    expect(validateCapability(cap)).toEqual({ valid: true });
  });
});
```

### Coverage

- Aim for >80% on core packages.
- Test happy path, error cases, and edge cases (empty inputs, max values, boundary conditions).
- Every new spec schema must have conformance tests in `spec/tests/`.

---

## 6. Protocol Design

### Adding a New Schema

1. Define the schema in `/spec/schemas/<name>.schema.json`.
2. Add valid examples in `/spec/examples/valid/`.
3. Add invalid examples in `/spec/examples/invalid/`.
4. Add conformance tests in `/spec/tests/`.
5. Add the domain model in `packages/core/src/aicp/`.
6. Update STATUS.md module matrix.
7. Update docs.

### Adding a New Capability Kind

1. Add the kind to the `capability.schema.json` enum.
2. Add validation logic in core package.
3. Add examples.
4. Add conformance tests.
5. Update adapter translation layers.

### Schema Validation

All protocol objects must validate against their JSON schema:

```python
import json
from jsonschema import validate

def validate_capability(capability: dict) -> None:
    with open('spec/schemas/capability.schema.json') as f:
        schema = json.load(f)
    validate(instance=capability, schema=schema)
```

---

## 7. Adapter Development

Adapters translate between AICP and external protocols/frameworks. They MUST NOT contain core orchestration logic.

### Protocol Adapters (`adapters/protocol/<name>/`)

Translate between AICP's internal protocol and external protocols (HTTP, MCP, OpenAPI, GraphQL, WebSocket).

### Framework Adapters (`adapters/framework/<name>/`)

Mount AICP routes on application frameworks (FastAPI, Express, NestJS, Next.js, Spring Boot).

### Agent Adapters (`adapters/agent/<name>/`)

Expose AICP capabilities to agent frameworks (LangChain, LangGraph, CrewAI).

### Adapter Rules

- Adapters translate only. They MUST NOT contain business logic.
- Adapter-specific logic MUST NOT leak into core models.
- Each adapter has its own `pyproject.toml` or `package.json`, `tests/`, and `README.md`.
- Test adapters against the conformance test suite, not just unit tests.

---

## 8. Architectural Invariants

These are immovable. Violating any of these breaks the protocol.

### Spec Invariants

- `/spec` is authoritative for protocol structure.
- Protocol changes MUST be documented in `/spec` before runtime implementation.
- All implementations MUST validate protocol objects against JSON schemas.
- Schema changes MUST maintain backward compatibility unless version bump.

### Runtime Invariants

1. A capability execution MUST always be policy-evaluated before side effects.
2. A workflow run MUST always have persisted state before transition.
3. A workflow step CANNOT be marked complete without an audit entry.
4. An approval-gated action CANNOT execute before approval is resolved.
5. Every execution response MUST expose `allowed_next_actions`.
6. Session context MUST be resumable across process restarts.
7. A workflow run has at most one active step unless inside a declared parallel block.
8. A resumed workflow MUST preserve prior audit lineage.
9. A workflow terminal state is immutable except via replay/fork semantics.
10. Every execution event MUST be attributable to agent, human, or system actor.

### Package Boundary Invariants

- `/packages/core` MUST remain runtime-agnostic and adapter-agnostic.
- `/packages/core` MUST NOT import from `/packages/runtime` or adapters.
- Adapters MUST translate only; they MUST NOT contain core orchestration logic.
- Adapter-specific logic MUST NOT leak into core models.

---

## 9. Forbidden Shortcuts

These shortcuts look helpful but destroy architecture. Do not do them.

- Do NOT change protocol behavior in runtime code without spec updates.
- Do NOT import from runtime into core packages.
- Do NOT embed adapter-specific logic into core models.
- Do NOT bypass policy evaluation for side-effecting capabilities.
- Do NOT add hidden workflow transitions not representable in the spec.
- Do NOT mark roadmap items as complete unless tests and implementation exist.
- Do NOT introduce implicit state transitions without audit entries.
- Do NOT make adapters "smart." Adapters translate only.
- Do NOT add `determinism_class` or `execution_mode` fields without spec updates.
- Do NOT create new API endpoints without adding them to the spec first.
- Do NOT present unimplemented adapters as available integrations.
- Do NOT use pseudocode without labeling it as pseudocode.

---

## 10. Execution Contract

All runtime implementations MUST produce the canonical execution envelope:

```json
{
  "execution_id": "exec_a1b2c3d4",
  "capability_name": "orders.place",
  "capability_kind": "action",
  "determinism_class": "bounded_nondeterministic",
  "workflow_id": "wf_e5f6g7h8",
  "step_id": "step_place_order",
  "session_id": "sess_i9j0k1l2",
  "execution_mode": "sync",
  "policy_result": {
    "effect": "allow",
    "policy_name": "default_actions",
    "trust_tier": 2,
    "risk_score": { "financial": 0.7, "irreversibility": 0.9, "privacy": 0.1 },
    "evaluation_time_ms": 0.3
  },
  "approval_state": {
    "status": "none",
    "approval_id": null,
    "decided_by": null,
    "decided_at": null
  },
  "status": "success",
  "data": { "order_id": "ord_m3n4o5p6" },
  "error": null,
  "error_detail": null,
  "execution_time_ms": 234,
  "idempotency_key": "cart_q7r8s9t0",
  "allowed_next_actions": [
    { "kind": "capability", "name": "order.track", "reason": "Track delivery", "requires_approval": false, "confidence": 0.95 }
  ],
  "rendered": "Order placed. Estimated delivery: 7:30 PM.",
  "format_hint": "text",
  "audit_correlation_id": "corr_u1v2w3x4",
  "actor": { "type": "agent", "agent_id": "agent_y5z6", "session_id": "sess_i9j0k1l2" },
  "timestamp": "2026-04-03T18:45:12.456Z"
}
```

Every execution MUST produce this envelope. UI, planner, judge, audit, and replay all consume it.

---

## 11. Compliance Levels

| Level | Name | Requirements |
|-------|------|-------------|
| 0 | Capability Discovery | Capability registry, schema validation, basic execution |
| 1 | Governed Execution | L0 + policy evaluation, approval checkpoints, audit trail, session management |
| 2 | Resumable Workflows | L1 + sequential workflows, compensation, state persistence, resume after approval |
| 3 | Event-Driven Orchestration | L2 + wait-for-event, timeout branching, parallel steps, loops |
| 4 | AI Planning Support | L3 + planner, judge, context builder, allowed-next-actions schema |
| 5 | Full Orchestration | L4 + multi-agent coordination, subflows, cross-flow events, federation, supervision |

Current reference implementation: **Level 2**.

---

## 12. Git Workflow

1. Create a feature branch: `git checkout -b feat/<module-name>`.
2. Make changes with tests.
3. Run lint/typecheck before committing: `ruff check . && ruff format --check .`
4. Commit with conventional commits: `feat: add capability validation`.
5. Push and create PR against `main`.

Commit message prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `spec:`.

---

## 13. Key Files Reference

| Path | Purpose |
|------|---------|
| `spec/schemas/*.schema.json` | Protocol JSON schemas (source of truth) |
| `packages/core/src/aicp/` | Domain models and validation |
| `packages/runtime/src/aicp_runtime/` | Execution engine, services, persistence |
| `packages/cli/src/aicp_cli/` | CLI commands |
| `adapters/protocol/` | Protocol adapters (HTTP, MCP, OpenAPI) |
| `adapters/framework/` | Framework adapters (FastAPI) |
| `adapters/agent/` | Agent adapters (LangChain, LangGraph, CrewAI) |
| `mcp/` | MCP server (exposes AICP outward to MCP clients) |
| `sdks/typescript/` | TypeScript SDK |
| `apps/studio/` | AICP Studio UI |
| `examples/` | Reference applications |
| `docs/` | Human-readable documentation |
| `rfcs/` | Protocol change proposals |
| `governance/` | Contribution guidelines |
| `STATUS.md` | Current implementation state |
| `ROADMAP.md` | Phased roadmap v0.1.1 to v1.0.0 |
| `ARCHITECTURE.md` | System architecture (11 planes, 20 modules) |
| `MODULE_MAP.md` | Feature-to-module mapping |

---

## 14. Product Framing

- **Public stack:** Protocol / Runtime / Connect / Studio.
- **Public term:** Action Surface (the agent-facing surface of software).
- Governance is protocol-native, not middleware.
- Studio is the supervision console, not the runtime.
- AICP is the protocol and runtime model. The Python runtime in this repository is the reference implementation.

---

## 15. Spec Language

AICP uses RFC 2119 convention for normative requirements:

| Term | Meaning |
|------|---------|
| **MUST** | Required for compliant implementations |
| **SHOULD** | Recommended unless strong reason otherwise |
| **MAY** | Optional extension |

Normative content lives in `/spec/schemas/`. Everything else is informative.

---

## 16. What to Do First

If you are starting fresh on this codebase:

1. Read `README.md` for the full picture.
2. Read `STATUS.md` for what exists vs. what is planned.
3. Read `ARCHITECTURE.md` for the 11-plane design.
4. Run `pytest` to verify the test suite passes.
5. Run `aicp dev` on an example app to see the runtime in action.
6. Pick a module from the 20-Module Status Matrix in STATUS.md.
7. Check if the module has a spec schema. If not, start there.
8. If it has a spec, write conformance tests first, then implement.
