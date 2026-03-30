# AICP Roadmap

## Guiding Principle

AICP should grow in layers, not in chaos.

## The product sequence

1. Make It Real
2. Make It Safe
3. Make It Adoptable Everywhere
4. Make It Intelligent

## Phase 0: Narrative & Protocol Reset

### Goals
- freeze naming
- freeze product stack
- freeze core abstractions
- align docs to new positioning

### Deliverables
- final positioning statement
- canonical terminology
- protocol object inventory
- architecture diagram
- updated roadmap
- product stack doc
- shipped-schema inventory vs deferred schema areas

### Exit criteria
- all overview docs use the same language
- AIUI removed from primary docs
- Protocol / Runtime / Connect / Studio clearly separated
- shipped protocol artifacts are explicitly distinguished from roadmap protocol areas

## Phase 1: Make It Real

### Goal
Have a working AICP Runtime that can expose and execute capabilities reliably.

### Build
- runtime server
- capability registry
- discovery endpoint
- execution endpoint
- typed I/O validation
- normalized execution results
- structured errors with fix hints
- basic continuation hints
- OpenAPI mapper
- FastAPI mapper
- CLI for map/serve/discover/execute

### Key commands
- `aicp map openapi`
- `aicp map fastapi`
- `aicp serve`
- `aicp discover`
- `aicp execute`

### Exit criteria
- import an existing API into AICP in minutes
- discover capabilities from runtime
- execute capabilities with normalized results
- all core schemas validated by conformance tests
- at least 2 strong examples work end-to-end

## Phase 2: Make It Safe

### Goal
Turn the runtime from a demo into something enterprises can trust.

### Build
- policy engine
- policy outcomes: allow / deny / ask / require_approval / limit
- ApprovalRequest object
- ApprovalDecision object
- paused execution state
- workflow pause and resume
- approval endpoints
- immutable audit journal
- session-level execution journal
- actor/identity context basics
- threshold-based approvals
- structured policy reasons

### Add
- GET /approval-requests
- POST /approval-requests/{id}/approve
- POST /approval-requests/{id}/reject
- POST /workflows/{id}/resume

### Exit criteria
- a payment/order/booking flow can pause for approval and resume correctly
- all major actions are journaled
- policy decisions are inspectable
- failure and approval trails are auditable

## Phase 3: Make It Adoptable Everywhere

### Goal
Meet teams where their systems already are.

### Build
- Postman mapper
- HAR mapper
- cURL mapper
- MCP bridge
- Python SDK polish
- TypeScript SDK polish
- LangChain adapter
- CrewAI adapter
- stronger packaging and install flow
- better codegen/types from schemas

### Exit criteria
- users can onboard from at least 5 source types
- adapters work with major agent ecosystems
- reference SDKs feel production-grade
- import-to-runtime flow is smooth

## Phase 4: Make It Intelligent

### Goal
Make AICP better at guidance, recovery, and orchestration.

### Build
- continuation graph
- rollback graph
- branch-aware workflows
- richer render packets
- session workspace state
- multi-agent coordination primitives
- cost/risk metadata
- confidence/ambiguity signaling
- richer identity and delegation model
- RBAC and enterprise policy packs

### Later
- GraphQL mapper
- gRPC mapper
- deeper SaaS integrations
- advanced Studio features

### Exit criteria
- runtime can guide agents through complex multi-step flows
- workflows have recovery branches
- capability graph improves planning quality
- enterprise governance model is robust

## Workstreams

- Product and docs
- Protocol and schemas
- Runtime
- Connect
- Developer experience
- Studio
- Examples
- Integration and QA

## What to deprioritize

- too many brand variations
- fancy Studio UI before runtime governance exists
- GraphQL/gRPC before core mappers are solid
- overdesigning multi-agent features too early
- novel notation experiments unless they directly help adoption
