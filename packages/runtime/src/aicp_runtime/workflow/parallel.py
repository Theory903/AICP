"""AICP Parallel Step Executor.

Executes multiple workflow sub-steps concurrently using ``asyncio.gather``.

Design
------
* Pure async; no I/O beyond calling the capability provider.
* Supports two failure policies:
  - ``fail_fast`` (default): cancel sibling tasks as soon as one fails.
    In practice with asyncio.gather we collect the first exception and mark
    remaining un-started steps as failed with a "cancelled" error message.
  - ``wait_all``: run all steps to completion, collecting every error.
* Results are returned as a :class:`ParallelStepResult` containing a
  ``Dict[step_id, SubStepOutcome]``.
* The executor does NOT modify WorkflowState directly; that is the
  responsibility of the calling runtime (e.g. an extended workflow engine).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ParallelExecutionError",
    "ParallelStepExecutor",
    "ParallelStepResult",
    "SubStepOutcome",
]

_VALID_FAILURE_POLICIES = frozenset({"fail_fast", "wait_all"})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SubStepOutcome:
    """Result of a single sub-step within a parallel block."""

    step_id: str
    success: bool
    result: Any = None
    error: str | None = None


@dataclass
class ParallelStepResult:
    """Aggregated result of a parallel step execution."""

    success: bool
    outcomes: dict[str, SubStepOutcome] = field(default_factory=dict)

    @property
    def failed_count(self) -> int:
        return sum(1 for o in self.outcomes.values() if not o.success)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for o in self.outcomes.values() if o.success)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class ParallelExecutionError(Exception):
    """Raised for invalid inputs to the executor (not for step failures)."""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class ParallelStepExecutor:
    """Run multiple capability-based sub-steps in parallel.

    Parameters
    ----------
    capability_provider:
        Any object with an ``execute(capability_name, arguments, **kwargs)``
        async method — compatible with the AICP ``CapabilityProvider``
        interface.
    """

    def __init__(self, capability_provider: Any) -> None:
        self._provider = capability_provider

    async def execute(
        self,
        sub_steps: list[dict[str, Any]],
        *,
        context: dict[str, Any],
        failure_policy: str = "fail_fast",
    ) -> ParallelStepResult:
        """Execute *sub_steps* concurrently.

        Parameters
        ----------
        sub_steps:
            List of step dicts, each containing ``id``, ``capability_name``,
            and optionally ``arguments``.
        context:
            Shared workflow context forwarded to each capability call.
        failure_policy:
            ``"fail_fast"`` (default) or ``"wait_all"``.

        Returns
        -------
        :class:`ParallelStepResult`
            Aggregated outcomes for all sub-steps.

        Raises
        ------
        :class:`ParallelExecutionError`
            If *sub_steps* is empty or *failure_policy* is invalid.
        """
        if not sub_steps:
            raise ParallelExecutionError(
                "parallel executor requires a non-empty list of sub-steps (empty list given)"
            )
        if failure_policy not in _VALID_FAILURE_POLICIES:
            raise ParallelExecutionError(
                f"invalid failure_policy '{failure_policy}'. "
                f"Valid values: {sorted(_VALID_FAILURE_POLICIES)}"
            )

        if failure_policy == "wait_all":
            return await self._execute_wait_all(sub_steps, context)
        return await self._execute_fail_fast(sub_steps, context)

    # ------------------------------------------------------------------
    # Internal strategies
    # ------------------------------------------------------------------

    async def _execute_fail_fast(
        self,
        sub_steps: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> ParallelStepResult:
        """Run all steps; return immediately with failure on the first error."""
        tasks = {
            step["id"]: asyncio.ensure_future(self._run_single(step, context))
            for step in sub_steps
        }

        outcomes: dict[str, SubStepOutcome] = {}
        try:
            # gather with return_exceptions=False → raises on first exception
            results = await asyncio.gather(*tasks.values(), return_exceptions=False)
            for step_id, result in zip(tasks.keys(), results):
                if isinstance(result, SubStepOutcome):
                    outcomes[step_id] = result
                else:
                    # Capability returned a plain value
                    outcomes[step_id] = SubStepOutcome(
                        step_id=step_id, success=True, result=result
                    )
        except Exception as exc:
            # Cancel remaining tasks
            for task in tasks.values():
                task.cancel()
            # Collect what we have so far
            for step_id, task in tasks.items():
                if step_id in outcomes:
                    continue
                if task.done() and not task.cancelled():
                    try:
                        res = task.result()
                        outcomes[step_id] = SubStepOutcome(
                            step_id=step_id, success=True, result=res
                        )
                    except Exception as step_exc:
                        outcomes[step_id] = SubStepOutcome(
                            step_id=step_id,
                            success=False,
                            error=str(step_exc),
                        )
                else:
                    outcomes[step_id] = SubStepOutcome(
                        step_id=step_id,
                        success=False,
                        error=str(exc),
                    )

            return ParallelStepResult(success=False, outcomes=outcomes)

        all_ok = all(o.success for o in outcomes.values())
        return ParallelStepResult(success=all_ok, outcomes=outcomes)

    async def _execute_wait_all(
        self,
        sub_steps: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> ParallelStepResult:
        """Run all steps; collect all outcomes regardless of failures."""
        tasks = [
            asyncio.ensure_future(self._run_single(step, context)) for step in sub_steps
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        outcomes: dict[str, SubStepOutcome] = {}
        for step, raw in zip(sub_steps, raw_results):
            step_id = step["id"]
            if isinstance(raw, SubStepOutcome):
                outcomes[step_id] = raw
            elif isinstance(raw, BaseException):
                outcomes[step_id] = SubStepOutcome(
                    step_id=step_id,
                    success=False,
                    error=str(raw),
                )
            else:
                outcomes[step_id] = SubStepOutcome(
                    step_id=step_id, success=True, result=raw
                )

        all_ok = all(o.success for o in outcomes.values())
        return ParallelStepResult(success=all_ok, outcomes=outcomes)

    async def _run_single(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
    ) -> SubStepOutcome:
        """Execute a single sub-step and return a :class:`SubStepOutcome`."""
        step_id = str(step.get("id", ""))
        capability_name = str(step.get("capability_name", ""))
        arguments: dict[str, Any] = dict(step.get("arguments") or {})

        try:
            result = await self._provider.execute(
                capability_name,
                arguments,
                context=context,
            )
            return SubStepOutcome(step_id=step_id, success=True, result=result)
        except Exception as exc:
            return SubStepOutcome(
                step_id=step_id,
                success=False,
                error=str(exc),
            )
