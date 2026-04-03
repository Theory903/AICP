"""AI-facing v1 action surface routes."""

from __future__ import annotations

from enum import Enum
from typing import Any

from aicp.interfaces.executor import ExecutionResult
from aicp.interfaces.workflow_runtime import StepResult
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator

from aicp_runtime.ai.intent_router import IntentRouter
from aicp_runtime.ai.judge import AICJudge, JudgeError
from aicp_runtime.ai.planner import AICPlanner, PlannerError, PlannerOutput, PlanStep
from aicp_runtime.auth.models import SessionAuthRecipe, SessionState
from aicp_runtime.interactions.models import AgentInteractionState
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService
from aicp_runtime.services.interactions import InteractionStateService
from aicp_runtime.services.sessions import SessionService
from aicp_runtime.services.workflows import WorkflowService


class AgentExecutionStatus(str, Enum):
    RUNNING = "running"
    PAUSED_FOR_APPROVAL = "paused_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyTrigger(BaseModel):
    policy_name: str | None = None
    effect: str = "ask"
    reason: str
    required_role: str | None = None


class ApprovalRequestView(BaseModel):
    id: str
    workflow_id: str | None = None
    execution_id: str | None = None
    capability_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    trigger: PolicyTrigger
    status: ApprovalStatus
    requested_at: str | None = None
    expires_at: str | None = None
    decided_at: str | None = None
    decided_by: str | None = None


class ContinuationHint(BaseModel):
    action: str
    message: str
    capability_name: str | None = None
    approval_request_id: str | None = None
    workflow_id: str | None = None
    execution_id: str | None = None


class AgentErrorPayload(BaseModel):
    message: str | None = None
    code: str | None = None
    fix_hint: str | None = None


class AgentExecutionResponse(BaseModel):
    execution_id: str | None = None
    workflow_id: str | None = None
    status: AgentExecutionStatus
    capability_name: str | None = None
    step_id: str | None = None
    data: Any = None
    error: AgentErrorPayload | None = None
    warnings: list[dict[str, Any]] | None = None
    approval_request: ApprovalRequestView | None = None
    next: ContinuationHint | None = None


class AgentWorkflowView(BaseModel):
    id: str
    name: str
    description: str = ""
    status: str
    current_step_id: str | None = None
    current_step_capability: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecuteRequest(BaseModel):
    capability_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability_name", mode="before")
    @classmethod
    def _normalize_capability_name(cls, value: Any) -> str:
        capability_name = str(value or "").strip()
        if not capability_name:
            raise ValueError("capability_name cannot be empty")
        return capability_name

    @field_validator("arguments", "context", mode="before")
    @classmethod
    def _normalize_mapping(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("must be an object")
        return value


class AgentWorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ValueError("name cannot be empty")
        return name


class AgentWorkflowExecuteRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def _normalize_arguments(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("arguments must be an object")
        return value


class AgentApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    approver_id: str = Field(min_length=1)
    reason: str | None = None
    modified_arguments: dict[str, Any] | None = None

    @field_validator("approver_id", mode="before")
    @classmethod
    def _normalize_approver_id(cls, value: Any) -> str:
        approver_id = str(value or "").strip()
        if not approver_id:
            raise ValueError("approver_id cannot be empty")
        return approver_id


class AgentSessionCreateRequest(BaseModel):
    provider_name: str = Field(min_length=1)
    auth_mode: str = Field(min_length=1)
    cookies: list[dict[str, Any]] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    tokens: dict[str, str] = Field(default_factory=dict)
    csrf_tokens: dict[str, str] = Field(default_factory=dict)
    auth_recipe: SessionAuthRecipe | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    selected_context: dict[str, Any] = Field(default_factory=dict)
    expires_at: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    refreshable: bool = False

    @field_validator("provider_name", "auth_mode", mode="before")
    @classmethod
    def _normalize_required_text(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class AgentInteractionCreateRequest(BaseModel):
    session_id: str | None = None
    selected_context: dict[str, Any] = Field(default_factory=dict)
    resource_cache: dict[str, Any] = Field(default_factory=dict)
    pending_forms: dict[str, Any] = Field(default_factory=dict)
    pagination_state: dict[str, Any] = Field(default_factory=dict)
    upload_state: dict[str, Any] = Field(default_factory=dict)


class AgentInteractionUpdateRequest(BaseModel):
    session_id: str | None = None
    selected_context: dict[str, Any] | None = None
    resource_cache: dict[str, Any] | None = None
    pending_forms: dict[str, Any] | None = None
    pagination_state: dict[str, Any] | None = None
    upload_state: dict[str, Any] | None = None
    last_capability: str | None = None
    last_result_summary: dict[str, Any] | None = None


class RankedCapabilityView(BaseModel):
    capability: dict[str, Any]
    score: int
    reasons: list[str] = Field(default_factory=list)


class ExecutionRecordView(BaseModel):
    execution_id: str
    capability_name: str
    status: str
    created_at: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class AgentSurfaceMapper:
    @classmethod
    async def from_execution_result(
        cls,
        *,
        result: ExecutionResult,
        capability_name: str,
        approval_service: ApprovalService,
    ) -> AgentExecutionResponse:
        approval_request = None
        approval_request_id = getattr(result, "approval_request_id", None)
        if isinstance(approval_request_id, str) and approval_request_id.strip():
            approval_request = await approval_service.get_approval(approval_request_id)

        if result.status.value == "success":
            return AgentExecutionResponse(
                execution_id=getattr(result, "execution_id", None),
                capability_name=capability_name,
                status=AgentExecutionStatus.COMPLETED,
                data=result.data,
                warnings=result.warnings,
                next=cls.continuation_hint(result.next),
            )

        if result.error_code == "requires_approval":
            return AgentExecutionResponse(
                execution_id=getattr(result, "execution_id", None),
                capability_name=capability_name,
                status=AgentExecutionStatus.PAUSED_FOR_APPROVAL,
                approval_request=cls.approval_view(approval_request),
                next=cls.continuation_hint(result.next),
                error=cls.error_payload(result),
            )

        return AgentExecutionResponse(
            execution_id=getattr(result, "execution_id", None),
            capability_name=capability_name,
            status=AgentExecutionStatus.FAILED,
            error=cls.error_payload(result),
            next=cls.continuation_hint(result.next),
        )

    @classmethod
    def from_step_result(
        cls,
        *,
        workflow_id: str,
        capability_name: str | None,
        step_id: str | None,
        step_result: StepResult,
        approval_request: dict[str, Any] | None,
    ) -> AgentExecutionResponse:
        if step_result.success:
            return AgentExecutionResponse(
                workflow_id=workflow_id,
                capability_name=capability_name,
                step_id=step_id,
                status=AgentExecutionStatus.COMPLETED,
                data=step_result.result,
                next=cls.continuation_hint(step_result.next),
            )

        if step_result.requires_approval or approval_request is not None:
            return AgentExecutionResponse(
                workflow_id=workflow_id,
                capability_name=capability_name,
                step_id=step_id,
                status=AgentExecutionStatus.PAUSED_FOR_APPROVAL,
                approval_request=cls.approval_view(approval_request),
                next=cls.continuation_hint(step_result.next),
                error=AgentErrorPayload(message=step_result.error),
            )

        return AgentExecutionResponse(
            workflow_id=workflow_id,
            capability_name=capability_name,
            step_id=step_id,
            status=AgentExecutionStatus.FAILED,
            error=AgentErrorPayload(message=step_result.error),
            next=cls.continuation_hint(step_result.next),
        )

    @classmethod
    def approval_view(
        cls, approval: dict[str, Any] | None
    ) -> ApprovalRequestView | None:
        if approval is None:
            return None

        raw_arguments = (
            approval.get("modified_arguments") or approval.get("arguments") or {}
        )
        arguments = raw_arguments if isinstance(raw_arguments, dict) else {}

        raw_status = str(approval.get("status") or "pending").strip().lower()
        status_value = (
            ApprovalStatus.APPROVED
            if raw_status == "approved"
            else ApprovalStatus.REJECTED
            if raw_status == "rejected"
            else ApprovalStatus.PENDING
        )

        trigger_effect = (
            str(
                approval.get("policy_effect") or approval.get("effect") or "ask"
            ).strip()
            or "ask"
        )

        return ApprovalRequestView(
            id=str(approval.get("id") or ""),
            workflow_id=optional_text(approval.get("workflow_id")),
            execution_id=optional_text(approval.get("execution_id")),
            capability_name=str(approval.get("capability_name") or "unknown"),
            arguments=arguments,
            trigger=PolicyTrigger(
                policy_name=optional_text(approval.get("policy_matched")),
                effect=trigger_effect,
                reason=str(approval.get("message") or "Approval required"),
                required_role=optional_text(
                    approval.get("required_role") or approval.get("approver_role")
                ),
            ),
            status=status_value,
            requested_at=optional_text(
                approval.get("requested_at") or approval.get("created_at")
            ),
            expires_at=optional_text(approval.get("expires_at")),
            decided_at=optional_text(approval.get("decided_at")),
            decided_by=optional_text(approval.get("decided_by")),
        )

    @classmethod
    def continuation_hint(
        cls, next_payload: dict[str, Any] | None
    ) -> ContinuationHint | None:
        if not isinstance(next_payload, dict):
            return None

        action = str(next_payload.get("action") or "complete")
        message = str(next_payload.get("hint") or next_payload.get("message") or action)

        return ContinuationHint(
            action=action,
            message=message,
            capability_name=optional_text(next_payload.get("capability")),
            approval_request_id=optional_text(next_payload.get("approval_request_id")),
            workflow_id=optional_text(next_payload.get("workflow_id")),
            execution_id=optional_text(next_payload.get("execution_id")),
        )

    @classmethod
    def error_payload(cls, result: ExecutionResult) -> AgentErrorPayload:
        return AgentErrorPayload(
            message=result.error,
            code=result.error_code,
            fix_hint=cls._fix_hint(result),
        )

    @staticmethod
    def _fix_hint(result: ExecutionResult) -> str | None:
        if result.error_code == "requires_approval":
            return "Wait for approval or submit an approval decision."
        if result.error_code == "missing_session":
            return "Attach a compatible session before retrying this capability."
        if result.error_code == "needs_reauthentication":
            return "Refresh or recreate the session before retrying this capability."
        if result.error_code == "provider_session_mismatch":
            return "Use a session created for the capability's provider."
        if result.error_code == "tenant_session_mismatch":
            return (
                "Use a session scoped to the requested tenant or switch tenant context."
            )
        if result.error_code == "output_validation_failed":
            return (
                "Inspect the provider response and update the declared "
                "output schema or execution adapter."
            )
        if result.error_code in {"validation_error", "invalid_input"}:
            return "Review the input payload and try again."
        if result.error_code == "not_found":
            return "Verify identifiers and resource existence."
        if result.error_code == "execution_failed":
            return "Check the capability implementation and downstream service health."
        return None


# ---------------------------------------------------------------------------
# AI plane request / response models
# ---------------------------------------------------------------------------


class PlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    available_capabilities: list[str] | None = Field(default=None)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal", mode="before")
    @classmethod
    def _normalize_goal(cls, value: Any) -> str:
        goal = str(value or "").strip()
        if not goal:
            raise ValueError("goal cannot be empty")
        return goal


class PlanStepView(BaseModel):
    step_id: str
    capability_name: str
    depends_on: list[str] = Field(default_factory=list)
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class PlanResponse(BaseModel):
    plan_id: str
    goal: str
    generated_at: str
    steps: list[PlanStepView]


class RouteRequest(BaseModel):
    utterance: str = Field(min_length=0)
    available_capabilities: list[dict[str, Any]] | None = Field(default=None)

    @field_validator("utterance", mode="before")
    @classmethod
    def _normalize_utterance(cls, value: Any) -> str:
        return str(value or "").strip()


class RouteResponse(BaseModel):
    destination: str
    capability_name: str | None = None
    confidence: float
    clarification_prompt: str | None = None
    rejection_reason: str | None = None


class JudgeRequest(BaseModel):
    plan: dict[str, Any]

    @field_validator("plan", mode="before")
    @classmethod
    def _require_plan(cls, value: Any) -> dict[str, Any]:
        if value is None:
            raise ValueError("plan must not be None")
        if not isinstance(value, dict):
            raise ValueError("plan must be an object")
        return value


class JudgeResponse(BaseModel):
    verdict: str
    score: float
    rationale: str
    evaluated_at: str


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def build_v1_router(
    discovery_service: DiscoveryService,
    execution_service: ExecutionService,
    approval_service: ApprovalService,
    interaction_service: InteractionStateService,
    session_service: SessionService,
    workflow_service: WorkflowService,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["ai-action-surface"])

    @router.post("/execute", response_model=AgentExecutionResponse)
    async def execute_action(
        request: AgentExecuteRequest,
        response: Response,
    ) -> AgentExecutionResponse:
        try:
            result = await execution_service.execute(
                capability_name=request.capability_name,
                arguments=request.arguments,
                context=request.context,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Execution failed: {exc}",
            ) from exc

        next_action = (result.next or {}).get("action") if result.next else None
        if next_action == "resume_approved":
            approval_request_id = (result.next or {}).get("approval_request_id")
            execution_id = (result.next or {}).get("execution_id")
            if approval_request_id and execution_id:
                try:
                    resume_result = await execution_service.resume_execution(
                        execution_id=execution_id,
                        approval_request_id=approval_request_id,
                    )
                    payload = await AgentSurfaceMapper.from_execution_result(
                        result=resume_result,
                        capability_name=request.capability_name,
                        approval_service=approval_service,
                    )
                    return payload
                except Exception as exc:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Resume execution failed: {exc}",
                    ) from exc

        payload = await AgentSurfaceMapper.from_execution_result(
            result=result,
            capability_name=request.capability_name,
            approval_service=approval_service,
        )
        if payload.status == AgentExecutionStatus.PAUSED_FOR_APPROVAL:
            response.status_code = status.HTTP_202_ACCEPTED
        return payload

    @router.get("/capabilities/rank", response_model=list[RankedCapabilityView])
    async def rank_capabilities(
        query: str = Query(default=""),
        interaction_id: str | None = Query(default=None),
        session_id: str | None = Query(default=None),
        session_provider: str | None = Query(default=None),
        limit: int = Query(default=10, ge=1, le=100),
    ) -> list[RankedCapabilityView]:
        interaction = (
            await interaction_service.get_interaction(interaction_id)
            if isinstance(interaction_id, str) and interaction_id.strip()
            else None
        )
        session = (
            await session_service.get_session(session_id)
            if isinstance(session_id, str) and session_id.strip()
            else None
        )
        if (
            session is None
            and isinstance(session_provider, str)
            and session_provider.strip()
        ):
            session = {"provider_name": session_provider.strip()}
        ranked = await discovery_service.rank_capabilities(
            query=query,
            session=session,
            interaction=interaction,
            limit=limit,
        )
        return [RankedCapabilityView.model_validate(item) for item in ranked]

    @router.get("/sessions", response_model=list[SessionState])
    async def list_sessions() -> list[SessionState]:
        sessions = await session_service.list_sessions()
        return [public_session_state(item) for item in sessions]

    @router.post(
        "/sessions", response_model=SessionState, status_code=status.HTTP_201_CREATED
    )
    async def create_session(request: AgentSessionCreateRequest) -> SessionState:
        session = await session_service.create_session(
            provider_name=request.provider_name,
            auth_mode=request.auth_mode,
            cookies=request.cookies,
            headers=request.headers,
            tokens=request.tokens,
            csrf_tokens=request.csrf_tokens,
            auth_recipe=request.auth_recipe.model_dump(mode="json", exclude_none=True)
            if request.auth_recipe is not None
            else None,
            metadata=request.metadata,
            selected_context=request.selected_context,
            expires_at=request.expires_at,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            refreshable=request.refreshable,
        )
        return public_session_state(session)

    @router.get("/sessions/{session_id}", response_model=SessionState)
    async def get_session(session_id: str) -> SessionState:
        session = await session_service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return public_session_state(session)

    @router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def revoke_session(session_id: str) -> Response:
        session = await session_service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        await session_service.revoke_session(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/sessions/{session_id}/refresh", response_model=SessionState)
    async def refresh_session(session_id: str) -> SessionState:
        session = await session_service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            refreshed = await session_service.refresh_session(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return public_session_state(refreshed)

    @router.get("/interactions", response_model=list[AgentInteractionState])
    async def list_interactions() -> list[AgentInteractionState]:
        interactions = await interaction_service.list_interactions()
        return [AgentInteractionState.model_validate(item) for item in interactions]

    @router.get("/executions", response_model=list[ExecutionRecordView])
    async def list_execution_records(
        capability_name: str | None = Query(default=None),
        status: str | None = Query(default=None),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> list[ExecutionRecordView]:
        records = await execution_service.list_execution_records(
            capability_name=capability_name,
            status=status,
            limit=limit,
        )
        return [ExecutionRecordView.model_validate(record) for record in records]

    @router.get("/executions/{execution_id}", response_model=ExecutionRecordView)
    async def get_execution_record(execution_id: str) -> ExecutionRecordView:
        record = await execution_service.get_execution_record(execution_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Execution not found")
        return ExecutionRecordView.model_validate(record)

    @router.post(
        "/interactions",
        response_model=AgentInteractionState,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_interaction(
        request: AgentInteractionCreateRequest,
    ) -> AgentInteractionState:
        interaction = await interaction_service.create_interaction(
            session_id=request.session_id,
            selected_context=request.selected_context,
            resource_cache=request.resource_cache,
            pending_forms=request.pending_forms,
            pagination_state=request.pagination_state,
            upload_state=request.upload_state,
        )
        return AgentInteractionState.model_validate(interaction)

    @router.get("/interactions/{interaction_id}", response_model=AgentInteractionState)
    async def get_interaction(interaction_id: str) -> AgentInteractionState:
        interaction = await interaction_service.get_interaction(interaction_id)
        if interaction is None:
            raise HTTPException(status_code=404, detail="Interaction not found")
        return AgentInteractionState.model_validate(interaction)

    @router.patch(
        "/interactions/{interaction_id}", response_model=AgentInteractionState
    )
    async def update_interaction(
        interaction_id: str,
        request: AgentInteractionUpdateRequest,
    ) -> AgentInteractionState:
        try:
            interaction = await interaction_service.update_interaction(
                interaction_id,
                **request.model_dump(exclude_none=True),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return AgentInteractionState.model_validate(interaction)

    @router.delete(
        "/interactions/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    async def delete_interaction(interaction_id: str) -> Response:
        await interaction_service.delete_interaction(interaction_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post("/workflows", response_model=AgentWorkflowView)
    async def create_workflow(request: AgentWorkflowCreateRequest) -> AgentWorkflowView:
        workflow = await workflow_service.create_workflow(
            name=request.name,
            description=request.description,
            steps=request.steps,
        )
        return AgentWorkflowView(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            current_step_id=workflow.current_step.id if workflow.current_step else None,
            current_step_capability=workflow.current_step.capability_name
            if workflow.current_step
            else None,
            metadata=workflow.metadata,
        )

    @router.post(
        "/workflows/{workflow_id}/execute", response_model=AgentExecutionResponse
    )
    async def execute_workflow_step(
        workflow_id: str,
        request: AgentWorkflowExecuteRequest,
        response: Response,
    ) -> AgentExecutionResponse:
        result = await workflow_service.execute_step(
            workflow_id=workflow_id,
            arguments=request.arguments,
        )
        workflow = await workflow_service.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")

        approval_request = None
        approval_request_id = workflow.metadata.get("approval_request_id")
        if isinstance(approval_request_id, str) and approval_request_id.strip():
            approval_request = await approval_service.get_approval(approval_request_id)

        payload = AgentSurfaceMapper.from_step_result(
            workflow_id=workflow_id,
            capability_name=workflow.current_step.capability_name
            if workflow.current_step
            else None,
            step_id=result.step_id,
            step_result=result,
            approval_request=approval_request,
        )
        if payload.status == AgentExecutionStatus.PAUSED_FOR_APPROVAL:
            response.status_code = status.HTTP_202_ACCEPTED
        return payload

    @router.get("/approvals", response_model=list[ApprovalRequestView])
    async def list_approvals(
        status_filter: ApprovalStatus | None = Query(default=None),
    ) -> list[ApprovalRequestView]:
        approvals = await approval_service.list_approvals()
        if status_filter is not None:
            approvals = [
                item
                for item in approvals
                if str(item.get("status", "")).strip().lower() == status_filter.value
            ]
        return [
            item
            for item in (AgentSurfaceMapper.approval_view(a) for a in approvals)
            if item is not None
        ]

    @router.get("/approvals/{approval_id}", response_model=ApprovalRequestView)
    async def get_approval(approval_id: str) -> ApprovalRequestView:
        approval = await approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        view = AgentSurfaceMapper.approval_view(approval)
        if view is None:
            raise HTTPException(status_code=500, detail="Approval could not be mapped")
        return view

    @router.post(
        "/approvals/{approval_id}/decide", response_model=AgentExecutionResponse
    )
    async def decide_approval(
        approval_id: str,
        request: AgentApprovalDecisionRequest,
        response: Response,
    ) -> AgentExecutionResponse:
        approval = await approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found")

        await approval_service.decide(
            approval_id=approval_id,
            decision=request.decision.value,
            approver=request.approver_id,
            reason=request.reason,
            modified_arguments=request.modified_arguments,
        )

        updated = await approval_service.get_approval(approval_id)
        if updated is None:
            raise HTTPException(
                status_code=500, detail="Approval disappeared after decision"
            )

        workflow_id = updated.get("workflow_id")
        workflow_id_text = (
            workflow_id
            if isinstance(workflow_id, str) and workflow_id.strip()
            else None
        )

        if request.decision == ApprovalDecision.APPROVED and workflow_id_text:
            resumed = await workflow_service.resume_after_approval(
                workflow_id=workflow_id_text,
                approval_id=approval_id,
            )
            payload = AgentSurfaceMapper.from_step_result(
                workflow_id=workflow_id_text,
                capability_name=updated.get("capability_name"),
                step_id=resumed.step_id,
                step_result=resumed,
                approval_request=updated,
            )
            response.status_code = status.HTTP_200_OK
            return payload

        response.status_code = status.HTTP_202_ACCEPTED
        return AgentExecutionResponse(
            workflow_id=workflow_id_text,
            execution_id=optional_text(updated.get("execution_id")),
            capability_name=str(updated.get("capability_name") or "") or None,
            status=AgentExecutionStatus.REJECTED
            if request.decision == ApprovalDecision.REJECTED
            else AgentExecutionStatus.PAUSED_FOR_APPROVAL,
            approval_request=AgentSurfaceMapper.approval_view(updated),
            next=ContinuationHint(
                action="stop"
                if request.decision == ApprovalDecision.REJECTED
                else "await_resume",
                message="Approval rejected. Stop this action."
                if request.decision == ApprovalDecision.REJECTED
                else "Approval recorded and awaiting workflow resume.",
                approval_request_id=approval_id,
                workflow_id=workflow_id_text,
                execution_id=optional_text(updated.get("execution_id")),
            ),
        )

    # -----------------------------------------------------------------------
    # AI Plane endpoints
    # -----------------------------------------------------------------------

    async def _provider_capability_names() -> list[str]:
        """Pull all capability names from the registered provider."""
        doc = await discovery_service.discover()
        return [
            cap.get("name", "")
            for cap in doc.get("capabilities", [])
            if cap.get("name")
        ]

    @router.post("/plan", response_model=PlanResponse)
    async def plan_goal(request: PlanRequest) -> PlanResponse:
        """Generate a multi-step plan from a natural language goal."""
        if request.available_capabilities is not None:
            caps = request.available_capabilities
        else:
            caps = await _provider_capability_names()

        planner = AICPlanner()
        try:
            output = planner.plan(
                goal=request.goal,
                available_capabilities=caps,
                context=request.context,
            )
        except PlannerError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        return PlanResponse(
            plan_id=output.plan_id,
            goal=output.goal,
            generated_at=output.generated_at,
            steps=[
                PlanStepView(
                    step_id=s.step_id,
                    capability_name=s.capability_name,
                    depends_on=s.depends_on,
                    arguments=s.arguments,
                    rationale=s.rationale,
                )
                for s in output.steps
            ],
        )

    @router.post("/route", response_model=RouteResponse)
    async def route_utterance(request: RouteRequest) -> RouteResponse:
        """Route a natural language utterance to the appropriate destination."""
        if request.available_capabilities is not None:
            caps = request.available_capabilities
        else:
            doc = await discovery_service.discover()
            caps = [
                {
                    "name": cap.get("name", ""),
                    "description": cap.get("description", ""),
                    "kind": cap.get("kind", "action"),
                }
                for cap in doc.get("capabilities", [])
                if cap.get("name")
            ]

        router_ai = IntentRouter(capabilities=caps)
        decision = router_ai.route(request.utterance)

        return RouteResponse(
            destination=decision.destination.value,
            capability_name=decision.capability_name,
            confidence=decision.confidence,
            clarification_prompt=decision.clarification_prompt,
            rejection_reason=decision.rejection_reason,
        )

    @router.post("/judge", response_model=JudgeResponse)
    async def judge_plan(request: JudgeRequest) -> JudgeResponse:
        """Evaluate a plan dict and return a structured verdict."""
        raw = request.plan
        steps = [
            PlanStep(
                step_id=str(s.get("step_id", "")),
                capability_name=str(s.get("capability_name", "")),
                depends_on=list(s.get("depends_on") or []),
                arguments=dict(s.get("arguments") or {}),
                rationale=s.get("rationale"),
            )
            for s in (raw.get("steps") or [])
            if isinstance(s, dict)
        ]
        plan_obj = PlannerOutput(
            goal=str(raw.get("goal") or ""),
            steps=steps,
            plan_id=str(raw.get("plan_id") or f"plan_{id(raw)}"),
            generated_at=str(raw.get("generated_at") or ""),
        )

        judge = AICJudge()
        try:
            result = judge.evaluate(plan_obj)
        except JudgeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        return JudgeResponse(
            verdict=result.verdict.value,
            score=result.score,
            rationale=result.rationale,
            evaluated_at=result.evaluated_at,
        )

    return router


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def public_session_state(session: dict[str, Any]) -> SessionState:
    masked = dict(session)
    masked["tokens"] = {
        key: "***redacted***" for key in (session.get("tokens") or {}).keys()
    }
    masked["csrf_tokens"] = {
        key: "***redacted***" for key in (session.get("csrf_tokens") or {}).keys()
    }
    masked["cookies"] = [
        {**cookie, "value": "***redacted***"}
        for cookie in (session.get("cookies") or [])
        if isinstance(cookie, dict)
    ]
    headers = dict(session.get("headers") or {})
    for key in list(headers.keys()):
        if str(key).strip().lower() in {
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
        }:
            headers[key] = "***redacted***"
    masked["headers"] = headers
    return SessionState.model_validate(masked)
