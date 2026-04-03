<!-- Context: project-intelligence/technical | Priority: critical | Version: 1.0 | Updated: 2026-04-03 -->

# Technical Domain

**Purpose**: Tech stack, architecture patterns, and development conventions for AICP (Agentic Web Operating System).
**Last Updated**: 2026-04-03

## Primary Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | Python | 3.10+ | Reference implementation runtime |
| Language | TypeScript | 5.x | SDK and MCP server |
| Schema | JSON Schema | 2020-12 | Protocol source of truth |
| Validation | Pydantic | 2.x | Python domain models |
| Runtime | FastAPI | 0.115+ | HTTP adapter |
| CLI | Click/Argparse | - | 28 CLI commands |
| Storage | SQLite + File | - | Persistence backends |
| Testing | pytest | 8.x | 172+ tests |

## Code Patterns

### Python Capability Definition
```python
class Capability(BaseModel):
    name: str
    description: str
    kind: CapabilityKind
    input_schema: dict
    output_schema: dict
    requires_approval: bool = False
    risk_level: str = "medium"
```

### Python Policy Evaluation
```python
def evaluate_policy(capability: Capability, actor: Actor) -> PolicyResult:
    # Trust tier check → risk scoring → effect determination
    if actor.trust_tier < capability.min_trust:
        return PolicyResult(effect="deny", reason="insufficient_trust")
    # ... compute risk score, return allow/deny/ask
```

### Python Workflow Execution
```python
async def execute_workflow(workflow: Workflow, session: Session) -> ExecutionEnvelope:
    for step in workflow.steps:
        result = await execute_capability(step.capability, step.args)
        if result.status == "pending_approval":
            await pause_for_approval(result.approval_id)
        # Track state, handle compensation on failure
```

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Files | snake_case | `capability_registry.py` |
| Classes | PascalCase | `CapabilityRegistry` |
| Functions | snake_case | `register_capability` |
| Constants | SCREAMING_SNAKE | `MAX_RETRY_ATTEMPTS` |
| Database | snake_case | `capability_table` |

## Code Standards

- All capability definitions must validate against JSON schemas in `/spec/schemas/`
- Every execution must produce the canonical execution envelope
- Policy evaluation happens BEFORE side effects (fail-closed defaults)
- Workflow state persists before every transition
- No hidden state — agents must be able to observe all relevant state
- Adapters translate only — no business logic in adapter layer

## Security Requirements

- Trust tier enforcement (0-4) on every capability execution
- Risk scoring before high-risk actions
- Immutable audit trail (append-only)
- Approval required for `require_approval` capabilities
- Session data encryption at rest (v0.2.0+)

## 11-Plane Architecture

| Plane | Name | Status (v0.1.1) |
|-------|------|-----------------|
| 0 | Signal | Not started |
| 1 | Perception | Not started |
| 2 | AI | Not started |
| 3 | Capability | Complete (L2) |
| 4 | Workflow | Complete (L2) |
| 5 | Governance | Complete (L2) |
| 6 | Execution | Complete (L2) |
| 7 | Multi-Agent | Not started |
| 8 | Federation | Minimal |
| 9 | Supervision | Partial |
| 10 | Learning | Not started |

## 📂 Codebase References

**Core Models**: `packages/core/src/aicp/` — Capability, Workflow, Policy, ExecutionEnvelope
**Runtime Services**: `packages/runtime/src/aicp_runtime/services/` — 8 services
**CLI Commands**: `packages/cli/src/aicp_cli/` — 28 commands
**Protocol Schemas**: `spec/schemas/` — 9 JSON schemas
**Adapters**: `adapters/` — FastAPI, MCP, OpenAPI, cURL, HAR, Postman

## Related Files

- `/ARCHITECTURE.md` — 11-plane system architecture
- `/MODULE_MAP.md` — Feature-to-module mapping
- `/spec/schemas/` — Protocol JSON schemas (source of truth)
