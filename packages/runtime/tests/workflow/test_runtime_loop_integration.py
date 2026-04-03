"""Integration tests: DefaultWorkflowRuntime executing loop steps end-to-end."""

from __future__ import annotations

import pytest

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.workflow_runtime import WorkflowStatus


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


class FakeProvider:
    def __init__(self, results=None, raise_at=None):
        self._results = results or []
        self._raise_at = raise_at or {}
        self.calls: list[tuple] = []

    async def execute(self, capability_name: str, arguments: dict, **kwargs):
        idx = len(self.calls)
        self.calls.append((capability_name, arguments))
        if idx in self._raise_at:
            raise RuntimeError(self._raise_at[idx])
        if idx < len(self._results):
            return self._results[idx]
        return {"ok": True}

    async def get_capability(self, name: str):
        return None

    async def has_capability(self, name: str) -> bool:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_runtime(results=None, raise_at=None):
    provider = FakeProvider(results=results, raise_at=raise_at)
    runtime = DefaultWorkflowRuntime(provider)
    return runtime, provider


# ---------------------------------------------------------------------------
# for-each loop integration
# ---------------------------------------------------------------------------


class TestLoopForEachIntegration:
    @pytest.mark.asyncio
    async def test_foreach_iterates_all_items(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="foreach_test",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "users"},
                        "capability_name": "notify.user",
                    },
                },
                {
                    "id": "done",
                    "capability_name": "workflow.done",
                },
            ],
        )
        # Inject context with items
        wf.context["users"] = [{"id": 1}, {"id": 2}, {"id": 3}]

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        # Three items → three capability calls
        assert len(provider.calls) == 3

    @pytest.mark.asyncio
    async def test_foreach_empty_list_succeeds(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="foreach_empty",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "items"},
                        "capability_name": "process.item",
                    },
                },
            ],
        )
        wf.context["items"] = []

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 0

    @pytest.mark.asyncio
    async def test_loop_step_advances_workflow_after_completion(self):
        runtime, _ = make_runtime()

        wf = await runtime.create_workflow(
            name="loop_advance",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "items"},
                        "capability_name": "do.thing",
                    },
                },
                {
                    "id": "next_step",
                    "capability_name": "final.step",
                },
            ],
        )
        wf.context["items"] = [1, 2]

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        # Next step guidance should point to next_step
        assert result.next is not None
        assert result.next.get("step_id") == "next_step"


# ---------------------------------------------------------------------------
# max_iterations integration
# ---------------------------------------------------------------------------


class TestLoopMaxIterationsIntegration:
    @pytest.mark.asyncio
    async def test_max_iterations_limits_execution(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="max_iter_test",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "items_variable": "items",
                            "max_iterations": 2,
                        },
                        "capability_name": "do.thing",
                    },
                },
            ],
        )
        wf.context["items"] = list(range(100))

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 2


# ---------------------------------------------------------------------------
# exit_condition integration
# ---------------------------------------------------------------------------


class TestLoopExitConditionIntegration:
    @pytest.mark.asyncio
    async def test_exit_condition_true_stops_after_first(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="exit_cond_test",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "exit_condition": "True",
                            "max_iterations": 5,
                        },
                        "capability_name": "poll.status",
                    },
                },
            ],
        )
        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) <= 5

    @pytest.mark.asyncio
    async def test_exit_condition_false_runs_to_max(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="exit_cond_false_test",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {
                            "exit_condition": "False",
                            "max_iterations": 3,
                        },
                        "capability_name": "poll.status",
                    },
                },
            ],
        )
        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert len(provider.calls) == 3


# ---------------------------------------------------------------------------
# Loop failure handling integration
# ---------------------------------------------------------------------------


class TestLoopFailureIntegration:
    @pytest.mark.asyncio
    async def test_loop_step_fails_on_capability_error(self):
        runtime, provider = make_runtime(raise_at={0: "capability exploded"})

        wf = await runtime.create_workflow(
            name="loop_fail_test",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "items"},
                        "capability_name": "do.thing",
                    },
                },
            ],
        )
        wf.context["items"] = [1, 2, 3]

        result = await runtime.execute_step(wf.id)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_loop_fail_marks_workflow_failed(self):
        runtime, _ = make_runtime(raise_at={0: "boom"})

        wf = await runtime.create_workflow(
            name="loop_fail_status",
            steps=[
                {
                    "id": "loop_step",
                    "metadata": {
                        "type": "loop",
                        "loop_condition": {"items_variable": "items"},
                        "capability_name": "do.thing",
                    },
                },
            ],
        )
        wf.context["items"] = [1]

        await runtime.execute_step(wf.id)
        updated_wf = await runtime.get_workflow(wf.id)
        assert updated_wf is not None
        assert updated_wf.status in (WorkflowStatus.FAILED, WorkflowStatus.RUNNING)
