"""Tests for LoopStepExecutor — unit tests (TDD: written before implementation)."""

from __future__ import annotations

import pytest

from aicp_runtime.workflow.loop import (
    LoopExecutionError,
    LoopStepExecutor,
    LoopStepResult,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeProvider:
    """Minimal capability provider stub."""

    def __init__(self, results: list | None = None, raise_after: int = -1):
        self._results = results or []
        self._raise_after = raise_after
        self.call_count = 0
        self.call_args: list[tuple] = []

    async def execute(self, capability_name: str, arguments: dict, **kwargs):
        self.call_args.append((capability_name, arguments))
        idx = self.call_count
        self.call_count += 1
        if self._raise_after >= 0 and idx >= self._raise_after:
            raise RuntimeError(f"Simulated failure at call {idx}")
        if idx < len(self._results):
            return self._results[idx]
        return {"ok": True}


# ---------------------------------------------------------------------------
# LoopStepResult
# ---------------------------------------------------------------------------


class TestLoopStepResult:
    def test_success_true_when_no_errors(self):
        r = LoopStepResult(success=True, iterations=3)
        assert r.success is True
        assert r.iterations == 3
        assert r.error is None

    def test_success_false_on_failure(self):
        r = LoopStepResult(success=False, iterations=1, error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_results_list_default_empty(self):
        r = LoopStepResult(success=True, iterations=0)
        assert r.results == []

    def test_results_stored(self):
        r = LoopStepResult(success=True, iterations=2, results=[{"a": 1}, {"b": 2}])
        assert len(r.results) == 2


# ---------------------------------------------------------------------------
# LoopStepExecutor — basic construction
# ---------------------------------------------------------------------------


class TestLoopStepExecutorInit:
    def test_requires_capability_provider(self):
        p = FakeProvider()
        ex = LoopStepExecutor(p)
        assert ex is not None

    def test_max_iterations_default(self):
        p = FakeProvider()
        ex = LoopStepExecutor(p)
        assert ex.default_max_iterations > 0


# ---------------------------------------------------------------------------
# for-each iteration over items_variable
# ---------------------------------------------------------------------------


class TestForEachLoop:
    @pytest.mark.asyncio
    async def test_iterates_over_items(self):
        provider = FakeProvider(results=[{"done": True}] * 3)
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "notify.user",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {
                    "items_variable": "users",
                },
            },
        }
        context = {"users": [{"id": 1}, {"id": 2}, {"id": 3}]}

        result = await executor.execute(step, context=context)

        assert result.success is True
        assert result.iterations == 3
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_empty_items_runs_zero_iterations(self):
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "notify.user",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {
                    "items_variable": "users",
                },
            },
        }
        result = await executor.execute(step, context={"users": []})

        assert result.success is True
        assert result.iterations == 0
        assert provider.call_count == 0

    @pytest.mark.asyncio
    async def test_items_variable_missing_raises(self):
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "notify.user",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {"items_variable": "missing_key"},
            },
        }
        with pytest.raises(LoopExecutionError, match="missing_key"):
            await executor.execute(step, context={})

    @pytest.mark.asyncio
    async def test_per_item_context_injected(self):
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "process.item",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {"items_variable": "items"},
            },
        }
        context = {"items": [{"val": "a"}, {"val": "b"}]}
        await executor.execute(step, context=context)

        # Each call should include the current item in the args
        assert provider.call_count == 2
        # The item should appear in the args of each call
        first_args = provider.call_args[0][1]
        assert "item" in first_args or "val" in str(first_args)


# ---------------------------------------------------------------------------
# max_iterations guard
# ---------------------------------------------------------------------------


class TestMaxIterations:
    @pytest.mark.asyncio
    async def test_respects_max_iterations(self):
        # 10 items but max_iterations=3 → only 3 run
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "do.thing",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {
                    "items_variable": "items",
                    "max_iterations": 3,
                },
            },
        }
        context = {"items": list(range(10))}
        result = await executor.execute(step, context=context)

        assert result.success is True
        assert result.iterations == 3
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_default_max_iterations_is_enforced(self):
        """Should not run more than default_max_iterations iterations."""
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        # Create a huge list — executor must cap at default_max_iterations
        big_list = list(range(10_000))
        step = {
            "id": "loop_step",
            "capability_name": "do.thing",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {"items_variable": "items"},
            },
        }
        result = await executor.execute(step, context={"items": big_list})

        assert provider.call_count <= executor.default_max_iterations


# ---------------------------------------------------------------------------
# while-style loop with exit_condition
# ---------------------------------------------------------------------------


class TestExitConditionLoop:
    @pytest.mark.asyncio
    async def test_exit_condition_string_false_keeps_running(self):
        """exit_condition='False' → run until max_iterations."""
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "poll.status",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {
                    "exit_condition": "False",
                    "max_iterations": 4,
                },
            },
        }
        result = await executor.execute(step, context={})
        assert result.iterations == 4

    @pytest.mark.asyncio
    async def test_exit_condition_string_true_stops_immediately(self):
        """exit_condition='True' → stop after first iteration."""
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "poll.status",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {
                    "exit_condition": "True",
                    "max_iterations": 10,
                },
            },
        }
        result = await executor.execute(step, context={})
        # Should stop after 1 iteration (exit immediately after first)
        assert result.iterations >= 1
        assert result.iterations < 10


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


class TestLoopFailure:
    @pytest.mark.asyncio
    async def test_capability_failure_stops_loop(self):
        provider = FakeProvider(raise_after=1)
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "do.thing",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {"items_variable": "items"},
            },
        }
        result = await executor.execute(step, context={"items": [1, 2, 3]})

        assert result.success is False
        assert result.error is not None
        # Stopped on second item (index 1)
        assert result.iterations <= 2

    @pytest.mark.asyncio
    async def test_invalid_loop_condition_raises(self):
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "do.thing",
            "arguments": {},
            "metadata": {
                "type": "loop",
                "loop_condition": {},  # no items_variable or exit_condition
            },
        }
        with pytest.raises(LoopExecutionError):
            await executor.execute(step, context={})

    @pytest.mark.asyncio
    async def test_missing_loop_condition_raises(self):
        provider = FakeProvider()
        executor = LoopStepExecutor(provider)

        step = {
            "id": "loop_step",
            "capability_name": "do.thing",
            "arguments": {},
            "metadata": {"type": "loop"},  # no loop_condition key
        }
        with pytest.raises(LoopExecutionError):
            await executor.execute(step, context={})
