# AICP Roadmap

## Guiding Principle

AICP should grow in layers, not in chaos.

**Every feature is designed for AI ease-of-use.** Even mini-LLMs should process AICP without complex reasoning.

## Phase 0: Foundation ✓ (Complete)

### Deliverables

- [x] Vision document (`docs/VISION.md`)
- [x] PRD (`docs/PRD.md`)
- [x] MVP definition (`docs/MVP.md`)
- [x] Use case narratives (`docs/USE_CASES.md`)
- [x] Architecture doc (`docs/ARCHITECTURE.md`)
- [x] Technical spec (`docs/TECH_SPEC.md`)
- [x] Agentic Experience design (`docs/AGENTIC_EXPERIENCE.md`)
- [ ] Security model draft
- [x] Repository setup

### Outcome

A coherent public project foundation.

## Phase 1: Agentic Protocol Core (v0.1)

### Focus: AI-First Response Design

Every response includes:
- `next` with suggested actions
- structured errors with `fix_hint`
- workflow state
- policy explicitly stated

### Deliverables

- [ ] capability schema (with `next` hints)
- [ ] policy schema (with autonomous_execution flag)
- [ ] workflow state schema
- [ ] execution result schema (with required `next` field)
- [ ] error schema (with `fix_hint` field)
- [ ] pagination schema
- [ ] render schema
- [ ] discovery contract (`GET /.well-known/aicp`)
- [ ] documentation site
- [ ] TypeScript reference implementation

### Outcome

The protocol becomes real, inspectable, testable — and **AI-friendly**.

## Phase 2: Reference Runtime

### Deliverables

- registry
- validator
- executor contract
- policy evaluator contract
- result normalization
- CLI tooling
- conformance tests

### Outcome

AICP becomes executable rather than only descriptive.

## Phase 3: Example Systems

### Deliverables

- food ordering example
- payment transfer example
- form filling example
- ticket booking example

### Outcome

The real value of workflow-aware AI execution becomes visible.

## Phase 4: Framework Adapters

### First Targets

- Express
- NestJS
- Spring Boot
- LangChain

### Outcome

Adoption becomes practical for real systems.

## Phase 5: Expansion

### Deliverables

- Next.js adapter
- Go adapter
- Rust adapter
- OpenAPI ingest/export
- MCP adapter

### Outcome

AICP begins to sit above a broader ecosystem.

## Phase 6: Advanced Features

### Potential Features

- richer planner contract,
- approval workflows,
- async orchestration,
- dry-run standard,
- signed manifests,
- policy receipts,
- identity-layer integration.

### Outcome

AICP matures into a broad execution standard.

## Deferred for Later Consideration

- universal AI login,
- portable identity,
- cross-client shared memory,
- agent marketplace,
- wallet systems,
- multi-tenant federated trust.

## Release Philosophy

Each release should satisfy three conditions:

1. clearer than the previous one,
2. more useful than the previous one,
3. still small enough to be adopted.

## Version Timeline

| Version | Focus | Target |
|---------|-------|--------|
| 0.1 | Protocol core schemas | Q2 2026 |
| 0.2 | Reference runtime | Q3 2026 |
| 0.3 | Example systems | Q4 2026 |
| 1.0 | First stable release | Q1 2027 |

## Success Criteria

Each phase is considered successful when:

- documentation is complete for delivered features,
- reference implementations pass conformance tests,
- at least one working example demonstrates the capability,
- community feedback is collected and incorporated.
