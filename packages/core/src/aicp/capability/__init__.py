"""Capability model.

The core AICP capability definition with rich metadata for AI agents.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityKind(str, Enum):
    """The kind of capability."""

    QUERY = "query"  # Read-only, no side effects
    ACTION = "action"  # Write operation with side effects
    WORKFLOW = "workflow"  # Multi-step capability
    ASYNC_ACTION = "async_action"  # Long-running action
    BATCH_ACTION = "batch_action"  # Batch operation


class InputSchema(BaseModel):
    """Input schema for a capability."""

    type: str = "object"
    properties: dict[str, Any] = {}
    required: list[str] = []
    description: str | None = None


class OutputSchema(BaseModel):
    """Output schema for a capability."""

    type: str = "object"
    properties: dict[str, Any] = {}
    description: str | None = None


class RenderSpec(BaseModel):
    """Specification for rendering capability results."""

    format: str = "text"  # text, json, table, code, image
    fields: list[str] | None = None
    max_length: int | None = None
    truncate: bool = True
    syntax: str | None = None


class PolicyRef(BaseModel):
    """Reference to a policy for this capability."""

    policy_name: str
    parameters: dict[str, Any] = {}


class ContinuationSpec(BaseModel):
    """Specification for continuing after execution."""

    can_continue: bool = True
    next_capabilities: list[str] = []  # Suggested next capabilities
    next_hint: str | None = None


class Capability(BaseModel):
    """An AICP capability.

    This is the core unit of AICP - a meaningful action that can be
    discovered, executed, and governed with rich metadata.

    Attributes:
        name: Unique identifier (e.g., 'payments.transfer', 'orders.create')
        description: Human-readable description
        kind: Type of capability (query, action, workflow, etc.)
        input_schema: JSON Schema for inputs
        output_schema: JSON Schema for outputs
        tags: Categorization tags
        policy: Optional policy reference
        render: Hints for rendering results
        continuation: Hints for continuing after execution
    """

    name: str
    description: str = ""
    kind: CapabilityKind = CapabilityKind.ACTION

    input_schema: InputSchema = Field(default_factory=InputSchema)
    output_schema: OutputSchema = Field(default_factory=OutputSchema)

    tags: list[str] = Field(default_factory=list)

    # Policy reference
    policy: PolicyRef | None = None

    # Rendering hints
    render: RenderSpec | None = None

    # Continuation hints
    continuation: ContinuationSpec | None = None

    # Provider info
    provider_name: str | None = None
    provider_type: str | None = None

    # Metadata
    version: str | None = None
    deprecated: bool = False
    deprecation_message: str | None = None
