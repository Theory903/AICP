"""Execution routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aicp_runtime.services.execution import ExecutionService


class ExecuteRequest(BaseModel):
    """Execution request payload."""

    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


def build_execute_router(execution_service: ExecutionService) -> APIRouter:
    router = APIRouter()

    @router.post("/execute/{capability_name}")
    async def execute(capability_name: str, request: ExecuteRequest):
        result = await execution_service.execute(
            capability_name,
            request.arguments,
            request.context,
        )
        return result.model_dump(mode="json")

    return router
