# Changelog

All notable changes to AICP are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — 2026-04-03 — Phase 2: Orchestration (Complete)

### Added

- **Parallel step execution** — `DefaultWorkflowRuntime` dispatches `type:parallel` steps to `ParallelStepExecutor` with `fail_fast` and `wait_all` join strategies
- **Event-driven flows** — `DefaultWorkflowRuntime` dispatches `type:wait_event` steps to `EventWaiter`; supports configurable timeout
- **Loop support** — `LoopStepExecutor` wired into runtime: for-each (items_variable), while (exit_condition), max_iterations cap, do-while post-check semantics
- **Subflow invocation** — `SubflowExecutor` wired into runtime: creates child workflow via parent runtime, drives to completion, propagates failures
- **`publish_event()` API** — `DefaultWorkflowRuntime.publish_event(workflow_id, name, payload)` delivers external events to waiting workflows
- **`publish_event` HTTP endpoint** — `POST /workflows/{workflow_id}/events` with `PublishEventRequest(name, payload)` model
- **`compensation_policy`** — added at workflow level in spec schema
- **17 L3 conformance tests** — parallel, wait_event, loop, subflow, DSL round-trip
- **16 new runtime parallel integration tests** — `packages/runtime/tests/workflow/test_runtime_parallel_integration.py`
- **11 new DSL→runtime integration tests** — `packages/runtime/tests/workflow/test_dsl_runtime_integration.py`
- **Loop integration tests** — `test_loop_executor.py`, `test_runtime_loop_integration.py`
- **Subflow integration tests** — `test_subflow_executor.py`, `test_runtime_subflow_integration.py`

### Changed

- `create_workflow()` relaxed — steps with `metadata.type` in `{parallel, wait_event, branch, loop}` no longer require `capability_name`
- `"subflow"` added to `_NON_CAPABILITY_STEP_TYPES` in `DefaultWorkflowRuntime`
- DSL key compatibility: reads both `wait_for_event` / `parallel_failure_policy` (DSL keys) and `event_name` / `failure_policy` (direct keys)
- Total tests: **692** (was 611)

### Fixed

- `SubflowExecutor` infinite loop: checks `child_wf.is_complete` before entering polling loop
- `FakeProvider.execute()` signature in integration tests to accept 3rd positional `context` arg
- `WorkflowDSL` → `WorkflowDSLParser` import in conformance tests
- `provider.call_count` → `len(provider.calls)` in loop integration tests

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
