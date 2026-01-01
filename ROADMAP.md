# AICP Roadmap

## Guiding Principle

AICP should grow in layers, not in chaos.

The roadmap is designed so that every release adds meaningful capability without compromising clarity or adoption.

## Phase 0: Foundation

### Deliverables

- [x] Vision document (`docs/VISION.md`)
- [x] PRD (`docs/PRD.md`)
- [x] MVP definition (`docs/MVP.md`)
- [x] Use case narratives (`docs/USE_CASES.md`)
- [x] Architecture doc (`docs/ARCHITECTURE.md`)
- [x] Technical spec (`docs/TECH_SPEC.md`)
- [ ] Security model draft
- [x] Repository setup

### Outcome

A coherent public project foundation.

## Phase 1: Protocol Core (v0.1)

### Deliverables

- [ ] capability schema (`spec/schemas/`)
- [ ] policy schema
- [ ] workflow state schema
- [ ] execution result schema
- [ ] error schema
- [ ] pagination schema
- [ ] render schema
- [ ] discovery contract
- [ ] documentation site
- [ ] TypeScript reference implementation

### Outcome

The protocol becomes real, inspectable, and testable.

## Phase 2: Reference Runtime

### Deliverables

- [ ] registry
- [ ] validator
- [ ] executor contract
- [ ] policy evaluator contract
- [ ] result normalization
- [ ] CLI tooling
- [ ] conformance tests

### Outcome

AICP becomes executable rather than only descriptive.

## Phase 3: Example Systems

### Deliverables

- [ ] food ordering example
- [ ] payment transfer example
- [ ] form filling example
- [ ] ticket booking example

### Outcome

The real value of workflow-aware AI execution becomes visible.

## Phase 4: Framework Adapters

### First Targets

- [ ] Express
- [ ] NestJS
- [ ] Spring Boot
- [ ] LangChain

### Outcome

Adoption becomes practical for real systems.

## Phase 5: Expansion

### Deliverables

- [ ] Next.js adapter
- [ ] Go adapter
- [ ] Rust adapter
- [ ] OpenAPI ingest/export
- [ ] MCP adapter

### Outcome

AICP begins to sit above a broader ecosystem.

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
