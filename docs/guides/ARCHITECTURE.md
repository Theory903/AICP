# AICP Architecture

## Overview

AICP is designed as a layered protocol and runtime architecture. The protocol defines the contracts. The runtime operationalizes them. Adapters expose those contracts through existing systems. Clients and agents consume them to understand and complete tasks.

## Architectural Principles

1. **Spec first**
   The protocol contract must be defined before implementation details drift.

2. **Framework-agnostic core**
   The core domain model must not depend on one backend framework.

3. **Thin adapters**
   Adapters should translate existing systems into AICP concepts rather than duplicating core logic.

4. **Policy as a first-class layer**
   Permissions and approvals are part of the model, not post-processing.

5. **Workflow state is explicit**
   AICP systems must represent step and state, not hide them in prompts.

## High-Level Architecture

```
Client / Agent
↓
AICP Discovery + Planning Layer
↓
Capability Registry
↓
Policy Evaluation Layer
↓
Workflow Runtime
↓
Execution Layer
↓
Underlying APIs / Services / Tools
↓
Result Normalization + Render Layer
```

## Main Components

### 1. Capability Registry

Stores and serves capability definitions.

Responsibilities:

- capability discovery,
- type reference lookup,
- metadata organization,
- and schema retrieval.

### 2. Planner / Resolver

Maps user intent or agent context to relevant capabilities and possible workflows.

Responsibilities:

- discover relevant capabilities,
- propose sequences,
- identify missing information,
- and support multi-step planning.

### 3. Policy Engine

Evaluates whether an action is allowed.

Responsibilities:

- scope checks,
- confirmation requirements,
- approval logic,
- autonomy limits,
- risk decisions.

### 4. Workflow Runtime

Tracks multi-step state.

Responsibilities:

- current step,
- completed steps,
- next transitions,
- missing fields,
- and workflow continuity.

### 5. Executor

Runs the selected capability against underlying systems.

Responsibilities:

- execute action,
- adapt transport,
- capture raw response,
- and return structured results.

### 6. Result Normalizer

Converts backend-specific outputs into AICP-standard results.

Responsibilities:

- map statuses,
- normalize errors,
- normalize pagination,
- handle async jobs,
- and preserve useful debug context.

### 7. Render Layer

Transforms result and render hints into client-consumable presentation instructions.

Responsibilities:

- produce summaries,
- identify important fields,
- choose view types,
- and communicate next steps.

## Data Flow Example

For a payment transfer:

1. Client submits user intent.
2. Planner identifies `payments.transfer`.
3. Policy engine evaluates risk and scope.
4. Workflow runtime checks whether prerequisite information exists.
5. Executor invokes the underlying transfer capability.
6. Result normalizer structures the outcome.
7. Render layer returns a receipt-ready result.

## Architectural Boundaries

### Core Protocol Boundary

Defines capabilities, workflows, policies, statuses, and render semantics.

### Runtime Boundary

Handles execution, planning, evaluation, and normalization.

### Adapter Boundary

Maps AICP into or out of specific systems such as Express, NestJS, Spring Boot, LangChain, or OpenAPI.

## Recommended Initial Implementation Strategy

- TypeScript monorepo,
- spec directory for schemas,
- core package for protocol models,
- runtime package for execution logic,
- adapter packages for initial frameworks,
- docs-first publishing.

## Directory Structure

```
aicp/
├── spec/                    # Protocol source of truth (JSON schemas)
├── packages/                # Reference implementations
│   ├── core/              # Protocol domain models
│   ├── runtime/           # Execution & orchestration
│   └── cli/               # Command-line tools
├── sdks/                   # Language-specific SDKs
├── adapters/               # Framework & protocol adapters
├── mcp/                    # MCP Server implementations
├── examples/               # Working reference applications
├── docs/                   # Human-readable documentation
├── rfcs/                   # Protocol change proposals
└── governance/             # Contribution guidelines
```

## Key Design Patterns

### Spec-First

The protocol is defined in `/spec` before runtime behavior drifts.

### Reference Implementation

`/packages/core` and `/packages/runtime` are reference implementations, not the only way.

### Thin Adapters

Adapters translate framework semantics to AICP, not reinvent AICP internally.

### No Mega-Utils

No `utils.ts` or `helpers.py`. Domain logic lives in domain-named modules.

### Single Responsibility

Each module does one thing: capability validation, policy evaluation, workflow transitions.
