"""AICP SubflowExecutor.

Executes a child workflow as a step within a parent workflow.

Design
------
* The executor accepts a ``WorkflowRuntime`` instance (the parent runtime itself)
  so it can call ``create_workflow`` and ``execute_step`` using the same runtime.
* Child workflow steps are driven to completion sequentially.
* If any child step fails the executor returns a failed :class:`SubflowResult`.
* The executor does NOT modify the parent WorkflowState directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

__all__ = [
    "SubflowError",
    "SubflowExecutor",
    "SubflowResult",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SubflowResult:
    """Result of a subflow step execution."""

    success: bool
    workflow_id: str
    error: str | None = None


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class SubflowError(Exception):
    """Raised for invalid subflow configuration (not for step failures)."""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class SubflowExecutor:
    """Execute a subflow step by running a child workflow to completion.

    Parameters
    ----------
    runtime:
        A :class:`WorkflowRuntime`-compatible object with ``create_workflow``
        and ``execute_step`` async methods.
    """

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    async def execute(
        self,
        step: dict[str, Any],
        *,
        context: dict[str, Any],
    ) -> SubflowResult:
        """Execute the subflow step.

        Parameters
        ----------
        step:
            Step dict with ``id`` and ``metadata`` containing ``subflow_name``
            and ``subflow_steps``.
        context:
            Parent workflow execution context (carried into child workflow
            creation for traceability).

        Returns
        -------
        :class:`SubflowResult`

        Raises
        ------
        :class:`SubflowError`
            If the subflow configuration is invalid (missing name or steps).
        """
        metadata: dict[str, Any] = step.get("metadata") or {}

        subflow_name: str | None = metadata.get("subflow_name")
        if not subflow_name:
            raise SubflowError(
                f"Subflow step '{step.get('id')}' is missing 'subflow_name' in metadata."
            )

        subflow_steps: list[dict[str, Any]] | None = metadata.get("subflow_steps")
        if subflow_steps is None:
            raise SubflowError(
                f"Subflow step '{step.get('id')}' is missing 'subflow_steps' in metadata."
            )

        # Create the child workflow
        child_wf = await self._runtime.create_workflow(
            name=subflow_name,
            description=f"Subflow of step '{step.get('id')}'",
            steps=subflow_steps,
        )

        # Drive child workflow to completion.
        # Use the returned child_wf directly first; fall back to polling get_workflow.
        current_state = child_wf
        while not (current_state is None or current_state.is_complete):
            step_result = await self._runtime.execute_step(child_wf.id)
            if not step_result.success:
                return SubflowResult(
                    success=False,
                    workflow_id=child_wf.id,
                    error=step_result.error or "Subflow step failed",
                )

            # Refresh state after each step
            current_state = await self._runtime.get_workflow(child_wf.id)

        # Verify final child workflow state
        final_state = await self._runtime.get_workflow(child_wf.id)
        if final_state is not None and hasattr(final_state, "status"):
            from aicp.interfaces.workflow_runtime import WorkflowStatus  # type: ignore[import]

            if final_state.status == WorkflowStatus.FAILED:
                return SubflowResult(
                    success=False,
                    workflow_id=child_wf.id,
                    error="Child workflow completed with FAILED status",
                )

        return SubflowResult(success=True, workflow_id=child_wf.id)
