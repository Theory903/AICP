# Financial-Grade Hardening

> How AICP moves from a strong v0.3.0 foundation to a bank/trade-grade v1.0.0 operating surface.

---

## Executive Summary

The current AICP runtime has the right primitives: execution envelopes, resumable workflows, approvals, audit logging, and a policy gate ahead of side effects. The gap to banking and trading is not a rewrite. It is a hardening program across identity, cryptography, governance, execution latency, supervision, and tenant isolation.

The most important conclusion from a repo audit is this: some gaps are real platform gaps, and some are inventory gaps in the docs. For example, `allowed_next_actions` existed in the schema but was not populated by the Python executor, while LangChain and LangGraph adapters already exist in the repository even though some docs still describe them as empty.

---

## Review Findings

### 1. Identity and trust are not production-grade yet

- Session tokens and basic auth exist.
- Principal hierarchy, DID-based identity, delegated authority chains, trust decay, and HSM-backed key handling do not.
- For finance and trading, Tier 4 sovereignty should be treated as out-of-scope. The practical ceiling is Tier 3 with mandatory approval above desk-defined thresholds.

### 2. Governance is still interpreted, not compiled

- JSON rule policies are present and usable.
- Risk scoring, anomaly detection, namespace inheritance, and compiled WASM enforcement are still missing.
- The repo already tracks the JSON-to-WASM migration as a spec gap; this now has a draft RFC in `rfcs/2026-policy-wasm-migration.md`.

### 3. Execution semantics need a finance profile

- The runtime already supports resumable workflows and approval checkpoints.
- It does not yet provide the full three-class execution engine promised by the architecture: hardened realtime reads, transactional writes with idempotency enforcement, and low-latency event streaming.
- Resource locks, duplicate-write protection, and async audit flush paths remain future work.

### 4. Audit is append-only but not yet tamper-evident

- Audit journaling and correlation IDs exist today.
- Cryptographic chaining, signed roots, and external anchoring do not.
- That matters for regulator-grade replay and post-incident forensics.

### 5. Multi-tenant support is partial, not complete

- The runtime already enforces session/tenant mismatch checks and carries tenant context.
- It does not yet provide database-level isolation, tenant-scoped registries, or per-tenant execution quotas.
- Security docs should describe this as partial enforcement, not as solved isolation.

### 6. Supervision is still a developer surface

- `/console` is useful for debugging and basic approval handling.
- It is not yet the sub-second control tower needed for regulated autonomous systems.
- Circuit breakers, live streaming, replay DAG inspection, and risk-first approval rendering remain outstanding.

### 7. Inventory drift exists in the docs

- LangChain and LangGraph adapters already exist in the repository.
- `often_follows` already influences discovery ranking.
- `allowed_next_actions` was documented as universal, but the runtime had not been populating it consistently before this change.

---

## What AICP Should Be in This Domain

AICP should not position itself as an alternative to MCP or A2A.

- MCP is the tool transport layer.
- A2A is the inter-agent communication layer.
- AICP is the governed execution, audit, workflow, and supervision layer above both.

That positioning is strongest in regulated domains because governance, approvals, trust decay, risk scoring, replay, and operator control are exactly the areas left open by the surrounding protocol ecosystem.

---

## Recommended Build Order

### Phase 0.4.0: Spec Hardening + Agent Integration

Keep the existing adapter milestone, but add a hardening lane in parallel:

1. Formalize `often_follows` semantics.
2. Formalize JSON-policy to WASM migration.
3. Make the runtime actually emit `allowed_next_actions` from explicit continuation and `often_follows` metadata.
4. Finish Python-first LangChain, LangGraph, and CrewAI adapter coverage before betting on TypeScript adapter parity.

### Phase 0.5.x: Security Hardening Track Parallel to Perception

Do not wait until v0.9.0 to begin the banking/trading foundation.

Pull forward:

1. Principal/org chain design
2. encrypted session design and storage abstraction
3. tenant-scoped persistence design
4. trust-tier decay rules
5. risk-scoring contract

Perception can still proceed, but security primitives should start here.

### Phase 0.6.0: Governance + Execution Tightening

Before autonomous finance is credible, deliver:

1. idempotency enforcement at execution-engine level
2. resource locks for concurrent mutations
3. real-time risk scoring hook for write capabilities
4. compliance gate hooks for financial namespaces

### Phase 0.7.0: Federation + Identity

Federation is where DID-based identity becomes mandatory rather than aspirational.

1. mutual DID authentication
2. signed principal chain propagation
3. tenant-aware cross-org invocation rules

### Phase 0.8.0: Supervision Before Learning

For finance, learning must remain advisory until supervision is complete.

1. live execution feed
2. approval queue with risk context
3. replay debugger
4. circuit breaker panel
5. learning outputs limited to proposals reviewed by humans

### Phase 0.9.0: Production Finance Profile

This is where high-assurance deployment features land:

1. compiled WASM policy bundles
2. HSM-backed signing and key rotation
3. cryptographically chained audit roots
4. database-level tenant isolation
5. per-tenant execution quotas and concurrency controls

### Phase 1.0.0: Regulated Autonomous Operating Surface

At v1.0.0 for this domain, AICP should provide:

1. cryptographically attributable execution
2. synchronous pre-trade governance gates
3. replayable, tamper-evident audit DAGs
4. human circuit breakers with sub-second effect
5. governed autonomous operation capped below sovereign trust

---

## Immediate Priorities

The first concrete implementation slice should stay small and foundational:

1. close spec gaps that already block consistent runtime behavior
2. align executor behavior with the documented execution contract
3. keep the repo inventory honest so roadmap decisions use real state, not stale docs

This repository change set starts that work by:

1. drafting RFCs for `often_follows` and policy compilation
2. populating `allowed_next_actions` in the executor
3. surfacing those next actions through the AI-facing `/v1/execute` contract

---

## See Also

- [`../../STATUS.md`](../../STATUS.md)
- [`../../ROADMAP.md`](../../ROADMAP.md)
- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
- [`../../rfcs/2026-often-follows-semantics.md`](../../rfcs/2026-often-follows-semantics.md)
- [`../../rfcs/2026-policy-wasm-migration.md`](../../rfcs/2026-policy-wasm-migration.md)
