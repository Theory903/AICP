"""Tool specification - typed, discoverable, AI-friendly tool definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolKind(Enum):
    """Kind of tool - maps to capability kind."""

    QUERY = "query"
    ACTION = "action"
    WORKFLOW = "workflow"
    ASYNC_ACTION = "async_action"
    BATCH_ACTION = "batch_action"


class SideEffectClass(Enum):
    """Side effect classification for AI awareness."""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    EXTERNAL_API = "external_api"
    STATE_CHANGE = "state_change"


class DeterminismClass(Enum):
    """Output predictability class."""

    DETERMINISTIC = "deterministic"
    BOUNDED_NONDETERMINISTIC = "bounded_nondeterministic"
    OBSERVATIONAL = "observational"
    HEURISTIC = "heuristic"


class RiskLevel(Enum):
    """Risk level for permission system."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolArgument:
    """A single argument for a tool."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None
    pattern: str | None = None


@dataclass
class ToolSpec:
    """Complete specification for an AICP tool."""

    name: str
    description: str
    kind: ToolKind
    category: str

    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    side_effect: SideEffectClass = SideEffectClass.NONE
    determinism: DeterminismClass = DeterminismClass.DETERMINISTIC

    requires_approval: bool = False
    requires_session: bool = False
    idempotency_key: str | None = None

    risk_level: RiskLevel = RiskLevel.NONE

    tags: list[str] = field(default_factory=list)
    often_follows: list[str] = field(default_factory=list)
    often_before: list[str] = field(default_factory=list)

    policy_name: str | None = None
    provider_name: str | None = None

    render_format: str = "text"
    next_capabilities: list[str] = field(default_factory=list)

    version: str = "1.0.0"
    deprecated: bool = False

    permission_pattern: str | None = None
    permission_description: str | None = None

    def to_ai_readable(self) -> dict[str, Any]:
        """Convert to AI-friendly format."""
        return {
            "tool_name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "side_effect": self.side_effect.value,
            "determinism": self.determinism.value,
            "approval_required": self.requires_approval,
            "risk": self.risk_level.value,
            "input": self._format_schema(self.input_schema),
            "output": self._format_schema(self.output_schema),
            "next_actions": self.next_capabilities,
            "tags": self.tags,
        }

    def _format_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Format schema for AI readability."""
        if not schema:
            return {"type": "object", "properties": {}}

        result = {"type": schema.get("type", "object"), "properties": {}}
        props = schema.get("properties", {})
        for name, prop in props.items():
            result["properties"][name] = {
                "type": prop.get("type", "any"),
                "description": prop.get("description", ""),
                "required": name in schema.get("required", []),
            }
        return result

    def get_permission_pattern(self) -> str:
        """Get permission pattern for this tool."""
        if self.permission_pattern:
            return self.permission_pattern

        prefix = self.category.split(".")[0] if "." in self.category else self.category
        return f"{prefix}({self.name})"

    def to_capability_dict(self) -> dict[str, Any]:
        """Convert to capability dictionary for AICP."""
        return {
            "name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "determinism_class": self.determinism.value,
            "idempotency_key": self.idempotency_key,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "tags": self.tags,
            "often_follows": self.often_follows,
            "policy": {"policy_name": self.policy_name} if self.policy_name else None,
            "render": {"format": self.render_format},
            "continuation": {
                "can_continue": bool(self.next_capabilities),
                "next_capabilities": self.next_capabilities,
            },
        }


@dataclass
class ToolResultEnvelope:
    """Uniform execution envelope for all tool results."""

    ok: bool
    tool_name: str
    status: str

    result: Any = None
    summary: str = ""
    error: str | None = None

    execution_id: str | None = None
    correlation_id: str | None = None

    allowed_next_actions: list[dict[str, Any]] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)

    risk: str = "none"

    execution_time_ms: int = 0
    timestamp: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ok": self.ok,
            "tool": self.tool_name,
            "status": self.status,
            "summary": self.summary,
            "result": self.result,
            "error": self.error,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "next": {
                "actions": self.allowed_next_actions,
                "hints": self.hints,
            },
            "risk": self.risk,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_execution(
        cls,
        tool_spec: ToolSpec,
        ok: bool,
        result: Any,
        error: str | None = None,
    ) -> ToolResultEnvelope:
        """Create envelope from execution result."""
        import uuid
        from datetime import datetime

        return cls(
            ok=ok,
            tool_name=tool_spec.name,
            status="completed" if ok else "failed",
            result=result,
            summary=f"{tool_spec.name} {'succeeded' if ok else 'failed'}",
            error=error,
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            correlation_id=f"corr_{uuid.uuid4().hex[:12]}",
            allowed_next_actions=[
                {"name": next_cap, "requires_approval": False}
                for next_cap in tool_spec.next_capabilities
            ],
            risk=tool_spec.risk_level.value,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )