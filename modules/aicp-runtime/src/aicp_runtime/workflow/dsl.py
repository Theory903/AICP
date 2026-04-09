"""AICP YAML Workflow DSL parser.

Parses a human-authored YAML workflow definition into a ``WorkflowState``
that the existing ``DefaultWorkflowRuntime`` (and future extended runtimes)
can execute.

The YAML format is defined by ``spec/schemas/workflow-dsl.schema.json``.

Design notes
------------
* The parser is *pure* — it does not touch persistence or execution.
* Rich step-type metadata (parallel_steps, wait_for_event, branch_conditions,
  retry_policy, …) is stored in ``Step.metadata`` so that the existing
  ``WorkflowState`` / ``Step`` Pydantic models are not modified.
* The runtime can inspect ``step.metadata["type"]`` to dispatch to extended
  execution handlers added in Phase 2 (parallel executor, event waiter, etc.).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aicp.interfaces.workflow_runtime import Step, WorkflowState, WorkflowStatus

__all__ = [
    "DSLParseError",
    "DSLValidationError",
    "WorkflowDSLParser",
]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

_VALID_TOP_LEVEL = frozenset(
    {
        "name",
        "description",
        "version",
        "context",
        "metadata",
        "steps",
        "on_failure",
        "on_complete",
    }
)

_VALID_STEP_FIELDS = frozenset(
    {
        "id",
        "type",
        "name",
        "description",
        "capability_name",
        "arguments",
        "input_mapping",
        "output_mapping",
        "guard",
        "retry_policy",
        "approval_policy",
        "timeout_ms",
        "on_success",
        "on_failure",
        "on_timeout",
        "on_approved",
        "on_rejected",
        "compensation",
        "wait_for_event",
        "event_filter",
        "branch_conditions",
        "default_branch",
        "parallel_steps",
        "parallel_failure_policy",
        "loop_condition",
        "loop_body",
        "subflow_id",
        "subflow_input_mapping",
        "subflow_output_mapping",
        "transform_expression",
        "transform_target",
        "message",
        "assigned_to",
    }
)

_VALID_BACKOFF = frozenset({"none", "fixed", "exponential"})
_VALID_PARALLEL_FAILURE_POLICY = frozenset({"fail_fast", "wait_all"})
_VALID_STEP_TYPES = frozenset(
    {
        "capability",
        "approval",
        "wait_event",
        "branch",
        "parallel",
        "loop",
        "subflow",
        "terminal",
        "human_task",
        "transform",
    }
)

# Metadata keys to propagate from DSL step dict → Step.metadata
_METADATA_FIELDS = frozenset(
    {
        "type",
        "name",
        "description",
        "input_mapping",
        "output_mapping",
        "guard",
        "retry_policy",
        "approval_policy",
        "timeout_ms",
        "on_success",
        "on_failure",
        "on_timeout",
        "on_approved",
        "on_rejected",
        "compensation",
        "wait_for_event",
        "event_filter",
        "branch_conditions",
        "default_branch",
        "parallel_steps",
        "parallel_failure_policy",
        "loop_condition",
        "loop_body",
        "subflow_id",
        "subflow_input_mapping",
        "subflow_output_mapping",
        "transform_expression",
        "transform_target",
        "message",
        "assigned_to",
    }
)


class DSLParseError(Exception):
    """Raised when the YAML text cannot be parsed at all (syntax error,
    or top-level is not a mapping)."""


class DSLValidationError(Exception):
    """Raised when the parsed YAML structure violates the DSL schema."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class WorkflowDSLParser:
    """Parse AICP YAML workflow definitions into ``WorkflowState`` objects.

    Usage::

        parser = WorkflowDSLParser()
        workflow = parser.parse(yaml_text)
        workflow = parser.parse_file("path/to/flow.yaml")
        yaml_text = parser.to_yaml(workflow)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, yaml_text: str) -> WorkflowState:
        """Parse a YAML string into a :class:`WorkflowState`."""
        doc = self._load_yaml(yaml_text)
        self._validate_top_level(doc)
        return self._build_workflow(doc)

    def parse_file(self, path: str | Path) -> WorkflowState:
        """Parse a YAML file at *path* into a :class:`WorkflowState`."""
        text = Path(path).read_text(encoding="utf-8")
        return self.parse(text)

    def to_yaml(self, workflow: WorkflowState) -> str:
        """Serialise a :class:`WorkflowState` back to a DSL YAML string.

        Only fields expressible in the DSL are emitted.  Runtime-only fields
        (status, timestamps, step execution state) are omitted so the result
        can be round-tripped through ``parse``.
        """
        doc: dict[str, Any] = {"name": workflow.name}
        if workflow.description:
            doc["description"] = workflow.description
        if workflow.context:
            doc["context"] = dict(workflow.context)
        if workflow.metadata:
            doc["metadata"] = dict(workflow.metadata)

        steps_list: list[dict[str, Any]] = []
        for step in workflow.steps:
            step_dict: dict[str, Any] = {"id": step.id}
            if step.capability_name:
                step_dict["capability_name"] = step.capability_name
            if step.arguments:
                step_dict["arguments"] = dict(step.arguments)
            # Re-emit DSL metadata fields
            for field in sorted(_METADATA_FIELDS):
                value = step.metadata.get(field)
                if value is not None:
                    step_dict[field] = value
            steps_list.append(step_dict)

        doc["steps"] = steps_list
        return yaml.dump(doc, allow_unicode=True, sort_keys=False)

    # ------------------------------------------------------------------
    # Internal: YAML loading
    # ------------------------------------------------------------------

    def _load_yaml(self, yaml_text: str) -> dict[str, Any]:
        """Load YAML text, raising :class:`DSLParseError` on failure."""
        try:
            doc = yaml.safe_load(yaml_text)
        except yaml.YAMLError as exc:
            raise DSLParseError(f"YAML parse error: {exc}") from exc
        if not isinstance(doc, dict):
            raise DSLParseError(
                f"Workflow DSL must be a YAML mapping, got {type(doc).__name__}"
            )
        return doc  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Internal: validation
    # ------------------------------------------------------------------

    def _validate_top_level(self, doc: dict[str, Any]) -> None:
        """Validate top-level structure of the parsed document."""
        # Check for unknown top-level keys
        unknown = set(doc.keys()) - _VALID_TOP_LEVEL
        if unknown:
            key = sorted(unknown)[0]
            raise DSLValidationError(
                f"Unknown top-level field: '{key}'. "
                f"Valid fields: {sorted(_VALID_TOP_LEVEL)}"
            )

        # name required
        if "name" not in doc or not str(doc.get("name", "") or "").strip():
            raise DSLValidationError("Workflow DSL requires a non-empty 'name' field")

        # steps required and non-empty
        if "steps" not in doc:
            raise DSLValidationError("Workflow DSL requires a 'steps' field")
        steps = doc["steps"]
        if not isinstance(steps, list) or len(steps) == 0:
            raise DSLValidationError("Workflow 'steps' must be a non-empty list")

    def _validate_step(self, raw: Any, index: int) -> None:
        """Validate a single step dict."""
        if not isinstance(raw, dict):
            raise DSLValidationError(
                f"Step at index {index} must be a mapping, got {type(raw).__name__}"
            )

        # id required
        if "id" not in raw or not str(raw.get("id", "") or "").strip():
            raise DSLValidationError(
                f"Step at index {index} is missing required 'id' field"
            )

        step_type = raw.get("type", "capability")

        # type must be valid if provided
        if step_type not in _VALID_STEP_TYPES:
            raise DSLValidationError(
                f"Step '{raw.get('id')}': unknown type '{step_type}'. "
                f"Valid types: {sorted(_VALID_STEP_TYPES)}"
            )

        # type-specific requirements
        if step_type == "parallel" and not raw.get("parallel_steps"):
            raise DSLValidationError(
                f"Step '{raw.get('id')}' of type 'parallel' must define 'parallel_steps'"
            )
        if step_type == "wait_event" and not raw.get("wait_for_event"):
            raise DSLValidationError(
                f"Step '{raw.get('id')}' of type 'wait_event' must define 'wait_for_event'"
            )

        # retry_policy backoff validation
        rp = raw.get("retry_policy")
        if isinstance(rp, dict):
            backoff = rp.get("backoff", "none")
            if backoff not in _VALID_BACKOFF:
                raise DSLValidationError(
                    f"Step '{raw.get('id')}': retry_policy.backoff '{backoff}' is invalid. "
                    f"Valid values: {sorted(_VALID_BACKOFF)}"
                )

        # parallel_failure_policy validation
        pfp = raw.get("parallel_failure_policy")
        if pfp is not None and pfp not in _VALID_PARALLEL_FAILURE_POLICY:
            raise DSLValidationError(
                f"Step '{raw.get('id')}': parallel_failure_policy '{pfp}' is invalid. "
                f"Valid values: {sorted(_VALID_PARALLEL_FAILURE_POLICY)}"
            )

    # ------------------------------------------------------------------
    # Internal: building the WorkflowState
    # ------------------------------------------------------------------

    def _build_workflow(self, doc: dict[str, Any]) -> WorkflowState:
        """Construct a :class:`WorkflowState` from a validated doc."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        raw_steps = doc["steps"]

        # Validate steps individually and check for duplicates
        seen_ids: set[str] = set()
        for idx, raw_step in enumerate(raw_steps):
            self._validate_step(raw_step, idx)
            step_id = str(raw_step["id"])
            if step_id in seen_ids:
                raise DSLValidationError(f"duplicate step id: '{step_id}'")
            seen_ids.add(step_id)

        steps = [self._build_step(raw_step) for raw_step in raw_steps]

        context: dict[str, Any] = {}
        raw_context = doc.get("context")
        if isinstance(raw_context, dict):
            context.update(raw_context)

        metadata: dict[str, Any] = {}
        raw_metadata = doc.get("metadata")
        if isinstance(raw_metadata, dict):
            metadata.update(raw_metadata)
        # Store DSL-level globals in metadata for runtime access
        if "on_failure" in doc:
            metadata["dsl_on_failure"] = doc["on_failure"]
        if "on_complete" in doc:
            metadata["dsl_on_complete"] = doc["on_complete"]
        if "version" in doc:
            metadata["dsl_version"] = doc["version"]

        return WorkflowState(
            id=f"wf_{uuid.uuid4().hex[:12]}",
            name=str(doc["name"]).strip(),
            description=str(doc.get("description") or "").strip(),
            steps=steps,
            current_step_index=0,
            context=context,
            metadata=metadata,
            status=WorkflowStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

    def _build_step(self, raw: dict[str, Any]) -> Step:
        """Construct a :class:`Step` from a raw DSL step dict."""
        step_id = str(raw["id"]).strip()
        capability_name = str(raw.get("capability_name") or "").strip()
        arguments: dict[str, Any] = {}
        raw_args = raw.get("arguments")
        if isinstance(raw_args, dict):
            arguments = dict(raw_args)

        # Collect DSL metadata fields into Step.metadata
        metadata: dict[str, Any] = {}
        for field in _METADATA_FIELDS:
            value = raw.get(field)
            if value is not None:
                metadata[field] = value

        return Step(
            id=step_id,
            capability_name=capability_name,
            arguments=arguments,
            metadata=metadata,
        )
