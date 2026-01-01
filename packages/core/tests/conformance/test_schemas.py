"""Schema conformance tests for AICP.

These tests verify that AICP models conform to their JSON schema definitions.
"""

import json
from pathlib import Path

import pytest
import referencing
from jsonschema import Draft202012Validator
from referencing.jsonschema import SchemaRegistry

from aicp import (
    Capability,
    CapabilityKind,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicySubject,
)
from aicp.interfaces import ExecutionResult, ExecutionStatus

SCHEMAS_DIR = Path(__file__).parent.parent.parent.parent.parent / "spec" / "schemas"


def _create_registry() -> SchemaRegistry:
    """Create a schema registry with all local schemas loaded."""
    registry: SchemaRegistry = SchemaRegistry()

    for schema_file in SCHEMAS_DIR.glob("*.json"):
        with open(schema_file) as f:
            schema = json.load(f)

        # Create a URI for this schema
        base_name = schema_file.stem.replace(".schema", "")
        schema_id = f"https://aicp.dev/schemas/{base_name}"

        # Remove $id to prevent resolution issues
        schema_copy = dict(schema)
        schema_copy.pop("$id", None)

        try:
            # Add as absolute URI
            registry = registry.with_resource(schema_id, referencing.Resource.from_contents(schema_copy))
            # Also add as relative filename (as used in $ref)
            registry = registry.with_resource(schema_file.name, referencing.Resource.from_contents(schema_copy))
        except Exception:
            pass  # Skip schemas that can't be loaded

    return registry


def load_schema(schema_name: str) -> dict:
    """Load a JSON schema by name."""
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.exists():
        pytest.skip(f"Schema not found: {schema_path}")
    with open(schema_path) as f:
        return json.load(f)


def validate_against_schema(schema_name: str, data: dict) -> tuple[bool, list[str]]:
    """Check if data conforms to schema. Returns (is_valid, error_messages)."""
    schema = load_schema(schema_name)

    # Remove $id to prevent remote resolution
    if "$id" in schema:
        del schema["$id"]

    registry = _create_registry()
    validator = Draft202012Validator(schema, registry=registry)
    errors = list(validator.iter_errors(data))
    if errors:
        return False, [f"{e.json_path}: {e.message}" for e in errors]
    return True, []


class TestCapabilitySchemaConformance:
    """Test Capability model conformance to JSON schema."""

    def test_valid_capability_conforms(self):
        """Test that a valid capability conforms to the schema."""
        capability = Capability(
            name="test.action",
            description="A test action",
            kind=CapabilityKind.ACTION,
        )
        data = capability.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("capability.schema.json", data)
        assert valid, f"Capability does not conform: {errors}"

    def test_capability_with_render_and_continuation(self):
        """Test capability with render and continuation hints."""
        capability = Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
            render={"format": "text"},
            continuation={"can_continue": True, "next_capabilities": ["payments.receipt"]},
        )
        data = capability.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("capability.schema.json", data)
        assert valid, f"Capability does not conform: {errors}"

    def test_capability_with_policy_ref(self):
        """Test capability with policy reference."""
        capability = Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
            policy={"policy_name": "high_value_confirmation", "parameters": {}},
        )
        data = capability.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("capability.schema.json", data)
        assert valid, f"Capability does not conform: {errors}"

    def test_capability_with_provider_info(self):
        """Test capability with provider info."""
        capability = Capability(
            name="test.action",
            description="Test",
            kind=CapabilityKind.ACTION,
            provider_name="my_provider",
            provider_type="http",
        )
        data = capability.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("capability.schema.json", data)
        assert valid, f"Capability does not conform: {errors}"


class TestCapabilityInvalidFixtures:
    """Test that invalid capabilities are rejected."""

    def test_missing_name_rejected(self):
        """Test that capability without name is rejected."""
        data = {
            "description": "Test",
            "kind": "action",
        }
        valid, errors = validate_against_schema("capability.schema.json", data)
        assert not valid, "Should reject capability without name"

    def test_missing_kind_rejected(self):
        """Test that capability without kind is rejected."""
        data = {
            "name": "test.action",
            "description": "Test",
        }
        valid, errors = validate_against_schema("capability.schema.json", data)
        assert not valid, "Should reject capability without kind"

    def test_invalid_kind_rejected(self):
        """Test that invalid kind is rejected."""
        data = {
            "name": "test.action",
            "description": "Test",
            "kind": "invalid_kind",
        }
        valid, errors = validate_against_schema("capability.schema.json", data)
        assert not valid, "Should reject invalid kind"

    def test_invalid_name_pattern_rejected(self):
        """Test that invalid name pattern is rejected."""
        data = {
            "name": "test action",  # Space not allowed
            "description": "Test",
            "kind": "action",
        }
        valid, errors = validate_against_schema("capability.schema.json", data)
        assert not valid, "Should reject name with spaces"


class TestPolicySchemaConformance:
    """Test Policy model conformance to JSON schema."""

    def test_valid_policy_conforms(self):
        """Test that a valid policy conforms to the schema."""
        policy = Policy(
            name="high_value_confirmation",
            description="Requires confirmation for high-value transactions",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
        data = policy.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("policy.schema.json", data)
        assert valid, f"Policy does not conform: {errors}"

    def test_policy_with_deny_effect(self):
        """Test policy with DENY effect."""
        policy = Policy(
            name="admin_only",
            description="Deny non-admin access",
            effect=PolicyEffect.DENY,
            subject=PolicySubject(capability_name="admin.*"),
        )
        data = policy.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("policy.schema.json", data)
        assert valid, f"Policy does not conform: {errors}"


class TestPolicyInvalidFixtures:
    """Test that invalid policies are rejected."""

    def test_missing_name_rejected(self):
        """Test that policy without name is rejected."""
        data = {
            "description": "Test",
            "effect": "allow",
            "subject": {},
        }
        valid, errors = validate_against_schema("policy.schema.json", data)
        assert not valid, "Should reject policy without name"

    def test_missing_effect_rejected(self):
        """Test that policy without effect is rejected."""
        data = {
            "name": "test_policy",
            "description": "Test",
            "subject": {},
        }
        valid, errors = validate_against_schema("policy.schema.json", data)
        assert not valid, "Should reject policy without effect"


class TestExecutionResultSchemaConformance:
    """Test ExecutionResult model conformance to JSON schema."""

    def test_success_result_conforms(self):
        """Test that a success result conforms to the schema."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"result": "success"},
            execution_time_ms=10.0,
            next={"action": "complete", "hint": "Task completed"},
            can_continue=False,
        )
        data = result.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("execution-result.schema.json", data)
        assert valid, f"Result does not conform: {errors}"

    def test_failure_result_with_fix_hint(self):
        """Test that failure result includes fix hint."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            error="Capability not found",
            error_code="not_found",
            execution_time_ms=5.0,
            next={
                "action": "retry",
                "capability": "test.action",
                "hint": "Check the input schema and ensure arguments match",
            },
            can_continue=True,
        )
        data = result.model_dump(exclude_none=True, mode="json")

        valid, errors = validate_against_schema("execution-result.schema.json", data)
        assert valid, f"Result does not conform: {errors}"


class TestExecutionResultInvalidFixtures:
    """Test that invalid execution results are rejected."""

    def test_missing_status_rejected(self):
        """Test that result without status is rejected."""
        data = {
            "data": {"result": "success"},
        }
        valid, errors = validate_against_schema("execution-result.schema.json", data)
        assert not valid, "Should reject result without status"

    def test_invalid_status_rejected(self):
        """Test that invalid status is rejected."""
        data = {
            "status": "invalid_status",
            "data": {},
        }
        valid, errors = validate_against_schema("execution-result.schema.json", data)
        assert not valid, "Should reject invalid status"


class TestSchemaStructure:
    """Test that schema files are valid JSON with proper structure."""

    def test_capability_schema_valid(self):
        """Test that capability schema is valid JSON."""
        schema = load_schema("capability.schema.json")
        assert "$schema" in schema
        assert "type" in schema
        assert "properties" in schema

    def test_policy_schema_valid(self):
        """Test that policy schema is valid JSON."""
        schema = load_schema("policy.schema.json")
        assert "$schema" in schema
        assert "type" in schema

    def test_execution_result_schema_has_next(self):
        """Test that execution-result schema has next field."""
        schema = load_schema("execution-result.schema.json")
        assert "properties" in schema
        assert "next" in schema["properties"]

    def test_error_schema_has_fix_hint(self):
        """Test that error schema has fix_hint field."""
        schema = load_schema("error.schema.json")
        assert "properties" in schema
        assert "fix_hint" in schema["properties"]


FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "spec" / "tests"


class TestFixtureConformance:
    """Test that canonical fixtures conform to schemas."""

    def _load_fixtures(self, category: str, validity: str) -> list[tuple[Path, dict]]:
        """Load all fixtures from a category."""
        fixtures = []
        base_dir = FIXTURES_DIR / validity / category
        if not base_dir.exists():
            pytest.skip(f"Fixture directory not found: {base_dir}")
        for f in base_dir.glob("*.json"):
            with open(f) as fh:
                fixtures.append((f, json.load(fh)))
        return fixtures

    def test_valid_capability_fixtures(self):
        """Test all valid capability fixtures conform to schema."""
        fixtures = self._load_fixtures("capability", "valid")
        assert len(fixtures) > 0, "No valid capability fixtures found"
        for fixture_path, data in fixtures:
            is_valid, errors = validate_against_schema("capability.schema.json", data)
            assert is_valid, f"{fixture_path.name}: {errors}"

    def test_invalid_capability_fixtures_rejected(self):
        """Test that invalid capability fixtures fail validation."""
        fixtures = self._load_fixtures("capability", "invalid")
        assert len(fixtures) > 0, "No invalid capability fixtures found"
        for fixture_path, data in fixtures:
            is_valid, _ = validate_against_schema("capability.schema.json", data)
            assert not is_valid, f"{fixture_path.name} should be rejected"

    def test_valid_policy_fixtures(self):
        """Test all valid policy fixtures conform to schema."""
        fixtures = self._load_fixtures("policy", "valid")
        assert len(fixtures) > 0, "No valid policy fixtures found"
        for fixture_path, data in fixtures:
            is_valid, errors = validate_against_schema("policy.schema.json", data)
            assert is_valid, f"{fixture_path.name}: {errors}"

    def test_invalid_policy_fixtures_rejected(self):
        """Test that invalid policy fixtures fail validation."""
        fixtures = self._load_fixtures("policy", "invalid")
        assert len(fixtures) > 0, "No invalid policy fixtures found"
        for fixture_path, data in fixtures:
            is_valid, _ = validate_against_schema("policy.schema.json", data)
            assert not is_valid, f"{fixture_path.name} should be rejected"

    def test_valid_execution_result_fixtures(self):
        """Test all valid execution-result fixtures conform to schema."""
        fixtures = self._load_fixtures("execution-result", "valid")
        assert len(fixtures) > 0, "No valid execution-result fixtures found"
        for fixture_path, data in fixtures:
            is_valid, errors = validate_against_schema("execution-result.schema.json", data)
            assert is_valid, f"{fixture_path.name}: {errors}"

    def test_invalid_execution_result_fixtures_rejected(self):
        """Test that invalid execution-result fixtures fail validation."""
        fixtures = self._load_fixtures("execution-result", "invalid")
        assert len(fixtures) > 0, "No invalid execution-result fixtures found"
        for fixture_path, data in fixtures:
            is_valid, _ = validate_against_schema("execution-result.schema.json", data)
            assert not is_valid, f"{fixture_path.name} should be rejected"

    def test_valid_workflow_fixtures(self):
        """Test all valid workflow fixtures conform to schema."""
        fixtures = self._load_fixtures("workflow", "valid")
        assert len(fixtures) > 0, "No valid workflow fixtures found"
        for fixture_path, data in fixtures:
            is_valid, errors = validate_against_schema("workflow.schema.json", data)
            assert is_valid, f"{fixture_path.name}: {errors}"

    def test_invalid_workflow_fixtures_rejected(self):
        """Test that invalid workflow fixtures fail validation."""
        fixtures = self._load_fixtures("workflow", "invalid")
        assert len(fixtures) > 0, "No invalid workflow fixtures found"
        for fixture_path, data in fixtures:
            is_valid, _ = validate_against_schema("workflow.schema.json", data)
            assert not is_valid, f"{fixture_path.name} should be rejected"

    def test_valid_discovery_fixtures(self):
        """Test all valid discovery fixtures conform to schema."""
        fixtures = self._load_fixtures("discovery", "valid")
        assert len(fixtures) > 0, "No valid discovery fixtures found"
        for fixture_path, data in fixtures:
            is_valid, errors = validate_against_schema("discovery.schema.json", data)
            assert is_valid, f"{fixture_path.name}: {errors}"

    def test_invalid_discovery_fixtures_rejected(self):
        """Test that invalid discovery fixtures fail validation."""
        fixtures = self._load_fixtures("discovery", "invalid")
        assert len(fixtures) > 0, "No invalid discovery fixtures found"
        for fixture_path, data in fixtures:
            is_valid, _ = validate_against_schema("discovery.schema.json", data)
            assert not is_valid, f"{fixture_path.name} should be rejected"
