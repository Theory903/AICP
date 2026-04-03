"""AICP LoopStepExecutor.

Executes a workflow loop step either as a for-each iteration over
``items_variable`` or as a while-style loop controlled by ``exit_condition``.

Design
------
* Pure async; no I/O beyond calling the capability provider.
* Three modes (determined by ``loop_condition`` fields):
  1. **for-each** (``items_variable`` set): iterate over a list stored in
     the workflow context. Each item is injected as ``item`` in arguments.
  2. **while** (``exit_condition`` set, no ``items_variable``): repeat
     until the exit condition evaluates to True OR ``max_iterations`` is hit.
  3. Both fields set: for-each takes precedence; ``max_iterations`` caps it.
* ``max_iterations`` defaults to ``default_max_iterations`` (100).
* Results are returned as :class:`LoopStepResult`.
* The executor does NOT modify WorkflowState directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "LoopExecutionError",
    "LoopStepExecutor",
    "LoopStepResult",
]

_DEFAULT_MAX_ITERATIONS = 100


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LoopStepResult:
    """Result of a loop step execution."""

    success: bool
    iterations: int
    results: list[Any] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class LoopExecutionError(Exception):
    """Raised for invalid loop configuration (not for capability failures)."""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class LoopStepExecutor:
    """Execute a loop step against a capability provider.

    Parameters
    ----------
    capability_provider:
        Object with ``execute(capability_name, arguments, **kwargs)`` async method.
    default_max_iterations:
        Hard cap on loop iterations when no explicit ``max_iterations`` is given.
    """

    def __init__(
        self,
        capability_provider: Any,
        default_max_iterations: int = _DEFAULT_MAX_ITERATIONS,
    ) -> None:
        self._provider = capability_provider
        self._default_max_iterations = default_max_iterations

    @property
    def default_max_iterations(self) -> int:
        return self._default_max_iterations

    async def execute(
        self,
        step: dict[str, Any],
        *,
        context: dict[str, Any],
    ) -> LoopStepResult:
        """Execute the loop step.

        Parameters
        ----------
        step:
            Step dict with ``id``, ``capability_name``, ``arguments``, and
            ``metadata`` (containing ``loop_condition``).
        context:
            Workflow execution context (used to resolve ``items_variable``).

        Returns
        -------
        :class:`LoopStepResult`

        Raises
        ------
        :class:`LoopExecutionError`
            If the loop configuration is invalid.
        """
        loop_condition: dict[str, Any] | None = (step.get("metadata") or {}).get(
            "loop_condition"
        )

        if not loop_condition:
            raise LoopExecutionError(
                f"Loop step '{step.get('id')}' is missing 'loop_condition' in metadata."
            )

        items_variable: str | None = loop_condition.get("items_variable")
        exit_condition: str | None = loop_condition.get("exit_condition")
        max_iterations: int = int(
            loop_condition.get("max_iterations") or self._default_max_iterations
        )

        if not items_variable and not exit_condition:
            raise LoopExecutionError(
                f"Loop step '{step.get('id')}': loop_condition must specify "
                "'items_variable' or 'exit_condition' (or both)."
            )

        capability_name: str = str(
            step.get("capability_name")
            or (step.get("metadata") or {}).get("capability_name")
            or ""
        )
        base_arguments: dict[str, Any] = dict(step.get("arguments") or {})
        step_id = str(step.get("id", "loop"))

        call_context = {
            "loop_step_id": step_id,
            **{k: v for k, v in context.items() if not isinstance(v, (list, dict))},
        }

        if items_variable:
            return await self._execute_foreach(
                items_variable=items_variable,
                capability_name=capability_name,
                base_arguments=base_arguments,
                context=context,
                call_context=call_context,
                max_iterations=max_iterations,
            )

        # while-style
        return await self._execute_while(
            exit_condition=exit_condition,  # type: ignore[arg-type]
            capability_name=capability_name,
            base_arguments=base_arguments,
            call_context=call_context,
            max_iterations=max_iterations,
        )

    # ------------------------------------------------------------------
    # Private strategies
    # ------------------------------------------------------------------

    async def _execute_foreach(
        self,
        *,
        items_variable: str,
        capability_name: str,
        base_arguments: dict[str, Any],
        context: dict[str, Any],
        call_context: dict[str, Any],
        max_iterations: int,
    ) -> LoopStepResult:
        """Iterate over context[items_variable]."""
        if items_variable not in context:
            raise LoopExecutionError(
                f"items_variable '{items_variable}' not found in workflow context."
            )

        items = context[items_variable]
        if not isinstance(items, (list, tuple)):
            raise LoopExecutionError(
                f"items_variable '{items_variable}' must be a list, "
                f"got {type(items).__name__!r}."
            )

        results: list[Any] = []
        count = 0

        for item in items:
            if count >= max_iterations:
                break

            args = {**base_arguments, "item": item}
            try:
                result = await self._provider.execute(
                    capability_name, args, context=call_context
                )
                results.append(result)
            except Exception as exc:
                return LoopStepResult(
                    success=False,
                    iterations=count + 1,
                    results=results,
                    error=str(exc),
                )
            count += 1

        return LoopStepResult(success=True, iterations=count, results=results)

    async def _execute_while(
        self,
        *,
        exit_condition: str,
        capability_name: str,
        base_arguments: dict[str, Any],
        call_context: dict[str, Any],
        max_iterations: int,
    ) -> LoopStepResult:
        """Run while exit_condition evaluates to False (or until max_iterations)."""
        results: list[Any] = []
        count = 0

        while count < max_iterations:
            # Evaluate exit condition using safe eval (only 'True'/'False' literals
            # are evaluated by default; anything else is treated as always-run)
            should_exit = self._eval_exit_condition(exit_condition)

            if should_exit and count > 0:
                # Exit after at least one iteration (post-check semantics)
                break

            try:
                result = await self._provider.execute(
                    capability_name, dict(base_arguments), context=call_context
                )
                results.append(result)
            except Exception as exc:
                return LoopStepResult(
                    success=False,
                    iterations=count + 1,
                    results=results,
                    error=str(exc),
                )
            count += 1

            # Check exit condition after execution (do-while semantics)
            if self._eval_exit_condition(exit_condition):
                break

        return LoopStepResult(success=True, iterations=count, results=results)

    @staticmethod
    def _eval_exit_condition(condition: str) -> bool:
        """Evaluate a simple exit condition string.

        Only supports literal 'True' and 'False' values for now.
        Future: full expression evaluator with context bindings.
        """
        stripped = (condition or "").strip()
        if stripped == "True":
            return True
        if stripped == "False":
            return False
        # Unknown/complex conditions: treat as not-exit (keep running)
        return False
