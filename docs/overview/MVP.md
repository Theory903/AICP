# AICP MVP Scope

## Purpose

The goal of the MVP is not to prove every future vision. It is to prove the core idea:

> that AICP can make AI systems understand and safely complete multi-step real-world tasks better than raw tool calling.

## MVP Success Criteria

The MVP is successful if it proves all of the following:

1. A capability can be represented meaningfully.
2. A multi-step workflow can be modeled clearly.
3. Policy metadata can influence execution.
4. Execution results and failures can be normalized.
5. Pagination and async states can be represented consistently.
6. A real example app can use AICP end to end.

## Included in MVP

### Core Protocol

- capability schema,
- input schema,
- output schema,
- policy schema,
- workflow state schema,
- result schema,
- error schema,
- pagination schema,
- render hints.

### Runtime

- basic registry,
- planner stub or planner contract,
- policy evaluator contract,
- executor contract,
- result normalization,
- validation tooling.

### Delivery

- documentation site,
- example reference flows,
- TypeScript reference implementation,
- CLI for validation and inspection.

## Example Workflows for MVP

1. **Food ordering**
2. **Payments transfer**
3. **Form filling**
4. **Ticket booking**

These four are enough because together they demonstrate:

- search and pagination,
- stateful progression,
- approvals and confirmations,
- validation-heavy forms,
- async and long-running steps,
- and render-aware outputs.

## Excluded from MVP

- portable identity,
- universal login,
- cross-client memory layer,
- enterprise IAM integration,
- wallet systems,
- multi-org federation,
- advanced UI framework,
- fully autonomous planning engine,
- all language adapters,
- and distributed trust or signing.

## MVP Deliverables

- `VISION.md`
- `PRD.md`
- `MVP.md`
- `USE_CASES.md`
- `ARCHITECTURE.md`
- `TECH_SPEC.md`
- `SECURITY.md`
- `ROADMAP.md`
- initial schemas,
- TypeScript runtime,
- Express and NestJS examples,
- and documentation site.

## What MVP Must Demonstrate Publicly

### Demo 1: Food Ordering

AI understands the workflow, missing address, payment confirmation, and final order placement.

### Demo 2: Payment Transfer

AI sees that a payment requires confirmation and treats it as high-risk.

### Demo 3: Form Filling

AI recognizes required fields, invalid entries, and submit readiness.

### Demo 4: Ticket Booking

AI completes multi-step booking with state and validation awareness.

## Why This MVP Is Correct

It is narrow enough to ship, broad enough to matter, and strong enough to communicate the protocol's value clearly.
