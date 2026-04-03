"""Integration tests: DefaultWorkflowRuntime executing subflow steps end-to-end."""

from __future__ import annotations

import pytest

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.workflow_runtime import WorkflowStatus


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


class FakeProvider:
    def __init__(self, results=None):
        self._results = results or []
        self.calls: list[tuple] = []

    async def execute(
        self,
        capability_name: str,
        arguments: dict,
        context: dict | None = None,
        **kwargs,
    ):
        idx = len(self.calls)
        self.calls.append((capability_name, arguments))
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


def make_runtime(results=None):
    provider = FakeProvider(results=results)
    runtime = DefaultWorkflowRuntime(provider)
    return runtime, provider


# ---------------------------------------------------------------------------
# Basic subflow integration
# ---------------------------------------------------------------------------


class TestSubflowIntegration:
    @pytest.mark.asyncio
    async def test_subflow_step_executes_child_workflow(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parent_workflow",
            steps=[
                {
                    "id": "subflow_step",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child_workflow",
                        "subflow_steps": [
                            {
                                "id": "child_step_1",
                                "capability_name": "child.action",
                                "arguments": {},
                            }
                        ],
                    },
                },
                {
                    "id": "parent_continuation",
                    "capability_name": "parent.finalize",
                    "arguments": {},
                },
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        # child.action should have been executed
        assert any("child.action" in str(c) for c in provider.calls)

    @pytest.mark.asyncio
    async def test_subflow_step_advances_workflow(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parent_workflow",
            steps=[
                {
                    "id": "subflow_step",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child",
                        "subflow_steps": [
                            {
                                "id": "cs1",
                                "capability_name": "do.thing",
                                "arguments": {},
                            }
                        ],
                    },
                },
                {
                    "id": "next_step",
                    "capability_name": "final.step",
                    "arguments": {},
                },
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        assert result.next is not None
        assert result.next.get("step_id") == "next_step"

    @pytest.mark.asyncio
    async def test_subflow_step_result_in_workflow_context(self):
        runtime, provider = make_runtime()

        wf = await runtime.create_workflow(
            name="parent_workflow",
            steps=[
                {
                    "id": "subflow_step",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child",
                        "subflow_steps": [
                            {
                                "id": "cs1",
                                "capability_name": "do.thing",
                                "arguments": {},
                            }
                        ],
                    },
                },
            ],
        )

        result = await runtime.execute_step(wf.id)
        assert result.success is True
        updated_wf = await runtime.get_workflow(wf.id)
        # The subflow execution result should be accessible
        assert updated_wf is not None


# ---------------------------------------------------------------------------
# Subflow workflow status integration
# ---------------------------------------------------------------------------


class TestSubflowWorkflowStatus:
    @pytest.mark.asyncio
    async def test_parent_workflow_completes_after_subflow(self):
        runtime, _ = make_runtime()

        wf = await runtime.create_workflow(
            name="parent",
            steps=[
                {
                    "id": "subflow_step",
                    "metadata": {
                        "type": "subflow",
                        "subflow_name": "child",
                        "subflow_steps": [
                            {"id": "cs1", "capability_name": "x.y", "arguments": {}}
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
