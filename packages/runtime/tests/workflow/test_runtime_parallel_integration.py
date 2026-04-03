"""Integration tests: DefaultWorkflowRuntime executing parallel and wait_event steps.

RED phase — these tests MUST FAIL until the runtime dispatch is wired.

Design:
- parallel step: step dict has metadata={"type": "parallel", "parallel_steps": [...], "failure_policy": "..."}
  and capability_name="" (empty string, allowed by the model).
- wait_event step: step dict has metadata={"type": "wait_event", "event_name": "...", "timeout_ms": ...}
  and capability_name="" (empty).
- A normal capability step has no metadata["type"] (or metadata["type"] == "capability") and
  capability_name set to the real capability.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.workflow_runtime import StepStatus, WorkflowStatus


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class FakeCapabilityProvider:
    """A minimal fake provider that records calls and returns canned results."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, dict]] = []
        self._results: dict[str, Any] = {}

    def set_result(self, capability_name: str, result: Any) -> None:
        self._results[capability_name] = result

    def set_error(self, capability_name: str, error: str) -> None:
        self._results[capability_name] = Exception(error)

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        self.calls.append((capability_name, arguments, context or {}))
        val = self._results.get(capability_name, {"status": "ok"})
        if isinstance(val, Exception):
            raise val
        return val


def make_runtime(
    provider: FakeCapabilityProvider | None = None,
) -> DefaultWorkflowRuntime:
    return DefaultWorkflowRuntime(
        capability_provider=provider or FakeCapabilityProvider(),
    )


# ---------------------------------------------------------------------------
# create_workflow: relaxed capability_name requirement
# ---------------------------------------------------------------------------


class TestCreateWorkflowRelaxedCapabilityName:
    """create_workflow must NOT raise for non-capability step types."""

    @pytest.mark.asyncio
    async def test_parallel_step_without_capability_name_is_accepted(self) -> None:
        rt = make_runtime()
        # This should NOT raise WorkflowError
        wf = await rt.create_workflow(
            name="test_parallel",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "a", "capability_name": "cap.a"},
                            {"id": "b", "capability_name": "cap.b"},
                        ],
                    },
                }
            ],
        )
        assert wf is not None
        assert len(wf.steps) == 1
        assert wf.steps[0].metadata["type"] == "parallel"

    @pytest.mark.asyncio
    async def test_wait_event_step_without_capability_name_is_accepted(self) -> None:
        rt = make_runtime()
        wf = await rt.create_workflow(
            name="test_wait_event",
            steps=[
                {
                    "id": "step_evt",
                    "capability_name": "",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "order.placed",
                        "timeout_ms": 1000,
                    },
                }
            ],
        )
        assert wf is not None
        assert wf.steps[0].metadata["type"] == "wait_event"

    @pytest.mark.asyncio
    async def test_mixed_workflow_capability_and_parallel_steps(self) -> None:
        rt = make_runtime()
        wf = await rt.create_workflow(
            name="mixed",
            steps=[
                {"id": "s1", "capability_name": "cap.first"},
                {
                    "id": "s2",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "a", "capability_name": "cap.a"},
                        ],
                    },
                },
                {"id": "s3", "capability_name": "cap.last"},
            ],
        )
        assert len(wf.steps) == 3

    @pytest.mark.asyncio
    async def test_normal_step_without_capability_name_still_raises(self) -> None:
        """Steps with no type metadata still require capability_name."""
        from aicp.interfaces.workflow_runtime import WorkflowError

        rt = make_runtime()
        with pytest.raises(WorkflowError):
            await rt.create_workflow(
                name="bad",
                steps=[{"id": "s1"}],  # no capability_name, no type metadata
            )


# ---------------------------------------------------------------------------
# execute_step: parallel dispatch
# ---------------------------------------------------------------------------


class TestExecuteParallelStep:
    """execute_step must dispatch to ParallelStepExecutor for type=parallel steps."""

    @pytest.mark.asyncio
    async def test_parallel_step_executes_all_sub_steps(self) -> None:
        provider = FakeCapabilityProvider()
        provider.set_result("cap.a", {"value": "A"})
        provider.set_result("cap.b", {"value": "B"})

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="parallel_wf",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "a", "capability_name": "cap.a"},
                            {"id": "b", "capability_name": "cap.b"},
                        ],
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        assert result.success is True
        # Both sub-steps should have been called
        called_caps = [c[0] for c in provider.calls]
        assert "cap.a" in called_caps
        assert "cap.b" in called_caps

    @pytest.mark.asyncio
    async def test_parallel_step_result_contains_sub_step_outcomes(self) -> None:
        provider = FakeCapabilityProvider()
        provider.set_result("cap.x", {"x": 1})
        provider.set_result("cap.y", {"y": 2})

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="parallel_wf",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "x", "capability_name": "cap.x"},
                            {"id": "y", "capability_name": "cap.y"},
                        ],
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        assert result.success is True
        # result.result should be the ParallelStepResult or serialised outcomes
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_parallel_step_advances_workflow_on_success(self) -> None:
        provider = FakeCapabilityProvider()
        provider.set_result("cap.a", "done")
        provider.set_result("cap.b", "done")

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="parallel_wf",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "a", "capability_name": "cap.a"},
                            {"id": "b", "capability_name": "cap.b"},
                        ],
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        assert result.success is True
        wf_state = await rt.get_workflow(wf.id)
        assert wf_state is not None
        assert wf_state.status == WorkflowStatus.COMPLETED
        assert wf_state.steps[0].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel_step_fail_fast_marks_step_failed(self) -> None:
        provider = FakeCapabilityProvider()
        provider.set_result("cap.ok", "fine")
        provider.set_error("cap.fail", "something went wrong")

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="parallel_wf_fail",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "failure_policy": "fail_fast",
                        "parallel_steps": [
                            {"id": "ok", "capability_name": "cap.ok"},
                            {"id": "fail", "capability_name": "cap.fail"},
                        ],
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        # fail_fast: overall result is failure
        assert result.success is False
        wf_state = await rt.get_workflow(wf.id)
        assert wf_state is not None
        assert wf_state.steps[0].status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_parallel_step_wait_all_collects_all_outcomes(self) -> None:
        provider = FakeCapabilityProvider()
        provider.set_result("cap.ok", "fine")
        provider.set_error("cap.fail", "oops")

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="parallel_wf_wait_all",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "failure_policy": "wait_all",
                        "parallel_steps": [
                            {"id": "ok", "capability_name": "cap.ok"},
                            {"id": "fail", "capability_name": "cap.fail"},
                        ],
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        # wait_all: still reports failure when any sub-step failed
        assert result.success is False

    @pytest.mark.asyncio
    async def test_parallel_step_with_following_capability_step(self) -> None:
        """After parallel step completes, the next capability step executes normally."""
        provider = FakeCapabilityProvider()
        provider.set_result("cap.a", "a_done")
        provider.set_result("cap.final", {"status": "final"})

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="mixed_wf",
            steps=[
                {
                    "id": "step_par",
                    "capability_name": "",
                    "metadata": {
                        "type": "parallel",
                        "parallel_steps": [
                            {"id": "a", "capability_name": "cap.a"},
                        ],
                    },
                },
                {"id": "step_final", "capability_name": "cap.final"},
            ],
        )

        result1 = await rt.execute_step(wf.id)
        assert result1.success is True

        result2 = await rt.execute_step(wf.id)
        assert result2.success is True

        called_caps = [c[0] for c in provider.calls]
        assert "cap.a" in called_caps
        assert "cap.final" in called_caps


# ---------------------------------------------------------------------------
# execute_step: wait_event dispatch
# ---------------------------------------------------------------------------


class TestExecuteWaitEventStep:
    """execute_step must dispatch to EventWaiter for type=wait_event steps."""

    @pytest.mark.asyncio
    async def test_wait_event_step_suspends_workflow_status(self) -> None:
        """Executing a wait_event step should set workflow to WAITING_EVENT."""
        rt = make_runtime()
        wf = await rt.create_workflow(
            name="event_wf",
            steps=[
                {
                    "id": "step_evt",
                    "capability_name": "",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "order.placed",
                        "timeout_ms": 200,
                    },
                }
            ],
        )

        # Publish the event concurrently so we don't block
        async def publish_later() -> None:
            await asyncio.sleep(0.05)
            await rt.publish_event(wf.id, "order.placed", {"order_id": "123"})

        task = asyncio.ensure_future(publish_later())
        result = await rt.execute_step(wf.id)
        await task

        assert result.success is True

    @pytest.mark.asyncio
    async def test_wait_event_step_timeout_returns_failure(self) -> None:
        """If no event arrives, execute_step should return a failure result."""
        rt = make_runtime()
        wf = await rt.create_workflow(
            name="event_wf_timeout",
            steps=[
                {
                    "id": "step_evt",
                    "capability_name": "",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "never.arrives",
                        "timeout_ms": 50,
                    },
                }
            ],
        )

        result = await rt.execute_step(wf.id)

        assert result.success is False
        assert "timeout" in (result.error or "").lower() or result.error is not None

    @pytest.mark.asyncio
    async def test_wait_event_step_delivers_payload_in_result(self) -> None:
        """The event payload should be available in the StepResult."""
        rt = make_runtime()
        wf = await rt.create_workflow(
            name="event_wf_payload",
            steps=[
                {
                    "id": "step_evt",
                    "capability_name": "",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "data.ready",
                        "timeout_ms": 500,
                    },
                }
            ],
        )

        payload = {"key": "value", "count": 42}

        async def publish_later() -> None:
            await asyncio.sleep(0.02)
            await rt.publish_event(wf.id, "data.ready", payload)

        task = asyncio.ensure_future(publish_later())
        result = await rt.execute_step(wf.id)
        await task

        assert result.success is True
        assert result.result is not None

    @pytest.mark.asyncio
    async def test_wait_event_followed_by_capability_step(self) -> None:
        """After wait_event completes, subsequent capability steps execute."""
        provider = FakeCapabilityProvider()
        provider.set_result("cap.process", {"processed": True})

        rt = make_runtime(provider)
        wf = await rt.create_workflow(
            name="event_then_cap",
            steps=[
                {
                    "id": "step_evt",
                    "capability_name": "",
                    "metadata": {
                        "type": "wait_event",
                        "event_name": "trigger",
                        "timeout_ms": 500,
                    },
                },
                {"id": "step_cap", "capability_name": "cap.process"},
            ],
        )

        async def publish_later() -> None:
            await asyncio.sleep(0.02)
            await rt.publish_event(wf.id, "trigger", {})

        task = asyncio.ensure_future(publish_later())
        result1 = await rt.execute_step(wf.id)
        await task

        assert result1.success is True

        result2 = await rt.execute_step(wf.id)
        assert result2.success is True
        assert provider.calls[0][0] == "cap.process"


# ---------------------------------------------------------------------------
# publish_event API
# ---------------------------------------------------------------------------


class TestPublishEventAPI:
    """DefaultWorkflowRuntime must expose publish_event(workflow_id, name, payload)."""

    @pytest.mark.asyncio
    async def test_publish_event_method_exists_on_runtime(self) -> None:
        rt = make_runtime()
        assert hasattr(rt, "publish_event"), (
            "DefaultWorkflowRuntime must have publish_event()"
        )

    @pytest.mark.asyncio
    async def test_publish_event_for_unknown_workflow_does_not_raise(self) -> None:
        rt = make_runtime()
        # Should not raise even if no waiter is registered
        await rt.publish_event("nonexistent_wf_id", "some.event", {"key": "val"})
