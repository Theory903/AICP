"""Workflow routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from aicp_runtime.services.workflows import WorkflowService


class CreateWorkflowRequest(BaseModel):
    """Workflow creation payload."""

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

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("steps", mode="before")
    @classmethod
    def _validate_steps(cls, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("steps must be a list")
        for step in value:
            if not isinstance(step, dict):
                raise ValueError("each step must be an object")
        return value


class ExecuteWorkflowStepRequest(BaseModel):
    """Workflow step execution payload."""

    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def _normalize_arguments(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("arguments must be an object")
        return value


class ResumeWorkflowRequest(BaseModel):
    """Workflow resume payload."""

    approval_id: str = Field(min_length=1)

    @field_validator("approval_id", mode="before")
    @classmethod
    def _normalize_approval_id(cls, value: Any) -> str:
        approval_id = str(value or "").strip()
        if not approval_id:
            raise ValueError("approval_id cannot be empty")
        return approval_id


class WorkflowCompensationView(BaseModel):
    """Compensation metadata associated with a workflow step or event."""

    rollback_capability: str | None = None
    available: bool = False


class WorkflowStepView(BaseModel):
    """Enriched workflow step view."""

    id: str
    capability_name: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    approval_request_id: str | None = None
    approval_status: str | None = None
    compensation: WorkflowCompensationView = Field(
        default_factory=WorkflowCompensationView
    )


class WorkflowExecutionView(BaseModel):
    """Workflow detail view with enriched step data."""

    id: str
    name: str
    description: str = ""
    status: str
    current_step_id: str | None = None
    current_step_capability: str | None = None
    current_step_index: int
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepView] = Field(default_factory=list)


class WorkflowTimelineEventView(BaseModel):
    """Workflow timeline event."""

    id: str | None = None
    timestamp: str | None = None
    event_type: str
    title: str
    actor: str | None = None
    status: str | None = None
    workflow_id: str | None = None
    step_id: str | None = None
    capability_name: str | None = None
    approval_request_id: str | None = None
    approval_status: str | None = None
    compensation: WorkflowCompensationView = Field(
        default_factory=WorkflowCompensationView
    )
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDetailResponse(BaseModel):
    """Workflow detail payload."""

    workflow: WorkflowExecutionView
    timeline: list[WorkflowTimelineEventView] = Field(default_factory=list)


class WorkflowTimelineResponse(BaseModel):
    """Workflow timeline payload."""

    workflow_id: str
    workflow_status: str
    current_step_id: str | None = None
    current_step_capability: str | None = None
    events: list[WorkflowTimelineEventView] = Field(default_factory=list)


def _dump_model(value: Any) -> Any:
    """Serialize Pydantic-ish values consistently."""
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json", exclude_none=True)
    return value


def build_workflows_router(workflow_service: WorkflowService) -> APIRouter:
    """Build the workflows API router."""
    router = APIRouter(tags=["workflows"])

    @router.get("/workflows")
    async def list_workflows() -> list[dict[str, Any]]:
        """List all workflows."""
        workflows = await workflow_service.list_workflows()
        return [_dump_model(workflow) for workflow in workflows]

    @router.post("/workflows")
    async def create_workflow(request: CreateWorkflowRequest) -> dict[str, Any]:
        """Create a new workflow."""
        workflow = await workflow_service.create_workflow(
            name=request.name,
            description=request.description,
            steps=request.steps,
        )
        return _dump_model(workflow)

    @router.get("/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str) -> dict[str, Any]:
        """Get a workflow by ID."""
        workflow = await workflow_service.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )
        return _dump_model(workflow)

    @router.get(
        "/workflows/{workflow_id}/detail",
        response_model=WorkflowDetailResponse,
    )
    async def get_workflow_detail(workflow_id: str) -> dict[str, Any]:
        """Get an enriched workflow detail view."""
        workflow_detail = await workflow_service.get_workflow_detail(workflow_id)
        if workflow_detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )
        return workflow_detail

    @router.get(
        "/workflows/{workflow_id}/timeline",
        response_model=WorkflowTimelineResponse,
    )
    async def get_workflow_timeline(workflow_id: str) -> dict[str, Any]:
        """Get workflow timeline events."""
        timeline = await workflow_service.get_workflow_timeline(workflow_id)
        if timeline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )
        return timeline

    @router.post("/workflows/{workflow_id}/execute")
    async def execute_workflow_step(
        workflow_id: str,
        request: ExecuteWorkflowStepRequest,
    ) -> dict[str, Any]:
        """Execute the next step of a workflow."""
        try:
            result = await workflow_service.execute_step(
                workflow_id=workflow_id,
                arguments=request.arguments,
            )
        except ValueError as exc:
            message = str(exc)
            lowered = message.lower()

            if "not found" in lowered:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            ) from exc
        except Exception as exc:
            message = str(exc)
            if "not found" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow execution failed: {message}",
            ) from exc

        return _dump_model(result)

    @router.post("/workflows/{workflow_id}/resume")
    async def resume_workflow(
        workflow_id: str,
        request: ResumeWorkflowRequest,
    ) -> dict[str, Any]:
        """Resume a workflow after approval."""
        try:
            result = await workflow_service.resume_after_approval(
                workflow_id=workflow_id,
                approval_id=request.approval_id,
            )
        except ValueError as exc:
            message = str(exc)
            lowered = message.lower()

            if "not found" in lowered:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            ) from exc
        except Exception as exc:
            message = str(exc)
            if "not found" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow resume failed: {message}",
            ) from exc

        return _dump_model(result)

    return router
