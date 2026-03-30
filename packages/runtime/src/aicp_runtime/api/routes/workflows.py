"""Workflow routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aicp_runtime.services.workflows import WorkflowService


class CreateWorkflowRequest(BaseModel):
    """Workflow creation payload."""

    name: str
    description: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)


class ExecuteWorkflowStepRequest(BaseModel):
    """Workflow step execution payload."""

    arguments: dict[str, Any] = Field(default_factory=dict)


class ResumeWorkflowRequest(BaseModel):
    """Workflow resume payload."""

    approval_id: str


def build_workflows_router(workflow_service: WorkflowService) -> APIRouter:
    router = APIRouter()

    @router.get("/workflows")
    async def list_workflows():
        workflows = await workflow_service.list_workflows()
        return [workflow.model_dump(mode="json") for workflow in workflows]

    @router.post("/workflows")
    async def create_workflow(request: CreateWorkflowRequest):
        workflow = await workflow_service.create_workflow(
            name=request.name,
            description=request.description,
            steps=request.steps,
        )
        return workflow.model_dump(mode="json")

    @router.get("/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str):
        workflow = await workflow_service.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow.model_dump(mode="json")

    @router.post("/workflows/{workflow_id}/execute")
    async def execute_workflow_step(workflow_id: str, request: ExecuteWorkflowStepRequest):
        try:
            result = await workflow_service.execute_step(workflow_id, request.arguments)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return result.model_dump(mode="json")

    @router.post("/workflows/{workflow_id}/resume")
    async def resume_workflow(workflow_id: str, request: ResumeWorkflowRequest):
        try:
            result = await workflow_service.resume_after_approval(
                workflow_id,
                approval_id=request.approval_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return result.model_dump(mode="json")

    return router
