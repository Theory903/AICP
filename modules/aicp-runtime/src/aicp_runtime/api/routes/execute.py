"""Execution routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from aicp_runtime.services.execution import ExecutionService


class ExecuteRequest(BaseModel):
    """Execution request payload."""

    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", "context", mode="before")
    @classmethod
    def _normalize_mapping(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("must be an object")
        return value


def build_execution_router(execution_service: ExecutionService) -> APIRouter:
    """Build the execution API router."""
    router = APIRouter(tags=["execution"])

    @router.post("/execute/{capability_name}")
    async def execute_capability(
        capability_name: str,
        request: ExecuteRequest,
    ) -> dict[str, Any]:
        """Execute a capability and return a normalized execution result."""
        try:
            result = await execution_service.execute(
                capability_name=capability_name,
                arguments=request.arguments,
                context=request.context,
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Execution failed: {exc}",
            ) from exc

        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json", exclude_none=True)

        if isinstance(result, dict):
            return result

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Execution service returned an unsupported result type",
        )

    return router
