"""Level 3 conformance tests for DefaultWorkflowRuntime.

Compliance Level 3 — Event-Driven Orchestration requirements:
- L2 (Resumable Workflows) PLUS:
  - Parallel steps (fork/join)
  - wait_for_event with timeout
  - Loop steps (for-each and while)
  - Subflow invocation
  - YAML DSL round-trip to runtime execution

These tests run the actual DefaultWorkflowRuntime end-to-end and verify
that each L3 scenario produces the correct outcome.
"""

from __future__ import annotations

import asyncio
import pytest

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.workflow_runtime import WorkflowStatus


# ---------------------------------------------------------------------------
# Shared fake provider
# ---------------------------------------------------------------------------


class FakeProvider:
    """Minimal capability provider for conformance testing."""

    def __init__(self, results=None):
        self._results = list(results or [])
        self.calls: list[tuple[str, dict]] = []

    async def execute(
        self,
        capability_name: str,
        arguments: dict,
        context: dict | None = None,
        **kwargs,
    ):
        self.calls.append((capability_name, arguments))
        idx = len(self.calls) - 1
        if idx < len(self._results):
            return self._results[idx]
        return {"ok": True, "capability": capability_name}

    async def get_capability(self, name: str):
        return None

    async def has_capability(self, name: str) -> bool:
        return False


def make_runtime(results=None):
    provider = FakeProvider(results=results)
    return DefaultWorkflowRuntime(provider), provider


# ---------------------------------------------------------------------------
# L3-1: Parallel steps (fork/join)
# ---------------------------------------------------------------------------


class TestL3Parallel:
    """L3 conformance: parallel step execution."""

    @pytest.mark.asyncio
    async def test_parallel_step_executes_all_substeps(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parallel_conformance",
            steps=[
                {
                    "id": "par_step",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {
                                "id": "task_a",
                                "capability_name": "task.a",
                                "arguments": {},
                            },
                            {
                                "id": "task_b",
                                "capability_name": "task.b",
                                "arguments": {},
                            },
                            {
                                "id": "task_c",
                                "capability_name": "task.c",
                                "arguments": {},
                            },
                        ],
                        "failure_policy": "wait_all",
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        capability_names = [c[0] for c in provider.calls]
        assert "task.a" in capability_names
        assert "task.b" in capability_names
        assert "task.c" in capability_names

    @pytest.mark.asyncio
    async def test_parallel_fail_fast_on_first_failure(self):
        """fail_fast: workflow step fails when any sub-step fails."""
        runtime, provider = make_runtime()

        # Patch provider to fail on first call
        async def fail_first(cap, args, **kw):
            raise RuntimeError("forced failure")

        provider.execute = fail_first

        wf = await runtime.create_workflow(
            name="parallel_fail_fast",
            steps=[
                {
                    "id": "par_fail",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {
                                "id": "will_fail",
                                "capability_name": "will.fail",
                                "arguments": {},
                            },
                            {
                                "id": "wont_run",
                                "capability_name": "wont.run",
                                "arguments": {},
                            },
                        ],
                        "failure_policy": "fail_fast",
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_parallel_workflow_advances_after_success(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parallel_advance",
            steps=[
                {
                    "id": "par",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {
                                "id": "step_xa",
                                "capability_name": "x.a",
                                "arguments": {},
                            },
                        ],
                    },
                },
                {
                    "id": "next",
                    "capability_name": "after.parallel",
                    "arguments": {},
                },
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert result.next is not None
        assert result.next.get("step_id") == "next"


# ---------------------------------------------------------------------------
# L3-2: Event-driven wait_event with timeout
# ---------------------------------------------------------------------------


class TestL3WaitEvent:
    """L3 conformance: wait_for_event step."""

    @pytest.mark.asyncio
    async def test_wait_event_receives_event(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="event_driven_conformance",
            steps=[
                {
                    "id": "wait_step",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "order.confirmed",
                        "timeout_ms": 2000,
                    },
                }
            ],
        )

        # Publish the event shortly after starting the wait
        async def publish_after_delay():
            await asyncio.sleep(0.05)
            await runtime.publish_event(wf.id, "order.confirmed", {"order_id": "o1"})

        asyncio.create_task(publish_after_delay())
        result = await runtime.execute_step(wf.id)

        assert result.success is True
        assert result.result is not None
        assert result.result.get("order_id") == "o1"

    @pytest.mark.asyncio
    async def test_wait_event_times_out(self):
        runtime, _ = make_runtime()

        wf = await runtime.create_workflow(
            name="timeout_conformance",
            steps=[
                {
                    "id": "wait_timeout",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "never.happens",
                        "timeout_ms": 50,  # very short timeout
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is False
        assert "timeout" in (result.error or "").lower() or result.error is not None

    @pytest.mark.asyncio
    async def test_publish_event_after_wait_completes(self):
        """publish_event on a workflow with no waiter is a safe no-op."""
        runtime, _ = make_runtime()

        wf = await runtime.create_workflow(
            name="no_waiter",
            steps=[
                {
                    "id": "cap_step",
                    "capability_name": "do.something",
                    "arguments": {},
                }
            ],
        )

        # Should not raise even though no waiter is registered
        await runtime.publish_event(wf.id, "some.event", {"x": 1})


# ---------------------------------------------------------------------------
# L3-3: Loop steps (for-each and while)
# ---------------------------------------------------------------------------


class TestL3Loop:
    """L3 conformance: loop step execution."""

    @pytest.mark.asyncio
    async def test_foreach_loop_iterates_all_items(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="foreach_conformance",
            steps=[
                {
                    "id": "loop_step",
                    "capability_name": "process.item",
                    "arguments": {},
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "items_variable": "items",
                        },
                    },
                }
            ],
        )
        wf.context["items"] = ["a", "b", "c"]

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 3
        # Each call injects `item` into arguments
        items_seen = [args.get("item") for _, args in provider.calls]
        assert items_seen == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_while_loop_runs_until_exit(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="while_conformance",
            steps=[
                {
                    "id": "while_step",
                    "capability_name": "check.condition",
                    "arguments": {},
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "exit_condition": "False",  # always keep running
                            "max_iterations": 3,
                        },
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 3

    @pytest.mark.asyncio
    async def test_loop_exits_immediately_with_true_condition(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="exit_immediately",
            steps=[
                {
                    "id": "early_exit_loop",
                    "capability_name": "do.once",
                    "arguments": {},
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "exit_condition": "True",  # exit after first run (post-check)
                        },
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 1  # runs exactly once (do-while semantics)

    @pytest.mark.asyncio
    async def test_foreach_loop_advances_workflow(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="foreach_advance",
            steps=[
                {
                    "id": "loop_s",
                    "capability_name": "proc",
                    "arguments": {},
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "things"},
                    },
                },
                {
                    "id": "after_loop",
                    "capability_name": "finalize",
                    "arguments": {},
                },
            ],
        )
        wf.context["things"] = [1, 2]

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert result.next is not None
        assert result.next.get("step_id") == "after_loop"


# ---------------------------------------------------------------------------
# L3-4: Subflow invocation
# ---------------------------------------------------------------------------


class TestL3Subflow:
    """L3 conformance: subflow step execution."""

    @pytest.mark.asyncio
    async def test_subflow_executes_child_steps(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parent_conformance",
            steps=[
                {
                    "id": "sf_step",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child_flow",
                        "subflow_steps": [
                            {
                                "id": "cs1",
                                "capability_name": "child.action",
                                "arguments": {},
                            }
                        ],
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert any("child.action" in c[0] for c in provider.calls)

    @pytest.mark.asyncio
    async def test_subflow_parent_completes(self):
        runtime, _ = make_runtime()

        wf = await runtime.create_workflow(
            name="parent_completes",
            steps=[
                {
                    "id": "sf",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child",
                        "subflow_steps": [
                            {"id": "c1", "capability_name": "x.y", "arguments": {}}
                        ],
                    },
                }
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        updated = await runtime.get_workflow(wf.id)
        assert updated is not None
        assert updated.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_subflow_then_next_step(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="subflow_chain",
            steps=[
                {
                    "id": "sf",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child",
                        "subflow_steps": [
                            {"id": "c1", "capability_name": "child.op", "arguments": {}}
                        ],
                    },
                },
                {
                    "id": "parent_final",
                    "capability_name": "parent.final",
                    "arguments": {},
                },
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert result.next is not None
        assert result.next.get("step_id") == "parent_final"


# ---------------------------------------------------------------------------
# L3-5: YAML DSL round-trip
# ---------------------------------------------------------------------------


class TestL3DSLRoundTrip:
    """L3 conformance: YAML DSL parses into a runnable workflow."""

    def test_dsl_parallel_workflow_parses(self):
        from aicp_runtime.workflow.dsl import WorkflowDSLParser  # type: ignore[import]

        yaml_text = """
name: parallel_dsl_test
description: DSL parallel test
steps:
  - id: par_step
    type: parallel
    parallel_steps:
      - capability_name: task.one
      - capability_name: task.two
    parallel_failure_policy: wait_all
  - id: after_par
    capability_name: finalize.step
"""
        wf_state = WorkflowDSLParser().parse(yaml_text)
        assert wf_state.name == "parallel_dsl_test"
        steps = wf_state.steps
        assert len(steps) == 2
        par = steps[0]
        assert par.metadata["type"] == "parallel"
        assert len(par.metadata["parallel_steps"]) == 2

    def test_dsl_event_workflow_parses(self):
        from aicp_runtime.workflow.dsl import WorkflowDSLParser  # type: ignore[import]

        yaml_text = """
name: event_dsl_test
steps:
  - id: wait_step
    type: wait_event
    wait_for_event: payment.received
    timeout_ms: 3000
  - id: after_event
    capability_name: confirm.payment
"""
        wf_state = WorkflowDSLParser().parse(yaml_text)
        steps = wf_state.steps
        assert steps[0].metadata["type"] == "wait_event"
        assert steps[0].metadata["wait_for_event"] == "payment.received"

    def test_dsl_loop_workflow_parses(self):
        from aicp_runtime.workflow.dsl import WorkflowDSLParser  # type: ignore[import]

        yaml_text = """
name: loop_dsl_test
steps:
  - id: loop_step
    type: loop
    capability_name: process.item
    loop_condition:
      items_variable: order_items
      max_iterations: 50
"""
        wf_state = WorkflowDSLParser().parse(yaml_text)
        steps = wf_state.steps
        assert steps[0].metadata["type"] == "loop"
        assert steps[0].metadata["loop_condition"]["items_variable"] == "order_items"

    @pytest.mark.asyncio
    async def test_dsl_sequential_workflow_executes(self):
        from aicp_runtime.workflow.dsl import WorkflowDSLParser  # type: ignore[import]

        yaml_text = """
name: dsl_sequential_execution
steps:
  - id: step_one
    capability_name: action.one
  - id: step_two
    capability_name: action.two
"""
        wf_state = WorkflowDSLParser().parse(yaml_text)
        provider = FakeProvider()
        runtime = DefaultWorkflowRuntime(provider)

        wf = await runtime.create_workflow(
            name=wf_state.name,
            description=wf_state.description,
            steps=[
                {
                    "id": s.id,
                    "capability_name": s.capability_name,
                    "arguments": s.arguments,
                    "metadata": s.metadata,
                }
                for s in wf_state.steps
            ],
        )

        result1 = await runtime.execute_step(wf.id)
        assert result1.success is True

        result2 = await runtime.execute_step(wf.id)
        assert result2.success is True

        final = await runtime.get_workflow(wf.id)
        assert final is not None
        assert final.status == WorkflowStatus.COMPLETED
        assert len(provider.calls) == 2
