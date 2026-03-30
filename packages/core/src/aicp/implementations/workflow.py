"""Default workflow runtime implementation.

A workflow runtime that manages multi-step execution with state,
confirmation handling, approval handling, and agent guidance.
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
    utc_now_rfc3339,
)

if TYPE_CHECKING:
    from aicp.approval_service import ApprovalService


class DefaultWorkflowRuntime(WorkflowRuntime):
    """Default workflow runtime with in-memory step orchestration."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        approval_service: "ApprovalService | None" = None,
    ) -> None:
        self._provider = capability_provider
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._workflows: dict[str, WorkflowState] = {}

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
            if "capability_name" not in step_def:
                raise WorkflowError(
                    "Each workflow step must include 'capability_name'",
                    workflow_id=workflow_id,
                    details={"step_index": index, "step": step_def},
                )

            step_objects.append(
                Step(
                    id=str(step_def.get("id", f"step_{index}")),
                    capability_name=step_def["capability_name"],
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

        workflow.status = WorkflowStatus.PAUSED_FOR_APPROVAL
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

        if workflow.status != WorkflowStatus.PAUSED_FOR_APPROVAL:
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