"""Workflow service backed by runtime persistence."""

from typing import Any

from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.policy_engine import PolicyEngine
from aicp.interfaces.workflow_runtime import StepResult, WorkflowState
from aicp.implementations.workflow import DefaultWorkflowRuntime

from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.audit import AuditService


class WorkflowService:
    """Workflow lifecycle service for the runtime package."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        runtime_store: RuntimeStore,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
        audit_service: AuditService | None = None,
    ):
        self._store = runtime_store
        self._runtime = DefaultWorkflowRuntime(capability_provider, policy_engine)
        self._approvals = approval_service
        self._audit = audit_service

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: list[dict[str, Any]] | None = None,
    ) -> WorkflowState:
        workflow = await self._runtime.create_workflow(name, description, steps)
        await self._store.save_workflow(workflow)
        if self._audit is not None:
            await self._audit.append(
                event_type="workflow_created",
                actor="runtime",
                workflow_id=workflow.id,
                status="pending",
            )
        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        workflow = await self._store.get_workflow(workflow_id)
        if workflow is not None:
            return workflow
        return await self._runtime.get_workflow(workflow_id)

    async def list_workflows(self) -> list[WorkflowState]:
        return await self._store.list_workflows()

    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        result = await self._runtime.execute_step(workflow_id, arguments)
        workflow = await self._runtime.get_workflow(workflow_id)
        if result.requires_confirmation and workflow is not None and self._approvals is not None:
            step = workflow.current_step
            last_args = workflow.context.get("last_args", {})
            requester = (arguments or {}).get("requester") or "agent"
            await self._approvals.create_approval_request(
                capability_name=step.capability_name if step is not None else "unknown",
                workflow_id=workflow_id,
                arguments=last_args,
                requester=requester,
                message=result.next.get("message", "Approval required") if result.next else "Approval required",
                step_id=step.id if step is not None else None,
            )
        if workflow is not None:
            await self._store.save_workflow(workflow)
        return result

    async def resume_after_approval(
        self,
        workflow_id: str,
        approval_id: str,
        decision: str | None = None,
        approver: str | None = None,
    ) -> StepResult:
        if decision is not None:
            if self._approvals is None or approver is None:
                raise ValueError("Approval service and approver are required to record a decision")
            await self._approvals.decide(approval_id, decision=decision, approver=approver)

        if self._approvals is None:
            raise ValueError("Approval service is not configured")

        approval = await self._approvals.get_approval(approval_id)
        if approval is None:
            raise ValueError(f"Approval request not found: {approval_id}")
        if approval["status"] != "approved":
            workflow = await self._runtime.get_workflow(workflow_id)
            if workflow is not None:
                workflow.status = "failed"
                workflow.touch()
                await self._store.save_workflow(workflow)
            return StepResult(success=False, error="Approval was not granted")

        runtime_args = approval.get("arguments", {})
        result = await self._runtime.confirm_and_continue(
            workflow_id,
            confirmed=True,
            modified_arguments=runtime_args,
        )
        workflow = await self._runtime.get_workflow(workflow_id)
        if workflow is not None:
            await self._store.save_workflow(workflow)
        return result
