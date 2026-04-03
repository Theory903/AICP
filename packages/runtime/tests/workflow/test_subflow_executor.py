"""Tests for SubflowExecutor — unit tests (TDD: written before implementation)."""

from __future__ import annotations

import pytest

from aicp_runtime.workflow.subflow import (
    SubflowError,
    SubflowExecutor,
    SubflowResult,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeWorkflowRuntime:
    """Minimal WorkflowRuntime stub for testing SubflowExecutor."""

    def __init__(self, should_fail: bool = False, auto_complete: bool = True):
        self._should_fail = should_fail
        self._auto_complete = auto_complete
        self.created: list[dict] = []
        self.executed: list[str] = []
        # wf_id → fake state
        self._states: dict[str, dict] = {}

    async def create_workflow(self, name: str, description: str = "", steps=None):
        import uuid
        wf_id = str(uuid.uuid4())
        state = {
            "id": wf_id,
            "name": name,
            "status": "running" if self._auto_complete else "created",
        }
        self._states[wf_id] = state
        self.created.append({"id": wf_id, "name": name})
        return _FakeWFState(wf_id, "completed" if self._auto_complete else "created")

    async def get_workflow(self, wf_id: str):
        state = self._states.get(wf_id)
        if state is None:
            return None
        return _FakeWFState(wf_id, state["status"])

    async def execute_step(self, wf_id: str, arguments=None):
        self.executed.append(wf_id)
        if self._should_fail:
            return _FakeStepResult(success=False, error="subflow step failed")
        # Mark workflow as completed after one step
        if wf_id in self._states:
            self._states[wf_id]["status"] = "completed"
        return _FakeStepResult(success=True)


class _FakeWFState:
    def __init__(self, wf_id: str, status: str):
        self.id = wf_id
        self.status = status

    @property
    def is_complete(self) -> bool:
        return self.status in ("completed", "failed", "cancelled")


class _FakeStepResult:
    def __init__(self, success: bool, error: str | None = None):
        self.success = success
        self.error = error


# ---------------------------------------------------------------------------
# SubflowResult
# ---------------------------------------------------------------------------


class TestSubflowResult:
    def test_success(self):
        r = SubflowResult(success=True, workflow_id="wf_123")
        assert r.success is True
        assert r.workflow_id == "wf_123"
        assert r.error is None

    def test_failure(self):
        r = SubflowResult(success=False, workflow_id="wf_123", error="failed")
        assert r.success is False
        assert r.error == "failed"


# ---------------------------------------------------------------------------
# SubflowExecutor construction
# ---------------------------------------------------------------------------


class TestSubflowExecutorInit:
    def test_requires_runtime(self):
        runtime = FakeWorkflowRuntime()
        ex = SubflowExecutor(runtime)
        assert ex is not None


# ---------------------------------------------------------------------------
# Basic subflow invocation
# ---------------------------------------------------------------------------


class TestSubflowInvocation:
    @pytest.mark.asyncio
    async def test_creates_and_runs_subflow(self):
        runtime = FakeWorkflowRuntime(auto_complete=True)
        executor = SubflowExecutor(runtime)

        step = {
            "id": "subflow_step",
            "metadata": {
                "type": "subflow",
                "subflow_name": "child_workflow",
                "subflow_steps": [
                    {"id": "s1", "capability_name": "do.thing", "arguments": {}}
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
        runtime = FakeWorkflowRuntime(should_fail=True, auto_complete=False)
        executor = SubflowExecutor(runtime)

        step = {
            "id": "subflow_step",
            "metadata": {
                "type": "subflow",
                "subflow_name": "failing_child",
                "subflow_steps": [
                    {"id": "s1", "capability_name": "do.thing", "arguments": {}}
                ],
            },
        }
        result = await executor.execute(step, context={})

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_missing_subflow_name_raises(self):
        runtime = FakeWorkflowRuntime()
        executor = SubflowExecutor(runtime)

        step = {
            "id": "subflow_step",
            "metadata": {
                "type": "subflow",
                # no subflow_name
                "subflow_steps": [],
            },
        }
        with pytest.raises(SubflowError, match="subflow_name"):
            await executor.execute(step, context={})

    @pytest.mark.asyncio
    async def test_missing_subflow_steps_raises(self):
        runtime = FakeWorkflowRuntime()
        executor = SubflowExecutor(runtime)

        step = {
            "id": "subflow_step",
            "metadata": {
                "type": "subflow",
                "subflow_name": "child",
                # no subflow_steps
            },
        }
        with pytest.raises(SubflowError, match="subflow_steps"):
            await executor.execute(step, context={})

    @pytest.mark.asyncio
    async def test_context_passed_to_subflow(self):
        runtime = FakeWorkflowRuntime()
        executor = SubflowExecutor(runtime)

        step = {
            "id": "subflow_step",
            "metadata": {
                "type": "subflow",
                "subflow_name": "child",
                "subflow_steps": [
                    {"id": "s1", "capability_name": "do.thing", "arguments": {}}
                ],
            },
        }
        context = {"user_id": "u123", "order_id": "o456"}
        result = await executor.execute(step, context=context)

        assert result.success is True
        # Context should be carried into the subflow name or first call
        assert runtime.created[0]["name"] == "child"
