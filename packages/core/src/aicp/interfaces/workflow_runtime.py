"""Workflow runtime interface.

Defines the contract for executing multi-step workflows with state,
confirmation handling, and continuation semantics.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now_rfc3339() -> str:
    """Return the current UTC time in RFC3339 format."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_APPROVAL = "awaiting_approval"


class WorkflowStatus(str, Enum):
    """Overall workflow status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    PAUSED_FOR_APPROVAL = "paused_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Step(BaseModel):
    """A single step in a workflow."""

    id: str
    capability_name: str
    arguments: dict[str, Any]
    status: StepStatus = StepStatus.PENDING
    result: Any | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class WorkflowState(BaseModel):
    """State of a workflow execution."""

    id: str
    name: str
    description: str = ""
    steps: list[Step] = Field(default_factory=list)
    current_step_index: int = 0
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: str = Field(default_factory=utc_now_rfc3339)
    updated_at: str = Field(default_factory=utc_now_rfc3339)

    @property
    def current_step(self) -> Step | None:
        """Get the current step being executed."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return bool(self.steps) and all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps
        )

    @property
    def is_failed(self) -> bool:
        """Check if workflow has failed."""
        return any(s.status == StepStatus.FAILED for s in self.steps)

    def touch(self) -> None:
        """Refresh the workflow update timestamp."""
        self.updated_at = utc_now_rfc3339()


class StepResult(BaseModel):
    """Result of executing a workflow step."""

    success: bool
    result: Any | None = None
    error: str | None = None
    requires_confirmation: bool = False
    next: dict[str, Any] | None = None  # Agent guidance


class WorkflowError(Exception):
    """Raised when workflow execution fails."""

    pass


class WorkflowRuntime(ABC):
    """Abstract interface for workflow execution.

    Workflow runtimes manage multi-step task execution with:
    - State persistence across steps
    - Confirmation checkpoints
    - Error handling and recovery
    - Agent guidance (next actions)
    """

    @property
    @abstractmethod
    def runtime_type(self) -> str:
        """Type identifier for this runtime."""
        pass

    @abstractmethod
    async def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: list[dict[str, Any]] | None = None,
    ) -> WorkflowState:
        """Create a new workflow.

        Args:
            name: Workflow name.
            description: Optional description.
            steps: Optional initial steps.

        Returns:
            The created workflow state.
        """
        pass

    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Get a workflow by ID.

        Args:
            workflow_id: The workflow ID.

        Returns:
            The workflow state if found.
        """
        pass

    @abstractmethod
    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute the next step in a workflow.

        Args:
            workflow_id: The workflow to execute.
            arguments: Optional arguments to override/add.

        Returns:
            Result of the step execution.
        """
        pass

    @abstractmethod
    async def confirm_and_continue(
        self,
        workflow_id: str,
        confirmed: bool,
        modified_arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Continue after confirmation checkpoint.

        Args:
            workflow_id: The workflow to continue.
            confirmed: Whether user confirmed.
            modified_arguments: Optional modified arguments if user changed them.

        Returns:
            Result of continuing.
        """
        pass

    @abstractmethod
    async def skip_step(self, workflow_id: str) -> StepResult:
        """Skip the current step.

        Args:
            workflow_id: The workflow ID.

        Returns:
            Result of skipping.
        """
        pass

    @abstractmethod
    async def retry_step(self, workflow_id: str) -> StepResult:
        """Retry the current failed step.

        Args:
            workflow_id: The workflow ID.

        Returns:
            Result of retry.
        """
        pass

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            True if cancelled.
        """
        pass

    @abstractmethod
    async def list_workflows(self) -> list[WorkflowState]:
        """List all workflows.

        Returns:
            List of workflow states.
        """
        pass
