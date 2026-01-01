"""AICP Validator.

Validates AICP resources against JSON schemas.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from aicp.capability import Capability
from aicp.interfaces.policy_engine import Policy
from aicp.interfaces.workflow_runtime import WorkflowState


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None, details: Any = None):
        super().__init__(message)
        self.field = field
        self.details = details


class AicpValidator:
    """Validates AICP resources against JSON schemas."""

    def __init__(self, schema_dir: Path | None = None):
        if schema_dir is None:
            schema_dir = Path(__file__).parent.parent.parent.parent / "spec" / "schemas"
        self._schema_dir = schema_dir
        self._schemas: dict[str, dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all JSON schemas."""
        if not self._schema_dir.exists():
            return
        for schema_file in self._schema_dir.glob("*.schema.json"):
            with open(schema_file) as f:
                schema = json.load(f)
                name = schema_file.stem.replace(".schema", "")
                self._schemas[name] = schema

    def _get_schema(self, name: str) -> dict[str, Any]:
        """Get a schema by name."""
        if name not in self._schemas:
            raise ValidationError(f"Unknown schema: {name}")
        return self._schemas[name]

    def validate_capability(self, data: dict[str, Any]) -> Capability:
        """Validate and parse capability data."""
        schema = self._get_schema("capability")
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(
                f"Invalid capability: {e.message}",
                field=str(e.json_path) if hasattr(e, "json_path") else None,
            )
        return Capability(**data)

    def validate_policy(self, data: dict[str, Any]) -> Policy:
        """Validate and parse policy data."""
        from aicp.interfaces.policy_engine import Policy as PolicyModel

        schema = self._get_schema("policy")
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(
                f"Invalid policy: {e.message}",
                field=str(e.json_path) if hasattr(e, "json_path") else None,
            )
        return PolicyModel(**data)

    def validate_workflow(self, data: dict[str, Any]) -> WorkflowState:
        """Validate and parse workflow data."""
        schema = self._get_schema("workflow")
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(
                f"Invalid workflow: {e.message}",
                field=str(e.json_path) if hasattr(e, "json_path") else None,
            )
        return WorkflowState(**data)

    def validate_execution_result(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate execution result data."""
        schema = self._get_schema("execution-result")
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(
                f"Invalid execution result: {e.message}",
                field=str(e.json_path) if hasattr(e, "json_path") else None,
            )
        return data

    def validate_error(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate error data."""
        schema = self._get_schema("error")
        try:
            jsonschema.validate(data, schema)
        except JsonSchemaValidationError as e:
            raise ValidationError(
                f"Invalid error: {e.message}",
                field=str(e.json_path) if hasattr(e, "json_path") else None,
            )
        return data

    def get_schema(self, name: str) -> dict[str, Any] | None:
        """Get a schema by name."""
        return self._schemas.get(name)
