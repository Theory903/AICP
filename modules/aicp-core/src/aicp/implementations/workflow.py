"""Default workflow runtime implementation.

A workflow runtime that manages multi-step execution with state,
confirmation handling, approval handling, and agent guidance.

Phase 2 extensions
------------------
* ``type: parallel`` steps — dispatched to :class:`ParallelStepExecutor`.
  Sub-steps are listed in ``step.metadata["parallel_steps"]``.
  Optional ``step.metadata["failure_policy"]`` controls fail_fast / wait_all.
* ``type: wait_event`` steps — dispatched to a per-workflow :class:`EventWaiter`.
  ``step.metadata["event_name"]`` and ``step.metadata["timeout_ms"]`` configure
  the wait; ``step.metadata["event_filter"]`` optionally narrows matching.
  Use :meth:`publish_event` from outside to deliver events.
* ``type: loop`` steps — dispatched to :class:`LoopStepExecutor`.
  ``step.metadata["loop_condition"]`` configures for-each or while semantics.
* ``type: subflow`` steps — dispatched to :class:`SubflowExecutor`.
  ``step.metadata["subflow_name"]`` and ``step.metadata["subflow_steps"]`` define
  the child workflow.
* Normal capability steps have no ``type`` key in metadata (or type == "capability").
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.policy_engine import PolicyEffect, PolicyEngine
from aicp.interfaces.workflow_runtime import (
    Step,
    StepResult,
    StepStatus,
    WorkflowError,
    WorkflowRuntime,
    WorkflowState,
    WorkflowStatus,
)

if TYPE_CHECKING:
    from aicp.approval_service import ApprovalService

# Phase 2 primitives — imported lazily inside methods to keep core package clean.
# The runtime package sits above core in the dependency tree, so we do a
# deferred import at call-site rather than at module level.
_PARALLEL_EXECUTOR_CLASS = None
_EVENT_WAITER_CLASS = None
_LOOP_EXECUTOR_CLASS = None
_SUBFLOW_EXECUTOR_CLASS = None


def _get_parallel_executor_class() -> type:
    global _PARALLEL_EXECUTOR_CLASS  # noqa: PLW0603
    if _PARALLEL_EXECUTOR_CLASS is None:
        from aicp_runtime.workflow.parallel import ParallelStepExecutor  # type: ignore[import]

        _PARALLEL_EXECUTOR_CLASS = ParallelStepExecutor
    return _PARALLEL_EXECUTOR_CLASS


def _get_event_waiter_class() -> type:
    global _EVENT_WAITER_CLASS  # noqa: PLW0603
    if _EVENT_WAITER_CLASS is None:
        from aicp_runtime.workflow.events import EventWaiter  # type: ignore[import]

        _EVENT_WAITER_CLASS = EventWaiter
    return _EVENT_WAITER_CLASS


def _get_loop_executor_class() -> type:
    global _LOOP_EXECUTOR_CLASS  # noqa: PLW0603
    if _LOOP_EXECUTOR_CLASS is None:
        from aicp_runtime.workflow.loop import LoopStepExecutor  # type: ignore[import]

        _LOOP_EXECUTOR_CLASS = LoopStepExecutor
    return _LOOP_EXECUTOR_CLASS


def _get_subflow_executor_class() -> type:
    global _SUBFLOW_EXECUTOR_CLASS  # noqa: PLW0603
    if _SUBFLOW_EXECUTOR_CLASS is None:
        from aicp_runtime.workflow.subflow import SubflowExecutor  # type: ignore[import]

        _SUBFLOW_EXECUTOR_CLASS = SubflowExecutor
    return _SUBFLOW_EXECUTOR_CLASS


# Step types that do NOT require a capability_name
_NON_CAPABILITY_STEP_TYPES = frozenset({"parallel", "wait_event", "branch", "loop", "subflow"})


class DefaultWorkflowRuntime(WorkflowRuntime):
    """Default workflow runtime with in-memory step orchestration."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self._provider = capability_provider
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._workflows: dict[str, WorkflowState] = {}
        # Per-workflow EventWaiter instances (created on demand)
        self._event_waiters: dict[str, Any] = {}

    @property
    def runtime_type(self) -> str:
        return "default"

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: list[dict[str, Any]] | None = None,
    ) -> WorkflowState:
        """Create and store a new workflow."""
        workflow_id = str(uuid.uuid4())
        step_objects: list[Step] = []

        for index, step_def in enumerate(steps or []):
            step_type = (step_def.get("metadata") or {}).get("type", "capability")
            requires_cap_name = step_type not in _NON_CAPABILITY_STEP_TYPES

            if requires_cap_name and "capability_name" not in step_def:
                raise WorkflowError(
                    "Each workflow step must include 'capability_name'",
                    workflow_id=workflow_id,
                    details={"step_index": index, "step": step_def},
                )

            step_objects.append(
                Step(
                    id=str(step_def.get("id", f"step_{index}")),
                    capability_name=step_def.get("capability_name", ""),
                    arguments=dict(step_def.get("arguments", {})),
                    metadata=dict(step_def.get("metadata", {})),
                )
            )

        workflow = WorkflowState(
            id=workflow_id,
            name=name,
            description=description,
            steps=step_objects,
        )
        workflow.sync_status()
        self._workflows[workflow_id] = workflow
        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute the current workflow step."""
        workflow = self._require_workflow(workflow_id)

        if workflow.status == WorkflowStatus.CANCELLED:
            return StepResult.fail(
                "Workflow is cancelled",
                workflow_status=workflow.status,
            )

        if workflow.is_complete:
            workflow.sync_status()
            return StepResult.fail(
                "Workflow already complete",
                workflow_status=workflow.status,
            )

        step = workflow.current_step
        if step is None:
            workflow.sync_status()
            return StepResult.fail(
                "No current step available",
                workflow_status=workflow.status,
            )

        if step.status == StepStatus.SKIPPED:
            workflow.advance()
            workflow.sync_status()
            return StepResult.ok(
                next=self._generate_next(workflow, workflow.current_step),
                workflow_status=workflow.status,
            )

        merged_args = {**step.arguments}
        if arguments:
            merged_args.update(arguments)

        workflow.context["last_args"] = merged_args
        workflow.context["last_step_id"] = step.id

        step.mark_running()
        workflow.status = WorkflowStatus.RUNNING
        workflow.touch()

        try:
            # ------------------------------------------------------------------
            # Phase 2: dispatch on step type
            # ------------------------------------------------------------------
            step_type = step.metadata.get("type", "capability")

            if step_type == "parallel":
                return await self._execute_parallel_step(workflow, step)

            if step_type == "wait_event":
                return await self._execute_wait_event_step(workflow, step)

            if step_type == "loop":
                return await self._execute_loop_step(workflow, step)

            if step_type == "subflow":
                return await self._execute_subflow_step(workflow, step)

            # Default: capability step
            policy_result = await self._evaluate_policy(workflow, step, merged_args)
            if policy_result is not None:
                return policy_result

            result = await self._provider.execute(
                step.capability_name,
                merged_args,
                {
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.name,
                    "step_id": step.id,
                    "kind": workflow.context.get("kind"),
                    "tenant_id": workflow.context.get("tenant_id"),
                },
            )

            step.mark_completed(result)
            workflow.advance()
            workflow.sync_status()

            return StepResult.ok(
                result=result,
                next=self._generate_next(workflow, workflow.current_step),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        except Exception as exc:
            step.mark_failed(str(exc))
            workflow.sync_status()

            return StepResult.fail(
                str(exc),
                next={
                    "action": "retry_step",
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "hint": f"Retry step '{step.capability_name}' after inspecting the failure.",
                },
                step_id=step.id,
                workflow_status=workflow.status,
            )

    async def confirm_and_continue(
        self,
        workflow_id: str,
        confirmed: bool,
        modified_arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Continue after a confirmation checkpoint."""
        workflow = self._require_workflow(workflow_id)
        step = workflow.current_step

        if step is None or step.status != StepStatus.AWAITING_CONFIRMATION:
            return StepResult.fail(
                "No confirmation needed",
                workflow_status=workflow.status,
            )

        if not confirmed:
            step.mark_skipped()
            workflow.advance()
            workflow.sync_status()
            return StepResult.ok(
                next=self._generate_next(workflow, workflow.current_step),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        confirmed_args = modified_arguments or workflow.context.get("last_args", {}) or {}
        workflow.context["confirmation_granted"] = True
        try:
            step.status = StepStatus.PENDING
            step.started_at = None
            step.completed_at = None
            workflow.sync_status()
            return await self.execute_step(workflow_id, confirmed_args)
        finally:
            workflow.context.pop("confirmation_granted", None)

    async def skip_step(self, workflow_id: str) -> StepResult:
        """Skip the current step."""
        workflow = self._require_workflow(workflow_id)
        step = workflow.current_step

        if step is None:
            return StepResult.fail(
                "No current step to skip",
                workflow_status=workflow.status,
            )

        if step.is_terminal:
            return StepResult.fail(
                f"Cannot skip step in terminal status '{step.status.value}'",
                step_id=step.id,
                workflow_status=workflow.status,
            )

        step.mark_skipped()
        workflow.advance()
        workflow.sync_status()

        return StepResult.ok(
            next=self._generate_next(workflow, workflow.current_step),
            step_id=step.id,
            workflow_status=workflow.status,
        )

    async def retry_step(self, workflow_id: str) -> StepResult:
        """Retry the current failed step."""
        workflow = self._require_workflow(workflow_id)
        step = workflow.current_step

        if step is None:
            return StepResult.fail(
                "No current step to retry",
                workflow_status=workflow.status,
            )

        if step.status != StepStatus.FAILED:
            return StepResult.fail(
                "No failed step to retry",
                step_id=step.id,
                workflow_status=workflow.status,
            )

        step.status = StepStatus.PENDING
        step.error = None
        step.result = None
        step.started_at = None
        step.completed_at = None
        workflow.sync_status()

        retry_args = workflow.context.get("last_args", {}) or step.arguments
        return await self.execute_step(workflow_id, retry_args)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return False

        workflow.status = WorkflowStatus.CANCELLED
        workflow.touch()
        return True

    async def pause_for_approval(
        self,
        workflow_id: str,
        approval_request_id: str,
    ) -> WorkflowState:
        """Pause a workflow for approval."""
        workflow = self._require_workflow(workflow_id)
        step = workflow.current_step

        workflow.status = WorkflowStatus.WAITING_APPROVAL
        workflow.metadata["approval_request_id"] = approval_request_id
        if step is not None:
            step.status = StepStatus.AWAITING_APPROVAL

        workflow.touch()
        return workflow

    async def resume_after_approval(
        self,
        workflow_id: str,
        approved: bool,
    ) -> StepResult:
        """Resume a workflow after approval decision."""
        workflow = self._require_workflow(workflow_id)

        if workflow.status != WorkflowStatus.WAITING_APPROVAL:
            raise WorkflowError(
                f"Workflow not paused for approval: {workflow_id}",
                workflow_id=workflow_id,
            )

        step = workflow.current_step
        if step is None:
            raise WorkflowError(
                f"Workflow has no current step: {workflow_id}",
                workflow_id=workflow_id,
            )

        if not approved:
            step.mark_failed("Approval denied")
            workflow.status = WorkflowStatus.CANCELLED
            workflow.touch()
            return StepResult.fail(
                "Approval denied",
                step_id=step.id,
                workflow_status=workflow.status,
            )

        workflow.metadata.pop("approval_request_id", None)
        workflow.context["approval_granted"] = True
        step.status = StepStatus.PENDING
        step.started_at = None
        step.completed_at = None
        workflow.sync_status()

        try:
            return await self.execute_step(workflow_id)
        finally:
            workflow.context.pop("approval_granted", None)

    async def list_workflows(self) -> list[WorkflowState]:
        """List all workflows."""
        return list(self._workflows.values())

    # ------------------------------------------------------------------
    # Phase 2: parallel and wait_event step handlers
    # ------------------------------------------------------------------

    async def _execute_parallel_step(
        self,
        workflow: WorkflowState,
        step: Step,
    ) -> StepResult:
        """Execute a parallel step using ParallelStepExecutor."""
        sub_steps: list[dict[str, Any]] = step.metadata.get("parallel_steps", [])
        # Support both DSL key (parallel_failure_policy) and direct key (failure_policy)
        failure_policy: str = (
            step.metadata.get("failure_policy") or step.metadata.get("parallel_failure_policy") or "fail_fast"
        )

        try:
            ParallelStepExecutor = _get_parallel_executor_class()  # noqa: N806
            executor = ParallelStepExecutor(self._provider)
            par_result = await executor.execute(
                sub_steps,
                context={
                    "workflow_id": workflow.id,
                    "workflow_name": workflow.name,
                    "step_id": step.id,
                },
                failure_policy=failure_policy,
            )
        except Exception as exc:
            step.mark_failed(str(exc))
            workflow.sync_status()
            return StepResult.fail(
                str(exc),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        if par_result.success:
            step.mark_completed(par_result)
            workflow.advance()
            workflow.sync_status()
            return StepResult.ok(
                result=par_result,
                next=self._generate_next(workflow, workflow.current_step),
                step_id=step.id,
                workflow_status=workflow.status,
            )
        else:
            error_msg = f"Parallel step failed: {par_result.failed_count} sub-step(s) failed"
            step.mark_failed(error_msg)
            workflow.sync_status()
            return StepResult.fail(
                error_msg,
                step_id=step.id,
                workflow_status=workflow.status,
            )

    async def _execute_wait_event_step(
        self,
        workflow: WorkflowState,
        step: Step,
    ) -> StepResult:
        """Execute a wait_event step using EventWaiter."""
        # Support both DSL format (wait_for_event) and direct format (event_name)
        event_name: str = step.metadata.get("event_name") or step.metadata.get("wait_for_event", "")
        timeout_ms: int = int(step.metadata.get("timeout_ms", 5000))
        event_filter: dict[str, Any] | None = step.metadata.get("event_filter")

        # Ensure we have an EventWaiter for this workflow
        waiter = self._get_or_create_event_waiter(workflow.id)

        # Set workflow to WAITING_EVENT while we wait
        workflow.status = WorkflowStatus.WAITING_EVENT
        workflow.touch()

        try:
            payload = await waiter.wait_for_event(
                event_name,
                timeout_ms=timeout_ms,
                event_filter=event_filter,
            )
        except Exception as exc:
            step.mark_failed(str(exc))
            workflow.sync_status()
            return StepResult.fail(
                str(exc),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        step.mark_completed(payload)
        workflow.advance()
        workflow.sync_status()
        return StepResult.ok(
            result=payload,
            next=self._generate_next(workflow, workflow.current_step),
            step_id=step.id,
            workflow_status=workflow.status,
        )

    def _get_or_create_event_waiter(self, workflow_id: str) -> Any:
        """Return the EventWaiter for this workflow, creating it if needed."""
        if workflow_id not in self._event_waiters:
            EventWaiter = _get_event_waiter_class()  # noqa: N806
            self._event_waiters[workflow_id] = EventWaiter(workflow_id=workflow_id)
        return self._event_waiters[workflow_id]

    async def _execute_loop_step(
        self,
        workflow: WorkflowState,
        step: Step,
    ) -> StepResult:
        """Execute a loop step using LoopStepExecutor."""
        step_dict = {
            "id": step.id,
            "capability_name": step.capability_name,
            "arguments": step.arguments,
            "metadata": step.metadata,
        }

        try:
            LoopStepExecutor = _get_loop_executor_class()  # noqa: N806
            executor = LoopStepExecutor(self._provider)
            loop_result = await executor.execute(step_dict, context=workflow.context)
        except Exception as exc:
            step.mark_failed(str(exc))
            workflow.sync_status()
            return StepResult.fail(
                str(exc),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        if loop_result.success:
            step.mark_completed(loop_result)
            workflow.advance()
            workflow.sync_status()
            return StepResult.ok(
                result=loop_result,
                next=self._generate_next(workflow, workflow.current_step),
                step_id=step.id,
                workflow_status=workflow.status,
            )
        else:
            error_msg = loop_result.error or "Loop step failed"
            step.mark_failed(error_msg)
            workflow.sync_status()
            return StepResult.fail(
                error_msg,
                step_id=step.id,
                workflow_status=workflow.status,
            )

    async def _execute_subflow_step(
        self,
        workflow: WorkflowState,
        step: Step,
    ) -> StepResult:
        """Execute a subflow step using SubflowExecutor."""
        step_dict = {
            "id": step.id,
            "capability_name": step.capability_name,
            "arguments": step.arguments,
            "metadata": step.metadata,
        }

        try:
            SubflowExecutor = _get_subflow_executor_class()  # noqa: N806
            executor = SubflowExecutor(self)
            subflow_result = await executor.execute(step_dict, context=workflow.context)
        except Exception as exc:
            step.mark_failed(str(exc))
            workflow.sync_status()
            return StepResult.fail(
                str(exc),
                step_id=step.id,
                workflow_status=workflow.status,
            )

        if subflow_result.success:
            step.mark_completed(subflow_result)
            workflow.advance()
            workflow.sync_status()
            return StepResult.ok(
                result=subflow_result,
                next=self._generate_next(workflow, workflow.current_step),
                step_id=step.id,
                workflow_status=workflow.status,
            )
        else:
            error_msg = subflow_result.error or "Subflow step failed"
            step.mark_failed(error_msg)
            workflow.sync_status()
            return StepResult.fail(
                error_msg,
                step_id=step.id,
                workflow_status=workflow.status,
            )

    async def publish_event(
        self,
        workflow_id: str,
        name: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to the EventWaiter for the given workflow.

        Safe to call even if no waiter is registered (event is dropped).
        """
        waiter = self._event_waiters.get(workflow_id)
        if waiter is not None:
            await waiter.publish_event(name, payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_workflow(self, workflow_id: str) -> WorkflowState:
        """Get workflow or raise."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise WorkflowError(
                f"Workflow not found: {workflow_id}",
                workflow_id=workflow_id,
            )
        return workflow

    async def _evaluate_policy(
        self,
        workflow: WorkflowState,
        step: Step,
        arguments: dict[str, Any],
    ) -> StepResult | None:
        """Evaluate policy for a step. Return a StepResult when execution must stop."""
        if self._policy_engine is None:
            return None

        if workflow.context.get("confirmation_granted") or workflow.context.get("approval_granted"):
            return None

        decision = await self._policy_engine.evaluate(
            step.capability_name,
            arguments,
            {
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "step_id": step.id,
                "kind": workflow.context.get("kind", "action"),
                "tenant_id": workflow.context.get("tenant_id"),
                "tags": workflow.context.get("tags", []),
            },
        )

        if decision.effect == PolicyEffect.DENY:
            step.mark_failed(decision.reason)
            workflow.sync_status()
            return StepResult.fail(
                decision.reason,
                step_id=step.id,
                workflow_status=workflow.status,
            )

        if decision.effect == PolicyEffect.LIMIT:
            step.mark_failed(decision.reason)
            workflow.sync_status()
            return StepResult.fail(
                decision.reason,
                next={
                    "action": "wait",
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "hint": "This step is rate-limited. Retry later.",
                },
                step_id=step.id,
                workflow_status=workflow.status,
            )

        if decision.effect == PolicyEffect.ASK:
            if self._approval_service is not None:
                approval_request = await self._approval_service.create_approval_request(
                    capability_name=step.capability_name,
                    arguments=arguments,
                    execution_id=f"wfexec_{workflow.id}_{step.id}",
                    workflow_id=workflow.id,
                )
                await self.pause_for_approval(workflow.id, approval_request.id)
                return StepResult.fail(
                    decision.reason,
                    requires_approval=True,
                    next={
                        "action": "await_approval",
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                        "approval_request_id": approval_request.id,
                        "hint": decision.reason,
                    },
                    step_id=step.id,
                    workflow_status=workflow.status,
                )

            step.status = StepStatus.AWAITING_CONFIRMATION
            workflow.status = WorkflowStatus.PAUSED
            workflow.touch()
            return StepResult.fail(
                decision.reason,
                requires_confirmation=True,
                next={
                    "action": "confirm",
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "hint": decision.reason,
                },
                step_id=step.id,
                workflow_status=workflow.status,
            )

        return None

    def _generate_next(
        self,
        workflow: WorkflowState,
        next_step: Step | None,
    ) -> dict[str, Any] | None:
        """Generate agent guidance for the next action."""
        if next_step is not None:
            return {
                "action": "execute_step",
                "workflow_id": workflow.id,
                "step_id": next_step.id,
                "capability": next_step.capability_name,
                "hint": f"Next step: {next_step.capability_name}",
            }

        if workflow.is_complete:
            return {
                "action": "complete",
                "workflow_id": workflow.id,
                "summary": f"Workflow '{workflow.name}' completed",
            }

        return None
