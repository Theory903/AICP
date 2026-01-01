# Product Requirements Document

## Product Name

**AICP — AI Capability Protocol**

## Product Summary

AICP is a protocol and runtime model that allows AI systems to discover meaningful capabilities, understand execution constraints, track multi-step workflow state, evaluate policy, execute safely, normalize failures, and render outcomes intelligently.

It is designed for developers, platform teams, and AI infrastructure builders who want to make their systems AI-operable without relying on brittle ad hoc tool calling.

## Problem Statement

Modern AI systems are increasingly expected to perform real-world actions, yet existing integration approaches are insufficient for reliable execution.

Current problems include:

- raw endpoints exposed without semantic business meaning,
- no standard workflow model for multi-step tasks,
- inconsistent handling of pagination and long-running jobs,
- poor policy awareness,
- lack of confirmation and approval semantics,
- inconsistent or opaque failure modes,
- and no standard way to render outcomes or next steps.

As a result, AI systems can often start tasks, but cannot safely or consistently finish them.

## Target Users

### Primary Users

1. **AI infrastructure engineers** building agent platforms and orchestration systems.
2. **Backend and platform engineers** exposing existing services to AI systems.
3. **Framework and SDK maintainers** who want native integration for AI-safe actions.
4. **Product teams** building assistants, copilots, and workflow agents.

### Secondary Users

1. **Open-source contributors** adopting and extending AICP.
2. **Enterprise architects** standardizing AI execution across teams.
3. **Developer experience teams** building internal AI platforms.

## Core User Jobs

Users need to:

- expose existing actions in a form AI can understand,
- represent real workflows instead of isolated calls,
- encode permissions, confirmation, and execution rules,
- let AI reason about missing inputs and next steps,
- normalize execution outcomes,
- and integrate with existing backends quickly.

## Product Goals

### Goal 1: Make capabilities AI-readable

Capabilities should be discoverable, typed, and semantically meaningful.

### Goal 2: Make workflows AI-navigable

AI should know current step, completed steps, missing fields, and next transitions.

### Goal 3: Make execution policy-aware

The protocol must support permissions, risk, confirmation, and approval semantics.

### Goal 4: Make results machine-reasonable and human-readable

Execution outcomes should include normalized status and rendering hints.

### Goal 5: Make adoption practical

AICP should support existing backends through adapters, overlays, and generated mappings.

## Non-Goals

The initial version of AICP will **not** attempt to:

- define a global identity system,
- replace OAuth or OIDC,
- build a universal wallet or payment network,
- define a complete UI standard,
- or replace all transport protocols.

Those may become adjacent systems later, but they are not part of the initial protocol scope.

## Product Scope

### In Scope

- capability schema,
- input/output typing,
- policy metadata,
- workflow state model,
- execution result model,
- normalized errors,
- pagination model,
- async job model,
- render hints,
- introspection and discovery,
- and reference runtime behavior.

### Out of Scope for v1

- portable identity and trust system,
- memory portability,
- financial custody or tokenization,
- full-blown UI component framework,
- advanced marketplace economics,
- and protocol-level federation between organizations.

## Key Features

### 1. Capability Discovery

Expose meaningful capabilities with machine-readable descriptions.

### 2. Typed Inputs and Outputs

Support structured schemas with required fields, constraints, defaults, and enums.

### 3. Policy Metadata

Embed risk, scopes, autonomy rules, confirmation requirements, and approval thresholds.

### 4. Workflow Awareness

Track current step, completed steps, missing fields, and next possible transitions.

### 5. Standard Execution Model

Define how to request execution and what normalized outcomes look like.

### 6. Error Normalization

Convert backend-specific errors into AI-reasonable states.

### 7. Pagination Support

Standardize pagination for searchable and list-returning capabilities.

### 8. Async and Long-Running Jobs

Support pending jobs, polling, and completion semantics.

### 9. Render Hints

Provide structured guidance for displaying outcomes.

### 10. Adapter Model

Allow adoption through native adapters and existing-spec overlays.

## User Stories

### Story 1: Food Ordering

As an AI assistant platform, I want to expose restaurant search, cart creation, address selection, payment confirmation, and order placement as a workflow so that the AI can complete food ordering safely.

### Story 2: Payment Transfer

As a financial workflow provider, I want to encode transfer actions with risk and confirmation metadata so that the AI does not execute transfers blindly.

### Story 3: Form Submission

As a platform exposing forms, I want the AI to understand required fields, dependencies, validation, and submission state.

### Story 4: Ticket Booking

As a booking platform, I want multi-step booking flows to be represented clearly so that the AI can collect details, choose options, and confirm purchase correctly.

## Functional Requirements

1. The protocol must support capability discovery.
2. The protocol must support typed input and output schemas.
3. The protocol must support workflow state representation.
4. The protocol must support policy evaluation metadata.
5. The protocol must define a normalized execution result model.
6. The protocol must standardize failure representation.
7. The protocol must define pagination semantics.
8. The protocol must support async job semantics.
9. The protocol must support render hints.
10. The protocol must support extension and versioning.

## Non-Functional Requirements

- Clear versioning model.
- Backward-compatibility principles.
- Framework-agnostic core.
- Adapter-friendly design.
- Human-readable and machine-readable specification.
- Validation-friendly JSON schema definitions.
- Low cognitive overhead for adoption.

## Success Metrics

### Adoption Metrics

- number of adapters built,
- number of example integrations,
- documentation completion and usage,
- GitHub stars, forks, and contributors,
- and number of external tools/platforms exposing AICP-compatible capabilities.

### Product Quality Metrics

- schema validation success rate,
- clarity of error normalization,
- adapter conformance,
- time-to-first-adoption,
- and successful completion rate for multi-step workflows in reference demos.

## Risks

- over-expanding v1 scope,
- becoming too abstract to adopt,
- confusing overlap with existing protocols,
- inconsistent adapter behavior,
- and poor first examples.

## Mitigation Strategy

- keep v1 small and crisp,
- publish clear positioning,
- make reference demos concrete,
- enforce schema validation,
- and use RFC-based governance.
