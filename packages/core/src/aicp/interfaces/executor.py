"""Executor interface.

Defines the contract for executing capabilities and normalizing results.
Executors handle the actual invocation and provide consistent output format.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ExecutionStatus(str, Enum):
    """Status of a capability execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


class ExecutionError(Exception):
    """Raised when capability execution fails."""

    pass


class ExecutionResult(BaseModel):
    """Normalized result of capability execution.

    This is AICP's key innovation over raw tool calling - every
    execution returns a structured result with metadata for the agent.
    """

    status: ExecutionStatus
    data: Any = None
    error: str | None = None
    error_code: str | None = None
    execution_time_ms: float | None = None

    # Agent guidance - this is the "agentic" part
    next: dict[str, Any] | None = None

    # Metadata for rendering
    rendered: str | None = None
    format_hint: str | None = None

    # Continuation hints
    can_continue: bool = True
    continuation_hint: str | None = None


class Executor(ABC):
    """Abstract interface for capability executors.

    Executors are responsible for:
    - Invoking capabilities with proper arguments
    - Normalizing results to ExecutionResult format
    - Handling errors consistently
    - Providing agent guidance (next actions)
    """

    @property
    @abstractmethod
    def executor_type(self) -> str:
        """Type identifier for this executor."""
        pass

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
        pass

    @abstractmethod
    async def execute_many(
        self,
        requests: list[dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Execute multiple capabilities.

        Default implementation executes sequentially.
        Executors can override for parallel execution.

        Args:
            requests: List of {capability_name, arguments, context}.

        Returns:
            List of ExecutionResults in same order as requests.
        """
        results = []
        for req in requests:
            result = await self.execute(
                req["capability_name"],
                req.get("arguments", {}),
                req.get("context"),
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

        Override this method to implement streaming execution.
        Default implementation returns a single chunk.

        Args:
            capability_name: Name of the capability to execute.
            arguments: Arguments for the capability.
            context: Optional execution context.

        Yields:
            Streaming chunks with data and metadata.
        """
        result = await self.execute(capability_name, arguments, context)
        yield {
            "type": "result",
            "status": result.status.value,
            "data": result.data,
            "error": result.error,
        }
