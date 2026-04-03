"""Workflow service backed by runtime persistence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from aicp.implementations.workflow import DefaultWorkflowRuntime
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.workflow_runtime import Step
from aicp.interfaces.policy_engine import PolicyEngine
from aicp.interfaces.workflow_runtime import (
    StepResult,
    WorkflowState,
    WorkflowStatus,
)

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
        self._provider = capability_provider
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
        """Create and persist a workflow."""
        name = self._require_text(name, field_name="name")
        description = str(description or "").strip()
        normalized_steps = deepcopy(steps or [])

        workflow = await self._runtime.create_workflow(
            name=name,
            description=description,
            steps=normalized_steps,
        )
        await self._save_workflow(workflow)

        await self._append_audit(
            event_type="workflow_created",
            actor="runtime",
            workflow_id=workflow.id,
            status=workflow.status.value,
            metadata={"name": workflow.name},
        )

        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Get a workflow from persistence, with runtime fallback."""
        workflow_id = self._require_text(workflow_id, field_name="workflow_id")

        workflow = await self._store.get_workflow(workflow_id)
        if workflow is not None:
            return workflow

        workflow = await self._runtime.get_workflow(workflow_id)
        if workflow is not None:
            await self._save_workflow(workflow)

        return workflow

    async def list_workflows(self) -> list[WorkflowState]:
        """List persisted workflows."""
        return await self._store.list_workflows()

    async def get_workflow_detail(self, workflow_id: str) -> dict[str, Any] | None:
        """Return an enriched workflow detail view with timeline data."""
        workflow = await self.get_workflow(workflow_id)
        if workflow is None:
            return None

        history = await self._list_workflow_history(workflow.id)
        capability_map = await self._get_capability_map(workflow.steps)
        approval_map = await self._get_approval_map(workflow, history)
        timeline = self._build_workflow_timeline(
            workflow=workflow,
            history=history,
            capability_map=capability_map,
            approval_map=approval_map,
        )

        return {
            "workflow": self._build_workflow_view(
                workflow=workflow,
                capability_map=capability_map,
                approval_map=approval_map,
            ),
            "timeline": timeline,
        }

    async def get_workflow_timeline(self, workflow_id: str) -> dict[str, Any] | None:
        """Return a workflow timeline view."""
        detail = await self.get_workflow_detail(workflow_id)
        if detail is None:
            return None

        workflow = detail["workflow"]
        return {
            "workflow_id": workflow["id"],
            "workflow_status": workflow["status"],
            "current_step_id": workflow["current_step_id"],
            "current_step_capability": workflow["current_step_capability"],
            "events": detail["timeline"],
        }

    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute the next step of a workflow."""
        workflow_id = self._require_text(workflow_id, field_name="workflow_id")
        safe_arguments = deepcopy(arguments or {})
        actor = str(safe_arguments.get("requester") or "agent")
        workflow_before = await self.get_workflow(workflow_id)
        current_step = (
            workflow_before.current_step if workflow_before is not None else None
        )

        if current_step is not None:
            await self._append_audit(
                event_type="workflow_step_started",
                actor=actor,
                workflow_id=workflow_id,
                step_id=current_step.id,
                capability_name=current_step.capability_name,
                status="running",
                metadata={"step_status": "running"},
            )

        result = await self._runtime.execute_step(workflow_id, safe_arguments)
        workflow = await self._runtime.get_workflow(workflow_id)

        if (
            result.requires_confirmation
            and workflow is not None
            and self._approvals is not None
        ):
            await self._create_approval_for_current_step(
                workflow, safe_arguments, result
            )
            result.requires_approval = True

        if workflow is not None:
            await self._save_workflow(workflow)

        await self._append_audit(
            event_type="workflow_step_executed",
            actor=actor,
            workflow_id=workflow_id,
            step_id=current_step.id if current_step is not None else result.step_id,
            capability_name=current_step.capability_name if current_step is not None else None,
            approval_request_id=self._get_approval_request_id(result, workflow),
            status="awaiting_approval"
            if result.requires_approval
            else "awaiting_confirmation"
            if result.requires_confirmation
            else ("success" if result.success else "failure"),
            metadata={
                "success": result.success,
                "error": result.error,
                "requires_confirmation": result.requires_confirmation,
                "requires_approval": result.requires_approval,
            },
        )

        await self._append_step_outcome_event(
            workflow=workflow,
            step=current_step,
            result=result,
            actor=actor,
        )

        return result

    async def publish_event(
        self,
        workflow_id: str,
        name: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to a waiting workflow step."""
        workflow_id = self._require_text(workflow_id, field_name="workflow_id")
        await self._runtime.publish_event(workflow_id, name, payload)

    async def resume_after_approval(
        self,
        workflow_id: str,
        approval_id: str,
        decision: str | None = None,
        approver: str | None = None,
    ) -> StepResult:
        """Resume a workflow after an approval decision."""
        workflow_id = self._require_text(workflow_id, field_name="workflow_id")
        approval_id = self._require_text(approval_id, field_name="approval_id")

        if decision is not None:
            if self._approvals is None:
                raise ValueError("Approval service is not configured")
            if approver is None:
                raise ValueError("approver is required when recording a decision")

            await self._approvals.decide(
                approval_id,
                decision=decision,
                approver=approver,
            )

        if self._approvals is None:
            raise ValueError("Approval service is not configured")

        approval = await self._approvals.get_approval(approval_id)
        if approval is None:
            raise ValueError(f"Approval request not found: {approval_id}")

        workflow = await self._runtime.get_workflow(workflow_id)
        if workflow is None:
            workflow = await self._store.get_workflow(workflow_id)

        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if approval.get("status") != "approved":
            current_step = workflow.current_step
            if current_step is not None:
                current_step.mark_failed("Approval was not granted")
                current_step.metadata["approval_request_id"] = approval_id
                current_step.metadata["approval_status"] = str(
                    approval.get("status") or "rejected"
                )
            workflow.status = WorkflowStatus.FAILED
            workflow.touch()
            await self._save_workflow(workflow)

            await self._append_audit(
                event_type="workflow_step_failed",
                actor=str(approval.get("decided_by") or approver or "approver"),
                workflow_id=workflow_id,
                step_id=current_step.id if current_step is not None else None,
                capability_name=current_step.capability_name
                if current_step is not None
                else None,
                approval_request_id=approval_id,
                status="failure",
                metadata={
                    "error": "Approval was not granted",
                    "approval_status": approval.get("status"),
                },
            )

            await self._append_audit(
                event_type="workflow_resume_rejected",
                actor=str(approval.get("decided_by") or approver or "approver"),
                workflow_id=workflow_id,
                approval_request_id=approval_id,
                status="failure",
                metadata={"approval_status": approval.get("status")},
            )

            return StepResult(success=False, error="Approval was not granted")

        runtime_args = deepcopy(
            approval.get("modified_arguments") or approval.get("arguments") or {}
        )
        current_step = workflow.current_step
        if current_step is not None:
            current_step.metadata["approval_request_id"] = approval_id
            current_step.metadata["approval_status"] = "approved"

        await self._append_audit(
            event_type="workflow_step_resumed",
            actor=str(approval.get("decided_by") or approver or "approver"),
            workflow_id=workflow_id,
            step_id=current_step.id if current_step is not None else None,
            capability_name=current_step.capability_name if current_step is not None else None,
            approval_request_id=approval_id,
            status="running",
            metadata={"approval_status": approval.get("status")},
        )

        result = await self._runtime.confirm_and_continue(
            workflow_id,
            confirmed=True,
            modified_arguments=runtime_args,
        )

        updated_workflow = await self._runtime.get_workflow(workflow_id)
        if updated_workflow is not None:
            await self._save_workflow(updated_workflow)

        await self._append_step_outcome_event(
            workflow=updated_workflow,
            step=current_step,
            result=result,
            actor=str(approval.get("decided_by") or approver or "approver"),
            approval_request_id=approval_id,
        )

        await self._append_audit(
            event_type="workflow_resumed_after_approval",
            actor=str(approval.get("decided_by") or approver or "approver"),
            workflow_id=workflow_id,
            step_id=current_step.id if current_step is not None else None,
            capability_name=current_step.capability_name if current_step is not None else None,
            approval_request_id=approval_id,
            status="success" if result.success else "failure",
            metadata={"error": result.error},
        )

        return result

    async def _create_approval_for_current_step(
        self,
        workflow: WorkflowState,
        arguments: dict[str, Any],
        result: StepResult,
    ) -> None:
        """Create an approval request for the current workflow step."""
        if self._approvals is None:
            return

        step = workflow.current_step
        last_args = deepcopy(workflow.context.get("last_args", {}))
        requester = str(arguments.get("requester") or "agent")
        message = (
            result.next.get("message", "Approval required")
            if result.next
            else "Approval required"
        )

        approval = await self._approvals.create_approval_request(
            capability_name=step.capability_name if step is not None else "unknown",
            workflow_id=workflow.id,
            arguments=last_args,
            requester=requester,
            message=message,
            step_id=step.id if step is not None else None,
        )

        workflow.metadata["approval_request_id"] = approval["id"]
        if step is not None:
            step.metadata["approval_request_id"] = approval["id"]
            step.metadata["approval_status"] = "pending"
        if result.next is None:
            result.next = {}
        result.next["approval_request_id"] = approval["id"]
        result.next.setdefault("workflow_id", workflow.id)
        result.next.setdefault("action", "await_approval")
        workflow.touch()

    async def _save_workflow(self, workflow: WorkflowState) -> None:
        """Persist a workflow."""
        await self._store.save_workflow(workflow)

    async def _append_audit(
        self,
        event_type: str,
        actor: str,
        **fields: Any,
    ) -> None:
        """Append an audit event if audit service is configured."""
        if self._audit is None:
            return
        await self._audit.append(event_type=event_type, actor=actor, **fields)

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        """Require a non-empty text value."""
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    async def _list_workflow_history(self, workflow_id: str) -> list[dict[str, Any]]:
        """List workflow audit entries when audit service is configured."""
        if self._audit is None:
            return []
        return await self._audit.list_entries(workflow_id=workflow_id)

    async def _get_capability_map(self, steps: list[Step]) -> dict[str, dict[str, Any]]:
        """Resolve capability metadata used by workflow views."""
        capability_map: dict[str, dict[str, Any]] = {}

        for step in steps:
            capability_name = step.capability_name
            if capability_name in capability_map:
                continue

            capability = await self._provider.get_capability(capability_name)
            rollback_capability = None
            rollback_available = False
            if capability is not None:
                rollback_capability = getattr(capability, "rollback_capability", None)
                if isinstance(rollback_capability, str) and rollback_capability.strip():
                    rollback_available = await self._provider.has_capability(
                        rollback_capability
                    )

            capability_map[capability_name] = {
                "rollback_capability": rollback_capability,
                "available": rollback_available,
            }

        return capability_map

    async def _get_approval_map(
        self,
        workflow: WorkflowState,
        history: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Build approval linkage keyed by step id."""
        step_approvals: dict[str, dict[str, Any]] = {}

        for entry in history:
            approval_request_id = entry.get("approval_request_id")
            step_id = entry.get("step_id")
            if not isinstance(approval_request_id, str) or not approval_request_id.strip():
                continue
            if isinstance(step_id, str) and step_id.strip():
                step_approvals.setdefault(step_id, {})["approval_request_id"] = approval_request_id
            if entry.get("event_type") == "approval_request_created" and isinstance(step_id, str):
                step_approvals.setdefault(step_id, {})["approval_status"] = "pending"
            metadata = entry.get("metadata") or {}
            if entry.get("event_type") == "approval_decision_made" and isinstance(step_id, str):
                decision = str(metadata.get("decision") or "").strip()
                if decision:
                    step_approvals.setdefault(step_id, {})["approval_status"] = decision

        approval_request_id = workflow.metadata.get("approval_request_id")
        current_step = workflow.current_step
        if isinstance(approval_request_id, str) and approval_request_id.strip():
            if current_step is not None:
                step_approvals.setdefault(current_step.id, {})["approval_request_id"] = approval_request_id

        if self._approvals is None:
            return step_approvals

        for step_id, approval_data in step_approvals.items():
            request_id = approval_data.get("approval_request_id")
            if not isinstance(request_id, str) or not request_id.strip():
                continue
            approval = await self._approvals.get_approval(request_id)
            if approval is None:
                continue
            approval_data["approval_status"] = str(approval.get("status") or "pending")

        return step_approvals

    def _build_workflow_view(
        self,
        *,
        workflow: WorkflowState,
        capability_map: dict[str, dict[str, Any]],
        approval_map: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Serialize an enriched workflow view."""
        current_step = workflow.current_step
        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "current_step_id": current_step.id if current_step is not None else None,
            "current_step_capability": current_step.capability_name
            if current_step is not None
            else None,
            "current_step_index": workflow.current_step_index,
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "metadata": deepcopy(workflow.metadata),
            "steps": [
                self._build_step_view(step, capability_map, approval_map)
                for step in workflow.steps
            ],
        }

    def _build_step_view(
        self,
        step: Step,
        capability_map: dict[str, dict[str, Any]],
        approval_map: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Serialize an enriched workflow step view."""
        approval = approval_map.get(step.id, {})
        return {
            "id": step.id,
            "capability_name": step.capability_name,
            "status": step.status.value,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "result": step.result,
            "error": step.error,
            "metadata": deepcopy(step.metadata),
            "approval_request_id": approval.get("approval_request_id")
            or step.metadata.get("approval_request_id"),
            "approval_status": approval.get("approval_status")
            or step.metadata.get("approval_status"),
            "compensation": deepcopy(
                capability_map.get(
                    step.capability_name,
                    {"rollback_capability": None, "available": False},
                )
            ),
        }

    def _build_workflow_timeline(
        self,
        *,
        workflow: WorkflowState,
        history: list[dict[str, Any]],
        capability_map: dict[str, dict[str, Any]],
        approval_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build a workflow timeline from audit history."""
        steps_by_id = {step.id: step for step in workflow.steps}
        timeline: list[dict[str, Any]] = []

        for entry in sorted(history, key=lambda item: str(item.get("timestamp", ""))):
            step_id = entry.get("step_id")
            step = steps_by_id.get(step_id) if isinstance(step_id, str) else None
            capability_name = entry.get("capability_name")
            if not isinstance(capability_name, str) or not capability_name.strip():
                capability_name = step.capability_name if step is not None else None

            approval = (
                approval_map.get(step_id, {}) if isinstance(step_id, str) else {}
            )
            approval_request_id = entry.get("approval_request_id") or approval.get(
                "approval_request_id"
            )
            approval_status = approval.get("approval_status")
            metadata = deepcopy(entry.get("metadata") or {})
            entry_approval_status = metadata.get("approval_status")
            if entry_approval_status is not None:
                approval_status = str(entry_approval_status) or None
            if entry.get("event_type") == "approval_request_created":
                approval_status = "pending"
            if entry.get("event_type") == "approval_decision_made":
                approval_status = str(metadata.get("decision") or approval_status or "") or None

            compensation = {"rollback_capability": None, "available": False}
            if isinstance(capability_name, str) and capability_name.strip():
                compensation = deepcopy(
                    capability_map.get(
                        capability_name,
                        {"rollback_capability": None, "available": False},
                    )
                )

            timeline.append(
                {
                    "id": entry.get("id"),
                    "timestamp": entry.get("timestamp"),
                    "event_type": entry.get("event_type"),
                    "title": self._timeline_title(entry.get("event_type")),
                    "actor": entry.get("actor"),
                    "status": entry.get("status"),
                    "workflow_id": entry.get("workflow_id") or workflow.id,
                    "step_id": step_id,
                    "capability_name": capability_name,
                    "approval_request_id": approval_request_id,
                    "approval_status": approval_status,
                    "compensation": compensation,
                    "summary": self._timeline_summary(entry, capability_name),
                    "metadata": metadata,
                }
            )

        return timeline

    async def _append_step_outcome_event(
        self,
        *,
        workflow: WorkflowState | None,
        step: Step | None,
        result: StepResult,
        actor: str,
        approval_request_id: str | None = None,
    ) -> None:
        """Append a granular step lifecycle audit event."""
        if step is None:
            return

        event_type: str
        status: str
        metadata: dict[str, Any] = {
            "error": result.error,
            "requires_confirmation": result.requires_confirmation,
            "requires_approval": result.requires_approval,
        }

        if result.requires_confirmation or result.requires_approval:
            event_type = "workflow_step_waiting"
            status = "awaiting_approval" if result.requires_approval else "awaiting_confirmation"
            metadata["approval_status"] = (
                "pending" if result.requires_approval else None
            )
        elif result.success:
            event_type = "workflow_step_completed"
            status = "success"
        else:
            event_type = "workflow_step_failed"
            status = "failure"

        await self._append_audit(
            event_type=event_type,
            actor=actor,
            workflow_id=workflow.id if workflow is not None else None,
            step_id=step.id,
            capability_name=step.capability_name,
            approval_request_id=approval_request_id or self._get_approval_request_id(result, workflow),
            status=status,
            metadata=metadata,
        )

    def _get_approval_request_id(
        self,
        result: StepResult,
        workflow: WorkflowState | None,
    ) -> str | None:
        """Extract approval request linkage from a result/workflow pair."""
        if result.next is not None:
            approval_request_id = result.next.get("approval_request_id")
            if isinstance(approval_request_id, str) and approval_request_id.strip():
                return approval_request_id
        if workflow is not None:
            approval_request_id = workflow.metadata.get("approval_request_id")
            if isinstance(approval_request_id, str) and approval_request_id.strip():
                return approval_request_id
        return None

    def _timeline_title(self, event_type: Any) -> str:
        """Return a short title for a timeline event."""
        title_map = {
            "workflow_created": "Workflow created",
            "workflow_step_started": "Step started",
            "workflow_step_executed": "Step executed",
            "workflow_step_waiting": "Step paused",
            "workflow_step_resumed": "Step resumed",
            "workflow_step_completed": "Step completed",
            "workflow_step_failed": "Step failed",
            "approval_request_created": "Approval requested",
            "approval_decision_made": "Approval decided",
            "workflow_resume_rejected": "Workflow resume rejected",
            "workflow_resumed_after_approval": "Workflow resumed after approval",
        }
        return title_map.get(str(event_type), str(event_type or "event"))

    def _timeline_summary(self, entry: dict[str, Any], capability_name: str | None) -> str:
        """Build a readable summary for a workflow timeline event."""
        event_type = entry.get("event_type")
        metadata = entry.get("metadata") or {}
        capability_label = capability_name or "step"

        if event_type == "workflow_created":
            return "Workflow entered runtime and was persisted."
        if event_type == "workflow_step_started":
            return f"Step started: {capability_label}"
        if event_type == "workflow_step_waiting":
            if metadata.get("requires_approval"):
                return f"Step paused for approval: {capability_label}"
            return f"Step paused for confirmation: {capability_label}"
        if event_type == "workflow_step_resumed":
            return f"Step resumed: {capability_label}"
        if event_type == "workflow_step_completed":
            return f"Step completed: {capability_label}"
        if event_type == "workflow_step_failed":
            error = metadata.get("error") or entry.get("status") or "unknown error"
            return f"Step failed: {error}"
        if event_type == "approval_request_created":
            return metadata.get("message") or "Approval required before continuation."
        if event_type == "approval_decision_made":
            decision = metadata.get("decision")
            reason = metadata.get("reason")
            if decision and reason:
                return f"Decision: {decision}. Reason: {reason}"
            if decision:
                return f"Decision: {decision}"
            return "Approval decision recorded."
        if event_type == "workflow_resumed_after_approval":
            return metadata.get("error") or "Workflow resumed after approval."
        if event_type == "workflow_resume_rejected":
            return "Workflow could not continue because approval was not granted."
        if event_type == "workflow_step_executed":
            if metadata.get("success"):
                return "Step execution recorded."
            return metadata.get("error") or "Step execution recorded."
        return "Runtime event recorded."
