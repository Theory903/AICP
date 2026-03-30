"""Default workflow runtime implementation.

A workflow runtime that manages multi-step execution with state,
confirmation handling, and agent guidance.
"""

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
    """Default workflow runtime with step orchestration."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        approval_service: "ApprovalService | None" = None,
    ):
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
        workflow_id = str(uuid.uuid4())
        step_objects = []

        if steps:
            for i, step_def in enumerate(steps):
                step = Step(
                    id=step_def.get("id", f"step_{i}"),
                    capability_name=step_def["capability_name"],
                    arguments=step_def.get("arguments", {}),
                )
                step_objects.append(step)

        workflow = WorkflowState(
            id=workflow_id,
            name=name,
            description=description,
            steps=step_objects,
        )
        self._workflows[workflow_id] = workflow
        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        return self._workflows.get(workflow_id)

    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        if workflow.is_complete:
            return StepResult(
                success=False,
                error="Workflow already complete",
            )

        step = workflow.current_step
        if not step:
            return StepResult(
                success=False,
                error="No more steps",
            )

        workflow.status = WorkflowStatus.RUNNING
        workflow.touch()
        step.status = StepStatus.RUNNING
        step.started_at = utc_now_rfc3339()

        merged_args = {**step.arguments}
        if arguments:
            merged_args.update(arguments)
        workflow.context["last_args"] = merged_args

        try:
            if self._policy_engine and not workflow.context.get("confirmation_granted"):
                decision = await self._policy_engine.evaluate(
                    step.capability_name,
                    merged_args,
                    {"workflow_id": workflow_id},
                )
                if decision.effect == PolicyEffect.DENY:
                    step.status = StepStatus.FAILED
                    step.error = decision.reason
                    step.completed_at = utc_now_rfc3339()
                    workflow.status = WorkflowStatus.FAILED
                    workflow.touch()
                    return StepResult(
                        success=False,
                        error=decision.reason,
                    )
                if decision.effect == PolicyEffect.ASK:
                    step.status = StepStatus.AWAITING_CONFIRMATION
                    workflow.status = WorkflowStatus.PAUSED
                    workflow.touch()
                    return StepResult(
                        success=False,
                        requires_confirmation=True,
                        next={
                            "action": "confirm",
                            "workflow_id": workflow_id,
                            "message": decision.reason,
                        },
                    )

            result = await self._provider.execute(
                step.capability_name,
                merged_args,
                {"workflow_id": workflow_id},
            )

            step.status = StepStatus.COMPLETED
            step.result = result
            step.completed_at = utc_now_rfc3339()

            workflow.current_step_index += 1
            workflow.status = (
                WorkflowStatus.COMPLETED if workflow.is_complete else WorkflowStatus.RUNNING
            )
            workflow.touch()

            next_step = workflow.current_step
            return StepResult(
                success=True,
                result=result,
                next=self._generate_next(workflow, next_step),
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = utc_now_rfc3339()
            workflow.status = WorkflowStatus.FAILED
            workflow.touch()
            return StepResult(
                success=False,
                error=str(e),
            )

    def _generate_next(
        self,
        workflow: WorkflowState,
        next_step: Step | None,
    ) -> dict[str, Any] | None:
        if next_step:
            return {
                "action": "execute_step",
                "workflow_id": workflow.id,
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

    async def confirm_and_continue(
        self,
        workflow_id: str,
        confirmed: bool,
        modified_arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        step = workflow.current_step
        if step and step.status == StepStatus.AWAITING_CONFIRMATION:
            if not confirmed:
                step.status = StepStatus.SKIPPED
                workflow.current_step_index += 1
                workflow.status = (
                    WorkflowStatus.COMPLETED if workflow.is_complete else WorkflowStatus.RUNNING
                )
                workflow.touch()
                return StepResult(
                    success=True,
                    result=None,
                    next=self._generate_next(workflow, workflow.current_step),
                )

            args = modified_arguments or workflow.context.get("last_args", {})
            workflow.context["confirmation_granted"] = True
            try:
                return await self.execute_step(workflow_id, args)
            finally:
                workflow.context.pop("confirmation_granted", None)

        return StepResult(success=False, error="No confirmation needed")

    async def skip_step(self, workflow_id: str) -> StepResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        step = workflow.current_step
        if step:
            step.status = StepStatus.SKIPPED

        workflow.current_step_index += 1
        workflow.status = WorkflowStatus.COMPLETED if workflow.is_complete else WorkflowStatus.RUNNING
        workflow.touch()

        return StepResult(
            success=True,
            next=self._generate_next(workflow, workflow.current_step),
        )

    async def retry_step(self, workflow_id: str) -> StepResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        step = workflow.current_step
        if step and step.status == StepStatus.FAILED:
            step.status = StepStatus.PENDING
            step.error = None
            step.started_at = None
            step.completed_at = None
            workflow.status = WorkflowStatus.PENDING
            workflow.touch()
            return await self.execute_step(workflow_id)

        return StepResult(success=False, error="No failed step to retry")

    async def cancel_workflow(self, workflow_id: str) -> bool:
        workflow = self._workflows.get(workflow_id)
        if workflow is not None:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.touch()
            return True
        return False

    async def pause_for_approval(
        self,
        workflow_id: str,
        approval_request_id: str,
    ) -> WorkflowState:
        """Pause a workflow for approval.

        Args:
            workflow_id: ID of the workflow to pause
            approval_request_id: ID of the approval request

        Returns:
            Updated workflow state
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        workflow.status = WorkflowStatus.PAUSED_FOR_APPROVAL
        workflow.metadata["approval_request_id"] = approval_request_id

        step = workflow.current_step
        if step:
            step.status = StepStatus.AWAITING_APPROVAL

        workflow.touch()
        return workflow

    async def resume_after_approval(
        self,
        workflow_id: str,
        approved: bool,
    ) -> StepResult:
        """Resume a workflow after approval decision.

        Args:
            workflow_id: ID of the workflow to resume
            approved: Whether the step was approved

        Returns:
            StepResult from executing the step (if approved)
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        if workflow.status != WorkflowStatus.PAUSED_FOR_APPROVAL:
            raise WorkflowError(f"Workflow not paused for approval: {workflow_id}")

        if not approved:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.touch()
            return StepResult(success=False, error="Approval denied")

        step = workflow.current_step
        if step:
            step.status = StepStatus.PENDING

        workflow.status = WorkflowStatus.RUNNING
        workflow.touch()
        return await self.execute_step(workflow_id)

    async def list_workflows(self) -> list[WorkflowState]:
        return list(self._workflows.values())
