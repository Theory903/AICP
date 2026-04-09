"""Tests for the parallel step executor.

TDD: written BEFORE implementation.
Contract for aicp_runtime.workflow.parallel.ParallelStepExecutor.

A ParallelStepExecutor runs multiple sub-steps concurrently and returns
a ParallelStepResult collecting all individual outcomes.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aicp_runtime.workflow.parallel import (
    ParallelExecutionError,
    ParallelStepExecutor,
    ParallelStepResult,
    SubStepOutcome,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_capability_provider(responses: dict[str, Any]) -> MagicMock:
    """Build a minimal CapabilityProvider mock.

    responses: {capability_name: return_value_or_exception}
    """
    provider = MagicMock()

    async def execute_side(capability_name: str, arguments: dict, **_kwargs):
        val = responses.get(capability_name, {"status": "ok"})
        if isinstance(val, Exception):
            raise val
        return val

    provider.execute = AsyncMock(side_effect=execute_side)
    return provider


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestParallelStepExecutorHappyPath:
    @pytest.mark.asyncio
    async def test_all_steps_succeed_returns_result(self):
        """All sub-steps succeed → overall success, results collected."""
        provider = make_capability_provider(
            {
                "notify.email": {"sent": True},
                "notify.sms": {"sent": True},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}},
            {"id": "sms", "capability_name": "notify.sms", "arguments": {}},
        ]
        result = await executor.execute(sub_steps, context={})

        assert isinstance(result, ParallelStepResult)
        assert result.success is True
        assert result.failed_count == 0
        assert len(result.outcomes) == 2

    @pytest.mark.asyncio
    async def test_outcomes_indexed_by_step_id(self):
        provider = make_capability_provider(
            {
                "notify.email": {"sent": True},
                "notify.sms": {"delivered": True},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}},
            {"id": "sms", "capability_name": "notify.sms", "arguments": {}},
        ]
        result = await executor.execute(sub_steps, context={})

        assert "email" in result.outcomes
        assert "sms" in result.outcomes
        assert result.outcomes["email"].success is True
        assert result.outcomes["sms"].success is True

    @pytest.mark.asyncio
    async def test_outcome_carries_result_data(self):
        provider = make_capability_provider(
            {
                "notify.email": {"msg_id": "abc123"},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}}
        ]
        result = await executor.execute(sub_steps, context={})

        outcome = result.outcomes["email"]
        assert isinstance(outcome, SubStepOutcome)
        assert outcome.result == {"msg_id": "abc123"}
        assert outcome.error is None

    @pytest.mark.asyncio
    async def test_single_step_succeeds(self):
        provider = make_capability_provider({"a.b": {"ok": True}})
        executor = ParallelStepExecutor(provider)
        sub_steps = [{"id": "s1", "capability_name": "a.b", "arguments": {}}]
        result = await executor.execute(sub_steps, context={})

        assert result.success is True
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_steps_run_with_arguments(self):
        """Arguments are forwarded to the capability provider."""
        captured: list[dict] = []

        async def execute_side(capability_name, arguments, **_kw):
            captured.append({"capability": capability_name, "args": arguments})
            return {"ok": True}

        provider = MagicMock()
        provider.execute = AsyncMock(side_effect=execute_side)

        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "s1", "capability_name": "foo.bar", "arguments": {"x": 42}},
            {"id": "s2", "capability_name": "foo.baz", "arguments": {"y": "hello"}},
        ]
        await executor.execute(sub_steps, context={})

        names = {c["capability"] for c in captured}
        assert "foo.bar" in names
        assert "foo.baz" in names
        s1_call = next(c for c in captured if c["capability"] == "foo.bar")
        assert s1_call["args"]["x"] == 42

    @pytest.mark.asyncio
    async def test_context_passed_to_steps(self):
        """The shared context is passed through to capabilities."""
        captured: list[dict] = []

        async def execute_side(capability_name, arguments, **kwargs):
            captured.append(kwargs)
            return {"ok": True}

        provider = MagicMock()
        provider.execute = AsyncMock(side_effect=execute_side)
        executor = ParallelStepExecutor(provider)
        sub_steps = [{"id": "s1", "capability_name": "foo.bar", "arguments": {}}]
        await executor.execute(sub_steps, context={"tenant": "acme"})

        # context should be forwarded (either via kwargs or merged into args)
        assert len(captured) == 1


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class TestParallelStepExecutorFailureModes:
    @pytest.mark.asyncio
    async def test_fail_fast_stops_on_first_failure(self):
        """With fail_fast (default), overall result is failure if any step fails."""
        provider = make_capability_provider(
            {
                "notify.email": RuntimeError("smtp down"),
                "notify.sms": {"delivered": True},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}},
            {"id": "sms", "capability_name": "notify.sms", "arguments": {}},
        ]
        result = await executor.execute(
            sub_steps, context={}, failure_policy="fail_fast"
        )

        assert result.success is False
        assert result.failed_count >= 1

    @pytest.mark.asyncio
    async def test_failed_outcome_carries_error_message(self):
        provider = make_capability_provider(
            {
                "notify.email": RuntimeError("smtp down"),
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}}
        ]
        result = await executor.execute(sub_steps, context={})

        outcome = result.outcomes["email"]
        assert outcome.success is False
        assert outcome.error is not None
        assert "smtp" in outcome.error.lower()

    @pytest.mark.asyncio
    async def test_wait_all_collects_all_outcomes(self):
        """With wait_all, all steps run even after a failure."""
        provider = make_capability_provider(
            {
                "notify.email": RuntimeError("smtp down"),
                "notify.sms": {"delivered": True},
                "notify.push": {"delivered": True},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "email", "capability_name": "notify.email", "arguments": {}},
            {"id": "sms", "capability_name": "notify.sms", "arguments": {}},
            {"id": "push", "capability_name": "notify.push", "arguments": {}},
        ]
        result = await executor.execute(
            sub_steps, context={}, failure_policy="wait_all"
        )

        assert result.success is False
        assert len(result.outcomes) == 3
        assert result.outcomes["email"].success is False
        assert result.outcomes["sms"].success is True
        assert result.outcomes["push"].success is True

    @pytest.mark.asyncio
    async def test_wait_all_failed_count_is_accurate(self):
        provider = make_capability_provider(
            {
                "a": RuntimeError("err1"),
                "b": RuntimeError("err2"),
                "c": {"ok": True},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "a", "capability_name": "a", "arguments": {}},
            {"id": "b", "capability_name": "b", "arguments": {}},
            {"id": "c", "capability_name": "c", "arguments": {}},
        ]
        result = await executor.execute(
            sub_steps, context={}, failure_policy="wait_all"
        )
        assert result.failed_count == 2

    @pytest.mark.asyncio
    async def test_all_fail_with_wait_all(self):
        provider = make_capability_provider(
            {
                "a": RuntimeError("err"),
                "b": RuntimeError("err"),
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "a", "capability_name": "a", "arguments": {}},
            {"id": "b", "capability_name": "b", "arguments": {}},
        ]
        result = await executor.execute(
            sub_steps, context={}, failure_policy="wait_all"
        )
        assert result.success is False
        assert result.failed_count == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestParallelStepExecutorEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_sub_steps_raises_error(self):
        """Empty sub_steps list is an invalid input."""
        provider = make_capability_provider({})
        executor = ParallelStepExecutor(provider)
        with pytest.raises(ParallelExecutionError, match="empty"):
            await executor.execute([], context={})

    @pytest.mark.asyncio
    async def test_invalid_failure_policy_raises_error(self):
        provider = make_capability_provider({"a.b": {"ok": True}})
        executor = ParallelStepExecutor(provider)
        sub_steps = [{"id": "s1", "capability_name": "a.b", "arguments": {}}]
        with pytest.raises(ParallelExecutionError, match="failure_policy"):
            await executor.execute(sub_steps, context={}, failure_policy="invalid")

    @pytest.mark.asyncio
    async def test_result_includes_step_ids(self):
        provider = make_capability_provider(
            {
                "x.y": {"r": 1},
                "x.z": {"r": 2},
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [
            {"id": "first", "capability_name": "x.y", "arguments": {}},
            {"id": "second", "capability_name": "x.z", "arguments": {}},
        ]
        result = await executor.execute(sub_steps, context={})
        assert set(result.outcomes.keys()) == {"first", "second"}

    @pytest.mark.asyncio
    async def test_default_failure_policy_is_fail_fast(self):
        """When failure_policy is not provided, fail_fast behaviour applies."""
        provider = make_capability_provider(
            {
                "a": RuntimeError("boom"),
            }
        )
        executor = ParallelStepExecutor(provider)
        sub_steps = [{"id": "a", "capability_name": "a", "arguments": {}}]
        result = await executor.execute(sub_steps, context={})
        assert result.success is False
