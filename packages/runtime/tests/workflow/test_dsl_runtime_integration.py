"""Integration tests: YAML DSL → WorkflowDSLParser → DefaultWorkflowRuntime.

These tests verify the full round-trip:
  1. Author a YAML workflow string
  2. Parse it with WorkflowDSLParser
  3. Register the resulting WorkflowState in DefaultWorkflowRuntime
  4. Execute all steps end-to-end

Design constraints:
  - DefaultWorkflowRuntime does not natively accept a pre-built WorkflowState.
    We inject it directly into _workflows (internal dict) to simulate
    a load-from-persistence path. The WorkflowService (Phase 2 follow-on)
    will expose a proper API for this; this is a testing seam.
"""

from __future__ import annotations

from typing import Any

import pytest

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.workflow_runtime import WorkflowStatus
from aicp_runtime.workflow.dsl import WorkflowDSLParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._results: dict[str, Any] = {}

    def set_result(self, cap: str, val: Any) -> None:
        self._results[cap] = val

    def set_error(self, cap: str, msg: str) -> None:
        self._results[cap] = RuntimeError(msg)

    async def execute(self, capability_name: str, arguments: dict, context: dict | None = None, **kw: Any) -> Any:
        self.calls.append(capability_name)
        val = self._results.get(capability_name, {"ok": True})
        if isinstance(val, Exception):
            raise val
        return val


def make_runtime(provider: FakeProvider | None = None) -> DefaultWorkflowRuntime:
    return DefaultWorkflowRuntime(capability_provider=provider or FakeProvider())


def inject_workflow(rt: DefaultWorkflowRuntime, wf_state: Any) -> None:
    """Inject a pre-built WorkflowState into the runtime."""
    rt._workflows[wf_state.id] = wf_state


# ---------------------------------------------------------------------------
# DSL → Runtime: capability steps
# ---------------------------------------------------------------------------


class TestDSLCapabilitySteps:
    """Parse YAML with capability steps and execute them via the runtime."""

    @pytest.mark.asyncio
    async def test_single_capability_step_from_dsl(self) -> None:
        provider = FakeProvider()
        provider.set_result("greet.user", {"message": "Hello!"})

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: greeting_flow
steps:
  - id: say_hello
    type: capability
    capability_name: greet.user
    arguments:
      name: Alice
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        result = await rt.execute_step(wf.id)

        assert result.success is True
        assert provider.calls == ["greet.user"]

    @pytest.mark.asyncio
    async def test_sequential_capability_steps_from_dsl(self) -> None:
        provider = FakeProvider()
        provider.set_result("step.a", "A")
        provider.set_result("step.b", "B")
        provider.set_result("step.c", "C")

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: sequential
steps:
  - id: s_a
    capability_name: step.a
  - id: s_b
    capability_name: step.b
  - id: s_c
    capability_name: step.c
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        for _ in range(3):
            r = await rt.execute_step(wf.id)
            assert r.success is True

        assert provider.calls == ["step.a", "step.b", "step.c"]
        final = rt._workflows[wf.id]
        assert final.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dsl_workflow_preserves_arguments(self) -> None:
        provider = FakeProvider()
        captured: list[dict] = []

        async def fake_execute(cap: str, args: dict, context: dict | None = None, **kw: Any) -> Any:
            captured.append(dict(args))
            return {"done": True}

        provider.execute = fake_execute  # type: ignore[method-assign]

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: args_flow
steps:
  - id: s1
    capability_name: do.thing
    arguments:
      key: value
      count: 42
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        result = await rt.execute_step(wf.id)

        assert result.success is True
        assert captured[0] == {"key": "value", "count": 42}


# ---------------------------------------------------------------------------
# DSL → Runtime: parallel steps
# ---------------------------------------------------------------------------


class TestDSLParallelSteps:
    """Parse YAML with parallel steps and execute them via the runtime."""

    @pytest.mark.asyncio
    async def test_parallel_step_from_dsl_executes_all_sub_steps(self) -> None:
        provider = FakeProvider()
        provider.set_result("fetch.orders", [1, 2, 3])
        provider.set_result("fetch.inventory", {"stock": 10})

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: parallel_fetch
steps:
  - id: fetch_all
    type: parallel
    parallel_steps:
      - id: orders
        capability_name: fetch.orders
      - id: inventory
        capability_name: fetch.inventory
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        result = await rt.execute_step(wf.id)

        assert result.success is True
        assert set(provider.calls) == {"fetch.orders", "fetch.inventory"}

    @pytest.mark.asyncio
    async def test_parallel_then_capability_step_from_dsl(self) -> None:
        provider = FakeProvider()
        provider.set_result("cap.a", "a")
        provider.set_result("cap.finalize", "done")

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: parallel_then_cap
steps:
  - id: par_step
    type: parallel
    parallel_steps:
      - id: a
        capability_name: cap.a
  - id: finalize
    capability_name: cap.finalize
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        r1 = await rt.execute_step(wf.id)
        assert r1.success is True

        r2 = await rt.execute_step(wf.id)
        assert r2.success is True

        assert "cap.a" in provider.calls
        assert "cap.finalize" in provider.calls
        assert rt._workflows[wf.id].status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel_step_fail_fast_policy_from_dsl(self) -> None:
        provider = FakeProvider()
        provider.set_result("cap.ok", "ok")
        provider.set_error("cap.bad", "network error")

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: parallel_fail
steps:
  - id: par_step
    type: parallel
    parallel_failure_policy: fail_fast
    parallel_steps:
      - id: good
        capability_name: cap.ok
      - id: bad
        capability_name: cap.bad
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        result = await rt.execute_step(wf.id)

        assert result.success is False


# ---------------------------------------------------------------------------
# DSL → Runtime: wait_event steps
# ---------------------------------------------------------------------------


class TestDSLWaitEventSteps:
    """Parse YAML with wait_event steps and execute them via the runtime."""

    @pytest.mark.asyncio
    async def test_wait_event_step_from_dsl_resolves(self) -> None:
        import asyncio

        rt = make_runtime()
        parser = WorkflowDSLParser()

        yaml_text = """
name: event_flow
steps:
  - id: wait_trigger
    type: wait_event
    wait_for_event: order.placed
    timeout_ms: 500
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        async def publish_later() -> None:
            await asyncio.sleep(0.03)
            await rt.publish_event(wf.id, "order.placed", {"order_id": "ORD-1"})

        task = asyncio.ensure_future(publish_later())
        result = await rt.execute_step(wf.id)
        await task

        assert result.success is True
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_wait_event_then_capability_step_from_dsl(self) -> None:
        import asyncio

        provider = FakeProvider()
        provider.set_result("process.order", {"processed": True})

        rt = make_runtime(provider)
        parser = WorkflowDSLParser()

        yaml_text = """
name: event_then_process
steps:
  - id: wait_order
    type: wait_event
    wait_for_event: order.ready
    timeout_ms: 500
  - id: process
    capability_name: process.order
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        async def publish_later() -> None:
            await asyncio.sleep(0.02)
            await rt.publish_event(wf.id, "order.ready", {})

        task = asyncio.ensure_future(publish_later())
        r1 = await rt.execute_step(wf.id)
        await task

        assert r1.success is True

        r2 = await rt.execute_step(wf.id)
        assert r2.success is True
        assert "process.order" in provider.calls

    @pytest.mark.asyncio
    async def test_wait_event_timeout_from_dsl(self) -> None:
        rt = make_runtime()
        parser = WorkflowDSLParser()

        yaml_text = """
name: event_timeout
steps:
  - id: wait_ghost
    type: wait_event
    wait_for_event: ghost.event
    timeout_ms: 50
"""
        wf = parser.parse(yaml_text)
        inject_workflow(rt, wf)

        result = await rt.execute_step(wf.id)

        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# DSL round-trip
# ---------------------------------------------------------------------------


class TestDSLRoundTrip:
    """to_yaml → parse → to_yaml should be stable."""

    @pytest.mark.asyncio
    async def test_roundtrip_capability_workflow(self) -> None:
        parser = WorkflowDSLParser()
        yaml1 = """
name: simple
description: A simple workflow
steps:
  - id: step1
    capability_name: cap.do
    arguments:
      x: 1
"""
        wf1 = parser.parse(yaml1)
        yaml2 = parser.to_yaml(wf1)
        wf2 = parser.parse(yaml2)

        assert wf2.name == wf1.name
        assert wf2.description == wf1.description
        assert len(wf2.steps) == len(wf1.steps)
        assert wf2.steps[0].capability_name == wf1.steps[0].capability_name
        assert wf2.steps[0].arguments == wf1.steps[0].arguments

    @pytest.mark.asyncio
    async def test_roundtrip_parallel_workflow(self) -> None:
        parser = WorkflowDSLParser()
        yaml1 = """
name: parallel
steps:
  - id: par
    type: parallel
    parallel_steps:
      - id: a
        capability_name: cap.a
      - id: b
        capability_name: cap.b
"""
        wf1 = parser.parse(yaml1)
        yaml2 = parser.to_yaml(wf1)
        wf2 = parser.parse(yaml2)

        assert len(wf2.steps) == 1
        assert wf2.steps[0].metadata["type"] == "parallel"
        assert len(wf2.steps[0].metadata["parallel_steps"]) == 2
