# Changelog

All notable changes to AICP are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0-dev] — 2026-04-03 — Phase 2: Orchestration (In Progress)

### Added

- **Parallel step execution** — `DefaultWorkflowRuntime` now dispatches `type:parallel` steps to `ParallelStepExecutor` with `fail_fast` and `wait_all` join strategies
- **Event-driven flows** — `DefaultWorkflowRuntime` now dispatches `type:wait_event` steps to `EventWaiter`; supports configurable timeout
- **`publish_event()` API** — `DefaultWorkflowRuntime.publish_event(workflow_id, name, payload)` delivers external events to waiting workflows
- **DSL key compatibility** — parallel steps read `parallel_failure_policy` (DSL) or `failure_policy` (direct); wait steps read `wait_for_event` (DSL) or `event_name` (direct)
- **16 new runtime parallel integration tests** — `packages/runtime/tests/workflow/test_runtime_parallel_integration.py`
- **11 new DSL→runtime integration tests** — `packages/runtime/tests/workflow/test_dsl_runtime_integration.py`

### Changed

- `create_workflow()` relaxed — steps with `metadata.type` in `{parallel, wait_event, branch, loop}` no longer require `capability_name`
- Total tests: **638** (was 611)

### In Progress

- Loop support (for-each, while, repeat-until)
- Subflow invocation
- `compensation_policy` at workflow level in spec
- Compliance Level 3 conformance tests
- `publish_event` HTTP endpoint on `WorkflowService`

---

## [0.2.0] — 2026-04-03 — Phase 1: AI Core (Complete)

### Added

- **`AICPlanner`** — multi-step planner with `PlanStep` / `PlannerOutput` models; POST `/v1/plan` endpoint
- **`AICJudge`** — execution result evaluator with `JudgeError`; POST `/v1/judge` endpoint
- **`IntentRouter`** — routes natural language intents to capabilities with `RoutingDestination`; POST `/v1/route` endpoint
- **5-layer `MemoryStore`** — working, episodic, semantic, skill, and environmental memory layers
- **`MetaMemory`** — token-aware context budget manager with `MemorySnapshot`
- **5 Cognitive Protocols** — UX, SWE, Ops, Research, Finance protocol families
- **`SessionService.update_memory` / `get_memory`** — cross-session memory persistence
- **26 L4 HTTP conformance tests** — plan response, judge response, route response, plan-judge round-trip

### Changed

- Total tests: **611** (was 445)
- Compliance Level advanced to L4 (AI Planning Support)

---

## [0.1.1-alpha] — 2026-04-03 — Phase 0: Foundation (Complete)

### Added

- **11 JSON schemas** in `spec/schemas/` — capability, workflow, workflow-dsl, policy, execution-result, approval-request, approval-decision, audit-entry, session, discovery, error
- **Full spec fixture coverage** — valid + invalid examples for all 11 schemas in `spec/tests/`
- **8 runtime services** — execution, approvals, workflows, sessions, discovery, audit, interactions, provider health
- **30+ API endpoints** across 13 route groups including `/v1` AI action surface
- **3 persistence backends** — in-memory, file (JSON/JSONL), SQLite (WAL mode, 7 tables)
- **28 CLI commands** — `aicp run` with inline approval prompt, `--yes`, `--no-input`, `--verbose`; full workflow, policy, approval, and import command sets
- **6 working adapters** — FastAPI, MCP server, MCP adapter, OpenAPI, cURL importer, HAR importer, Postman importer
- **Agent console UI** at `/console` — 840-line self-contained HTML dashboard
- **TypeScript Core SDK** — built and distributable, Compliance Level 0
- **Approval auto-resume** — intent matching resumes workflows after human approval
- **Dev server** — `aicp dev` mounts AICP routes on existing user apps

### Changed

- Total tests: **445**
- Compliance Level: L2 (Resumable Workflows)
