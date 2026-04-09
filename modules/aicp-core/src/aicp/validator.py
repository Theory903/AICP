"""AICP Validator.

Validates AICP resources against JSON schemas and parses them into models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from aicp.capability import Capability
from aicp.interfaces.policy_engine import Policy
from aicp.interfaces.workflow_runtime import WorkflowState


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: Any = None,
        schema_name: str | None = None,
    ):
        super().__init__(message)
        self.field = field
        self.details = details
        self.schema_name = schema_name


class AicpValidator:
    """Validates AICP resources against JSON schemas."""

    def __init__(self, schema_dir: Path | None = None):
        self._schema_dir = schema_dir or self._default_schema_dir()
        self._schemas: dict[str, dict[str, Any]] = {}
        self._validators: dict[str, Draft202012Validator] = {}
        self._load_schemas()

    @staticmethod
    def _default_schema_dir() -> Path:
        """Resolve the default schema directory."""
        return Path(__file__).resolve().parents[2] / "spec" / "schemas"

    def _load_schemas(self) -> None:
        """Load all JSON schemas from the schema directory."""
        if not self._schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self._schema_dir}")

        schema_files = sorted(self._schema_dir.glob("*.schema.json"))
        if not schema_files:
            raise FileNotFoundError(f"No schema files found in: {self._schema_dir}")

        for schema_file in schema_files:
            with schema_file.open(encoding="utf-8") as handle:
                schema = json.load(handle)

            schema_name = schema_file.name.removesuffix(".schema.json")
            Draft202012Validator.check_schema(schema)

            self._schemas[schema_name] = schema
            self._validators[schema_name] = Draft202012Validator(schema)

    def _get_schema(self, name: str) -> dict[str, Any]:
        """Get a schema by name."""
        schema = self._schemas.get(name)
        if schema is None:
            raise ValidationError(
                f"Unknown schema: {name}",
                schema_name=name,
            )
        return schema

    def _get_validator(self, name: str) -> Draft202012Validator:
        """Get a compiled validator by schema name."""
        validator = self._validators.get(name)
        if validator is None:
            raise ValidationError(
                f"Unknown schema: {name}",
                schema_name=name,
            )
        return validator

    @staticmethod
    def _format_error_path(error: JsonSchemaValidationError) -> str | None:
        """Format jsonschema error path into a readable dotted path."""
        if not error.absolute_path:
            return None
        return ".".join(str(part) for part in error.absolute_path)

    def _raise_validation_error(
        self,
        schema_name: str,
        error: JsonSchemaValidationError,
    ) -> None:
        """Convert jsonschema errors into AICP validation errors."""
        raise ValidationError(
            message=f"Invalid {schema_name}: {error.message}",
            field=self._format_error_path(error),
            details={
                "validator": error.validator,
                "validator_value": error.validator_value,
                "instance": error.instance,
                "schema_path": list(error.absolute_schema_path),
            },
            schema_name=schema_name,
        ) from error

    def _validate_data(self, schema_name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Validate raw data against a named schema."""
        validator = self._get_validator(schema_name)
        errors = sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))

        if errors:
            self._raise_validation_error(schema_name, errors[0])

        return data

    def validate_capability(self, data: dict[str, Any]) -> Capability:
        """Validate and parse capability data."""
        validated = self._validate_data("capability", data)
        return Capability.model_validate(validated)

    def validate_policy(self, data: dict[str, Any]) -> Policy:
        """Validate and parse policy data."""
        validated = self._validate_data("policy", data)
        return Policy.model_validate(validated)

    def validate_workflow(self, data: dict[str, Any]) -> WorkflowState:
        """Validate and parse workflow data."""
        validated = self._validate_data("workflow", data)
        return WorkflowState.model_validate(validated)

    def validate_execution_result(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate execution result data."""
        return self._validate_data("execution-result", data)

    def validate_error(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate error data."""
        return self._validate_data("error", data)

    def get_schema(self, name: str) -> dict[str, Any] | None:
        """Get a schema by name."""
        return self._schemas.get(name)

    def list_schemas(self) -> list[str]:
        """List all loaded schema names."""
        return sorted(self._schemas.keys())
