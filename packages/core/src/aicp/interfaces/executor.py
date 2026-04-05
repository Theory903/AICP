"""Executor interface.

Defines the contract for executing capabilities and normalizing results.
Executors handle invocation and provide a consistent output format.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(str, Enum):
    """Status of a capability execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


class ExecutionError(Exception):
    """Raised when capability execution fails."""

    def __init__(
        self,
        message: str,
        capability_name: str | None = None,
        error_code: str | None = None,
        details: Any = None,
    ):
        self.capability_name = capability_name
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class ExecutionResult(BaseModel):
    """Normalized result of capability execution.

    This is AICP's execution contract. Every execution returns:
    - normalized outcome state
    - optional structured payload
    - machine-usable next guidance
    - rendering hints
    - continuation / approval metadata
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: ExecutionStatus
    data: Any = None
    error: str | None = None
    error_code: str | None = None
    warnings: list[dict[str, Any]] | None = None
    execution_time_ms: float | None = Field(default=None, ge=0)

    # Agent guidance
    next: dict[str, Any] | None = None
    allowed_next_actions: list[dict[str, Any]] = Field(default_factory=list)

    # Rendering metadata
    rendered: str | None = None
    format_hint: str | None = None

    # Continuation hints
    can_continue: bool = True
    continuation_hint: str | None = None

    # Approval (HITL)
    approval_request_id: str | None = None
    approval_status: str | None = None

    @property
    def is_success(self) -> bool:
        """Return True when execution succeeded."""
        return self.status == ExecutionStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Return True when execution did not succeed."""
        return self.status != ExecutionStatus.SUCCESS

    @classmethod
    def success(
        cls,
        data: Any = None,
        *,
        execution_time_ms: float | None = None,
        next: dict[str, Any] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        rendered: str | None = None,
        format_hint: str | None = None,
        can_continue: bool = True,
        continuation_hint: str | None = None,
        allowed_next_actions: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """Build a success result."""
        return cls(
            status=ExecutionStatus.SUCCESS,
            data=data,
            execution_time_ms=execution_time_ms,
            next=next,
            warnings=warnings,
            rendered=rendered,
            format_hint=format_hint,
            can_continue=can_continue,
            continuation_hint=continuation_hint,
            allowed_next_actions=list(allowed_next_actions or []),
        )

    @classmethod
    def failure(
        cls,
        *,
        error: str,
        error_code: str | None = None,
        execution_time_ms: float | None = None,
        next: dict[str, Any] | None = None,
        can_continue: bool = True,
        continuation_hint: str | None = None,
        approval_request_id: str | None = None,
        approval_status: str | None = None,
        status: ExecutionStatus = ExecutionStatus.FAILURE,
        allowed_next_actions: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """Build a failure-like result."""
        return cls(
            status=status,
            error=error,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            next=next,
            can_continue=can_continue,
            continuation_hint=continuation_hint,
            approval_request_id=approval_request_id,
            approval_status=approval_status,
            allowed_next_actions=list(allowed_next_actions or []),
        )


class Executor(ABC):
    """Abstract interface for capability executors.

    Executors are responsible for:
    - invoking capabilities with proper arguments
    - normalizing results to ExecutionResult
    - handling errors consistently
    - providing next-action guidance for agents
    """

    @property
    @abstractmethod
    def executor_type(self) -> str:
        """Type identifier for this executor."""
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a capability.

        Args:
            capability_name: Name of the capability to execute.
            arguments: Arguments for the capability.
            context: Optional execution context.

        Returns:
            Normalized ExecutionResult.
        """
        raise NotImplementedError

    async def execute_many(
        self,
        requests: list[dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Execute multiple capabilities sequentially.

        Executors may override this for batching or parallel execution.
        """
        results: list[ExecutionResult] = []
        for request in requests:
            result = await self.execute(
                request["capability_name"],
                request.get("arguments", {}),
                request.get("context"),
            )
            results.append(result)
        return results

    async def execute_streaming(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a capability with streaming results.

        Override this method to implement real streaming.
        Default implementation emits a simple start/result/end sequence.
        """
        yield {"type": "start", "capability": capability_name}

        result = await self.execute(capability_name, arguments, context)

        yield {
            "type": "result",
            "status": result.status.value,
            "data": result.data,
            "error": result.error,
            "error_code": result.error_code,
            "metadata": result.model_dump(exclude_none=True),
        }

        yield {"type": "end", "capability": capability_name}
