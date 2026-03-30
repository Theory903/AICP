# AGENTS.md - AICP Development Guide

This file provides guidance to AI coding agents working in the AICP repository.

---

## 1. Project Overview

AICP (AI Capability Protocol) is the governed action runtime for AI agents. It turns APIs, apps, and workflows into discoverable, policy-enforced, stateful capabilities that agents can use safely in production.

**Core concepts:**
- **Action Surface**: The agent-facing surface of software
- **Capability**: A governed action with typed input/output and policy
- **Workflow**: A multi-step process made from one or more capabilities
- **Policy**: Rules defining what is allowed, denied, or requires approval
- **Execution**: The actual invocation of a capability with result normalization
- **ApprovalRequest**: A protocol checkpoint triggered by policy ask
- **AuditEntry**: An immutable record of execution, policy, or approval events

---

## 2. Repository Structure

```
aicp/
├── .github/                       # GitHub configuration & workflows
├── spec/                          # Protocol source of truth (JSON schemas)
│   ├── schemas/                   # JSON Schema definitions
│   ├── examples/                 # Valid/invalid examples
│   └── tests/                    # Schema validation tests
├── packages/                      # Reference implementations (Python)
│   ├── core/                      # Protocol domain model
│   ├── runtime/                  # Execution & orchestration
│   └── cli/                      # Command-line tools
├── sdks/                         # Language-specific SDKs
│   ├── typescript/               # TypeScript SDK packages
│   └── python/                   # Python SDK
├── adapters/                     # Framework & protocol adapters
│   ├── protocol/                 # HTTP, MCP, OpenAPI, GraphQL, mappers
│   ├── framework/                # FastAPI, Express, NestJS
│   └── agent/                    # LangChain, LangGraph
├── mcp/                          # MCP Server implementations
├── examples/                     # Working reference applications
├── docs/                         # Human-readable documentation
├── rfcs/                         # Protocol change proposals
└── governance/                    # Contribution guidelines
```

**Key principle**: `/spec` is the source of truth. If docs and spec disagree, spec wins.

---

## 3. Build Commands

### Python (packages/*, sdks/python)

```bash
# Install dependencies
pip install -e ".[dev]"

# Build package
python -m build

# Run linter
ruff check .

# Run type checker
ruff check --select=typecheck .
# OR: mypy src/

# Format code
ruff format .

# Run tests
pytest

# Run single test file
pytest path/to/test_file.py

# Run single test function
pytest path/to/test_file.py::test_function_name

# Run tests with coverage
pytest --cov=src --cov-report=xml

# Run specific package tests
pytest packages/core/tests/
pytest packages/runtime/tests/
```

### TypeScript/Node.js (sdks/typescript/*, mcp/*)

```bash
# Install dependencies
cd sdks/typescript && npm install

# Build all TypeScript packages
cd sdks/typescript && npm run build

# Run linter
npm run lint

# Run type checker
npm run typecheck

# Format code
npm run format

# Run tests
npm test

# Run single test file
npm test -- path/to/test-file.test.ts

# Run tests with coverage
npm test -- --coverage
```

### Monorepo (pnpm + turbo)

```bash
# Install all dependencies
pnpm install

# Build all packages
pnpm build

# Run all tests
pnpm test

# Run lint across all packages
pnpm lint

# Run typecheck across all packages
pnpm typecheck
```

---

## 4. Code Style Guidelines

### General Principles

- **Spec-first**: Define protocol in `/spec` before implementing runtime behavior
- **Reference implementation**: Keep adapters thin, core clean
- **Single responsibility**: Each module does one thing
- **KISS**: Prefer obvious over clever, explicit over implicit
- **Dependency inversion**: Core depends on abstractions, not implementations

### Python Style

Follow [PEP 8](https://peps.python.org/pep-0008/) with these additions:

**Imports (order matters):**
```python
# Standard library first, then third-party, then local
import asyncio
from typing import Optional

from pydantic import BaseModel, Field

from aicp.core.capability import Capability
from aicp.core.errors import AicpError
```

**Naming:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes, types
- `SCREAMING_SNAKE_CASE` for constants
- Prefix private methods with `_`

**Types:**
- Use type hints everywhere
- Prefer `Optional[X]` over `X | None`
- Use `Protocol` for structural subtyping

```python
from typing import Protocol, Optional

class CapabilityProvider(Protocol):
    def get_capability(self, name: str) -> Optional[Capability]: ...
    def list_capabilities(self) -> list[Capability]: ...
```

**Error handling:**
- Define custom exceptions inheriting from `AicpError`
- Use result objects for expected failures
- Never swallow exceptions silently

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

Follow [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html):

**Imports:**
```typescript
// External first, then internal
import { z } from 'zod';
import { EventEmitter } from 'events';

import { Capability, CapabilitySchema } from './capability';
import { AicpError } from '../errors';
```

**Naming:**
- `camelCase` for functions, variables
- `PascalCase` for classes, interfaces, types
- `SCREAMING_SNAKE_CASE` for constants
- Prefix private members with `_`

**Types:**
- Use explicit return types for public functions
- Prefer interfaces over type aliases for objects
- Use `readonly` for immutable data

```typescript
export interface Capability {
  readonly name: string;
  readonly description: string;
  readonly kind: CapabilityKind;
  readonly input: InputSchema;
  readonly output: OutputSchema;
  readonly policy?: Policy;
}

export type CapabilityKind = 
  | 'action' 
  | 'query' 
  | 'workflow' 
  | 'async_action' 
  | 'batch_action';
```

**Error handling:**
- Define error classes extending `Error`
- Use discriminated unions for error types
- Log errors with appropriate context

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

### File Organization

**Python packages:**
```
packages/core/src/aicp/
├── __init__.py
├── capability/
│   ├── __init__.py
│   ├── capability.py
│   └── validator.py
├── workflow/
│   ├── __init__.py
│   ├── workflow.py
│   └── state.py
├── policy/
│   ├── __init__.py
│   ├── policy.py
│   └── evaluator.py
├── execution/
│   ├── __init__.py
│   ├── executor.py
│   └── result.py
├── rendering/
│   ├── __init__.py
│   └── render.py
├── errors/
│   ├── __init__.py
│   └── exceptions.py
└── pagination/
    ├── __init__.py
    └── page_info.py
```

**TypeScript packages:**
```
sdks/typescript/packages/core/src/
├── index.ts
├── capability/
│   ├── index.ts
│   ├── capability.ts
│   └── validator.ts
├── workflow/
│   ├── index.ts
│   └── workflow.ts
└── types.ts
```

---

## 5. Testing Guidelines

### Test Organization

- Place tests in `tests/` or `__tests__/` directories adjacent to source
- Name test files: `test_*.py` or `*.test.ts`
- Use descriptive test names: `test_capability_validation_rejects_invalid_input`

### Test Structure

```python
# Python: pytest
import pytest
from aicp.core.capability import Capability, validate_capability

class TestCapabilityValidation:
    def test_valid_capability_passes(self):
        capability = Capability(
            name="test.action",
            description="A test action",
            kind="action",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
        result = validate_capability(capability)
        assert result.is_valid

    def test_missing_name_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            Capability(kind="action", ...)
        assert exc_info.value.code == "missing_required_field"
```

```typescript
// TypeScript: Vitest or Jest
import { describe, it, expect } from 'vitest';
import { validateCapability, Capability } from './capability';

describe('CapabilityValidation', () => {
  it('should pass for valid capability', () => {
    const capability: Capability = {
      name: 'test.action',
      description: 'A test action',
      kind: 'action',
      inputSchema: { type: 'object' },
      outputSchema: { type: 'object' }
    };
    expect(validateCapability(capability)).toEqual({ valid: true });
  });
});
```

### Test Coverage

- Aim for >80% coverage on core packages
- Test happy path and error cases
- Include edge cases (empty inputs, max values, etc.)

---

## 6. Protocol Design Guidelines

### Adding New Capability Kinds

1. Define the kind in the core type definitions
2. Add JSON schema in `/spec/schemas/`
3. Add validation logic in core package
4. Add examples in `/spec/examples/valid/`
5. Add invalid examples in `/spec/examples/invalid/`
6. Update documentation in `/docs/`

### Schema Validation

All protocol objects must be validated against JSON schemas:

```python
from jsonschema import validate, ValidationError

def validate_capability(capability: dict) -> None:
    with open('spec/schemas/capability.schema.json') as f:
        schema = json.load(f)
    validate(instance=capability, schema=schema)
```

---

## 7. Adapter Development

### Protocol Adapters

Location: `/adapters/protocol/<name>/`

Structure:
```
adapters/protocol/http/
├── pyproject.toml
├── src/aicp_http/
│   ├── __init__.py
│   ├── adapter.py
│   └── converter.py
├── tests/
└── README.md
```

### Framework Adapters

Location: `/adapters/framework/<name>/`

Examples: FastAPI, Express, NestJS, Next.js, Spring Boot

### Agent Adapters

Location: `/adapters/agent/<name>/`

Examples: LangChain tools, LangGraph, CrewAI

---

## 8. Git Workflow

1. Create feature branch: `git checkout -b feat/capability-name`
2. Make changes with tests
3. Run lint/typecheck before committing
4. Commit with conventional commits: `feat: add capability validation`
5. Push and create PR

---

## 9. Key Files Reference

| Path | Purpose |
|------|---------|
| `spec/schemas/*.schema.json` | Protocol JSON schemas |
| `packages/core/src/aicp/` | Domain models and validation |
| `packages/runtime/src/aicp_runtime/` | Execution engine |
| `adapters/protocol/` | Protocol adapters (HTTP, MCP) |
| `adapters/framework/` | Framework adapters |
| `mcp/` | MCP server implementations |
| `docs/handbook/` | Protocol concepts |
| `governance/CONTRIBUTING.md` | Contribution process |

---

## 10. Important Notes

- **Never commit secrets**: Use environment variables, never hardcode API keys
- **Spec before code**: Protocol changes must be documented in `/spec` first
- **Backward compatibility**: Follow semantic versioning for SDKs
- **Test first**: Use TDD for new features
- **Document public APIs**: All public interfaces need docstrings/type annotations
- **Adapter thinness**: Adapters should translate, not reinvent core logic
- **Core imports**: `/packages/core` should never import from `/packages/runtime` or adapters

## 11. Product Framing Rules

- Public stack: Protocol / Runtime / Connect / Studio
- Public term: Action Surface
- Do not use AIUI as a primary public term
- Governance is protocol-native, not middleware
- Studio is control plane, not core runtime
