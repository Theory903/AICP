"""Default workflow runtime implementation.

A workflow runtime that manages multi-step execution with state,
confirmation handling, and agent guidance.
"""

import time
import uuid
from typing import Any

from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.policy_engine import PolicyEffect, PolicyEngine
from aicp.interfaces.workflow_runtime import (
    Step,
    StepResult,
    StepStatus,
    WorkflowError,
    WorkflowRuntime,
    WorkflowState,
)


class DefaultWorkflowRuntime(WorkflowRuntime):
    """Default workflow runtime with step orchestration."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
    ):
        self._provider = capability_provider
        self._policy_engine = policy_engine
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

        step.status = StepStatus.RUNNING
        step.started_at = time.time()

        merged_args = {**step.arguments}
        if arguments:
            merged_args.update(arguments)
        workflow.context["last_args"] = merged_args

        try:
            if self._policy_engine:
                decision = await self._policy_engine.evaluate(
                    step.capability_name,
                    merged_args,
                    {"workflow_id": workflow_id},
                )
                if decision.effect == PolicyEffect.DENY:
                    step.status = StepStatus.FAILED
                    step.error = decision.reason
                    return StepResult(
                        success=False,
                        error=decision.reason,
                    )
                if decision.effect == PolicyEffect.ASK:
                    step.status = StepStatus.AWAITING_CONFIRMATION
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
            step.completed_at = time.time()

            workflow.current_step_index += 1

            next_step = workflow.current_step
            return StepResult(
                success=True,
                result=result,
                next=self._generate_next(workflow, next_step),
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = time.time()
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
                return StepResult(
                    success=True,
                    result=None,
                    next=self._generate_next(workflow, workflow.current_step),
                )

            args = modified_arguments or workflow.context.get("last_args", {})
            return await self.execute_step(workflow_id, args)

        return StepResult(success=False, error="No confirmation needed")

    async def skip_step(self, workflow_id: str) -> StepResult:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        step = workflow.current_step
        if step:
            step.status = StepStatus.SKIPPED

        workflow.current_step_index += 1

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
            return await self.execute_step(workflow_id)

        return StepResult(success=False, error="No failed step to retry")

    async def cancel_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    async def list_workflows(self) -> list[WorkflowState]:
        return list(self._workflows.values())
