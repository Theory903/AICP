"""Workflow runtime interface.

Defines the contract for executing multi-step workflows with state,
confirmation handling, approval checkpoints, and continuation semantics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now_rfc3339() -> str:
    """Return the current UTC time in RFC3339 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    """Overall workflow status.

    Values match the workflow.schema.json spec exactly.
    """

    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_EVENT = "waiting_event"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Step(BaseModel):
    """A single step in a workflow."""

    model_config = ConfigDict(extra="forbid")

    id: str
    capability_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Return True when the step has reached a terminal state."""
        return self.status in {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
        }

    @property
    def is_waiting(self) -> bool:
        """Return True when the step is waiting on external input."""
        return self.status in {
            StepStatus.AWAITING_CONFIRMATION,
            StepStatus.AWAITING_APPROVAL,
        }

    def mark_running(self) -> None:
        """Mark the step as running."""
        self.status = StepStatus.RUNNING
        if self.started_at is None:
            self.started_at = utc_now_rfc3339()

    def mark_completed(self, result: Any | None = None) -> None:
        """Mark the step as completed."""
        self.status = StepStatus.COMPLETED
        self.result = result
        self.error = None
        if self.started_at is None:
            self.started_at = utc_now_rfc3339()
        self.completed_at = utc_now_rfc3339()

    def mark_failed(self, error: str) -> None:
        """Mark the step as failed."""
        self.status = StepStatus.FAILED
        self.error = error
        if self.started_at is None:
            self.started_at = utc_now_rfc3339()
        self.completed_at = utc_now_rfc3339()

    def mark_skipped(self) -> None:
        """Mark the step as skipped."""
        self.status = StepStatus.SKIPPED
        self.error = None
        if self.started_at is None:
            self.started_at = utc_now_rfc3339()
        self.completed_at = utc_now_rfc3339()


class WorkflowState(BaseModel):
    """State of a workflow execution."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    steps: list[Step] = Field(default_factory=list)
    current_step_index: int = Field(default=0, ge=0)
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: str = Field(default_factory=utc_now_rfc3339)
    updated_at: str = Field(default_factory=utc_now_rfc3339)

    @property
    def current_step(self) -> Step | None:
        """Get the current step being executed."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def last_step(self) -> Step | None:
        """Get the last step in the workflow."""
        if not self.steps:
            return None
        return self.steps[-1]

    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return bool(self.steps) and all(
            step.status in {StepStatus.COMPLETED, StepStatus.SKIPPED}
            for step in self.steps
        )

    @property
    def is_failed(self) -> bool:
        """Check if workflow has failed."""
        return any(step.status == StepStatus.FAILED for step in self.steps)

    @property
    def is_waiting(self) -> bool:
        """Check if workflow is paused on confirmation or approval."""
        step = self.current_step
        return step is not None and step.is_waiting

    def touch(self) -> None:
        """Refresh the workflow update timestamp."""
        self.updated_at = utc_now_rfc3339()

    def advance(self) -> None:
        """Move to the next step index."""
        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
        self.touch()

    def sync_status(self) -> None:
        """Recompute workflow status from step states."""
        if self.status == WorkflowStatus.CANCELLED:
            return

        if not self.steps:
            self.status = WorkflowStatus.CREATED
            self.touch()
            return

        if self.is_complete:
            self.status = WorkflowStatus.COMPLETED
        elif self.is_failed:
            self.status = WorkflowStatus.FAILED
        else:
            current = self.current_step
            if current is None:
                self.status = WorkflowStatus.COMPLETED
            elif current.status == StepStatus.AWAITING_APPROVAL:
                self.status = WorkflowStatus.WAITING_APPROVAL
            elif current.status == StepStatus.AWAITING_CONFIRMATION:
                self.status = WorkflowStatus.PAUSED
            elif current.status == StepStatus.RUNNING:
                self.status = WorkflowStatus.RUNNING
            else:
                self.status = WorkflowStatus.CREATED

        self.touch()


class StepResult(BaseModel):
    """Result of executing or changing a workflow step."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    result: Any | None = None
    error: str | None = None
    requires_confirmation: bool = False
    requires_approval: bool = False
    next: dict[str, Any] | None = None
    step_id: str | None = None
    workflow_status: WorkflowStatus | None = None

    @classmethod
    def ok(
        cls,
        result: Any | None = None,
        *,
        next: dict[str, Any] | None = None,
        step_id: str | None = None,
        workflow_status: WorkflowStatus | None = None,
    ) -> "StepResult":
        """Build a successful step result."""
        return cls(
            success=True,
            result=result,
            next=next,
            step_id=step_id,
            workflow_status=workflow_status,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        *,
        next: dict[str, Any] | None = None,
        requires_confirmation: bool = False,
        requires_approval: bool = False,
        step_id: str | None = None,
        workflow_status: WorkflowStatus | None = None,
    ) -> "StepResult":
        """Build a failed or blocked step result."""
        return cls(
            success=False,
            error=error,
            next=next,
            requires_confirmation=requires_confirmation,
            requires_approval=requires_approval,
            step_id=step_id,
            workflow_status=workflow_status,
        )


class WorkflowError(Exception):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        message: str,
        workflow_id: str | None = None,
        step_id: str | None = None,
        details: Any = None,
    ):
        self.workflow_id = workflow_id
        self.step_id = step_id
        self.details = details
        super().__init__(message)


class WorkflowRuntime(ABC):
    """Abstract interface for workflow execution.

    Workflow runtimes manage multi-step task execution with:
    - state persistence across steps
    - confirmation checkpoints
    - approval checkpoints
    - error handling and recovery
    - agent guidance for next actions
    """

    @property
    @abstractmethod
    def runtime_type(self) -> str:
        """Type identifier for this runtime."""
        raise NotImplementedError

    @abstractmethod
    async def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: list[dict[str, Any]] | None = None,
    ) -> WorkflowState:
        """Create a new workflow."""
        raise NotImplementedError

    @abstractmethod
    async def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        """Get a workflow by ID."""
        raise NotImplementedError

    @abstractmethod
    async def execute_step(
        self,
        workflow_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute the next step in a workflow."""
        raise NotImplementedError

    @abstractmethod
    async def confirm_and_continue(
        self,
        workflow_id: str,
        confirmed: bool,
        modified_arguments: dict[str, Any] | None = None,
    ) -> StepResult:
        """Continue after a confirmation checkpoint."""
        raise NotImplementedError

    @abstractmethod
    async def skip_step(self, workflow_id: str) -> StepResult:
        """Skip the current step."""
        raise NotImplementedError

    @abstractmethod
    async def retry_step(self, workflow_id: str) -> StepResult:
        """Retry the current failed step."""
        raise NotImplementedError

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        raise NotImplementedError

    @abstractmethod
    async def list_workflows(self) -> list[WorkflowState]:
        """List all workflows."""
        raise NotImplementedError