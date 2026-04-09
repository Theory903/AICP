"""Phase 4 Integration Tests — subflow wiring and workflow schema validation."""

from __future__ import annotations

import pytest

from aicp_runtime.workflow.subflow import SubflowExecutor, SubflowError


class FakeWorkflow:
    """Minimal Fake workflow object for testing subflow execution."""

    def __init__(self, wf_id: str, should_fail: bool = False):
        self.id = wf_id
        self.is_complete = False
        self._should_fail = should_fail
        self._steps_executed = 0

    def mark_complete(self):
        self.is_complete = True


class FakeRuntime:
    """Minimal WorkflowRuntime for testing subflow execution."""

    def __init__(self, should_fail: bool = False):
        self._should_fail = should_fail
        self.created: list[dict] = []
        self._workflows: dict[str, FakeWorkflow] = {}

    async def create_workflow(self, name: str, description: str = "", steps=None):
        import uuid
        wf_id = f"wf_{uuid.uuid4().hex[:8]}"
        wf = FakeWorkflow(wf_id, self._should_fail)
        self._workflows[wf_id] = wf
        self.created.append({"id": wf_id, "name": name})
        return wf

    async def execute_step(self, wf_id: str, arguments=None):
        wf = self._workflows.get(wf_id)
        if wf is None:
            return type("obj", (object,), {"success": False, "error": "not found"})()
        if self._should_fail:
            wf.mark_complete()
            return type("obj", (object,), {"success": False, "error": "step failed"})()
        wf._steps_executed += 1
        if wf._steps_executed >= 1:
            wf.mark_complete()
        return type("obj", (object,), {"success": True})()

    async def get_workflow(self, wf_id: str):
        return self._workflows.get(wf_id)


class TestSubflowWiring:
    """Tests for subflow wiring in the Python runtime."""

    @pytest.mark.asyncio
    async def test_subflow_registers_and_runs(self):
        runtime = FakeRuntime()
        executor = SubflowExecutor(runtime)

        step = {
            "id": "call_subflow",
            "metadata": {
                "type": "subflow",
                "subflow_name": "child_workflow",
                "subflow_steps": [
                    {"id": "s1", "capability_name": "do_thing", "arguments": {}},
                ],
            },
        }

        result = await executor.execute(step, context={})

        assert result.success is True
        assert result.workflow_id is not None
        assert len(runtime.created) == 1
        assert runtime.created[0]["name"] == "child_workflow"

    @pytest.mark.asyncio
    async def test_subflow_failure_propagates(self):
        runtime = FakeRuntime(should_fail=True)
        executor = SubflowExecutor(runtime)

        step = {
            "id": "fail_subflow",
            "metadata": {
                "type": "subflow",
                "subflow_name": "failing_child",
                "subflow_steps": [
                    {"id": "s1", "capability_name": "do_thing", "arguments": {}},
                ],
            },
        }

        result = await executor.execute(step, context={})

        assert result.success is False
        assert result.error is not None


class TestWorkflowSchemaValidation:
    """Tests for workflow schema validation."""

    @pytest.mark.asyncio
    async def test_subflow_step_requires_metadata(self):
        runtime = FakeRuntime()
        executor = SubflowExecutor(runtime)

        step = {"id": "step1"}

        with pytest.raises(SubflowError):
            await executor.execute(step, context={})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
