"""Conformance tests for plugin manifest schema."""

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


@pytest.fixture
def manifest_schema():
    """Load the plugin manifest schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "plugin-manifest.schema.json"
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def valid_manifest_basic():
    """Basic valid plugin manifest."""
    return {
        "id": "my-plugin",
        "kind": "capability_source",
        "name": "My Plugin",
        "version": "1.0.0",
    }


@pytest.fixture
def valid_manifest_full():
    """Complete valid plugin manifest."""
    return {
        "id": "memory-lancedb",
        "kind": "capability_source",
        "name": "LanceDB Memory Store",
        "version": "1.0.0",
        "description": "Semantic memory storage backed by LanceDB",
        "author": "AICP Team",
        "license": "Apache-2.0",
        "repository": "https://github.com/aicp/aicp",
        "tags": ["memory", "storage", "vector-db"],
        "requirements": {
            "aicp_version_min": "1.0.0",
            "aicp_version_max": "2.0.0",
            "python_version_min": "3.11",
            "dependencies": {
                "lancedb": ">=0.3.0",
                "pydantic": ">=2.0",
            }
        },
        "config_schema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Database path"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["db_path"],
        },
        "ui_hints": {
            "categories": ["memory", "storage"],
            "field_order": ["db_path", "max_results"],
            "field_hints": {
                "db_path": {
                    "label": "Database Path",
                    "description": "Where to store the database",
                    "input_type": "text",
                    "placeholder": "/var/lib/lancedb",
                }
            }
        },
        "lifecycle": {
            "auto_enable": False,
            "auto_enable_when_configured": ["provider_x"],
            "lazy_load": True,
            "isolation_mode": "sandbox",
        },
        "capabilities": [
            {
                "name": "memory.store",
                "kind": "action",
                "description": "Store a memory",
            },
            {
                "name": "memory.retrieve",
                "kind": "query",
                "description": "Retrieve memories",
            }
        ],
        "hooks": [
            "on_capability_execute_after",
            "on_learning_event",
        ],
        "contracts": {
            "capability_ids": ["memory.store", "memory.retrieve"],
            "workflow_templates": ["memory-workflow"],
            "policy_sets": ["memory-policy"],
        },
        "permissions": {
            "access_level": "scoped",
            "requires_approval": False,
            "trust_tier": 2,
        },
        "entry_points": {
            "main": "memory_lancedb:define_plugin",
            "runtime": "memory_lancedb.runtime:*",
            "setup": "memory_lancedb.setup:wizard",
        },
        "enabled_by_default": False,
        "legacy_plugin_ids": ["old-memory-plugin"],
    }


# Basic validation tests
class TestManifestValidation:
    def test_valid_minimal_manifest(self, manifest_schema, valid_manifest_basic):
        """Valid minimal manifest passes."""
        validate(instance=valid_manifest_basic, schema=manifest_schema)

    def test_valid_full_manifest(self, manifest_schema, valid_manifest_full):
        """Valid full manifest passes."""
        validate(instance=valid_manifest_full, schema=manifest_schema)

    def test_missing_id(self, manifest_schema, valid_manifest_basic):
        """Missing 'id' field fails."""
        manifest = valid_manifest_basic.copy()
        del manifest["id"]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_missing_kind(self, manifest_schema, valid_manifest_basic):
        """Missing 'kind' field fails."""
        manifest = valid_manifest_basic.copy()
        del manifest["kind"]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_missing_name(self, manifest_schema, valid_manifest_basic):
        """Missing 'name' field fails."""
        manifest = valid_manifest_basic.copy()
        del manifest["name"]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_missing_version(self, manifest_schema, valid_manifest_basic):
        """Missing 'version' field fails."""
        manifest = valid_manifest_basic.copy()
        del manifest["version"]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)


# Field value tests
class TestManifestFieldValues:
    def test_invalid_id_pattern(self, manifest_schema, valid_manifest_basic):
        """ID with invalid pattern fails."""
        manifest = valid_manifest_basic.copy()
        manifest["id"] = "Invalid-ID"  # Uppercase not allowed
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_invalid_version_pattern(self, manifest_schema, valid_manifest_basic):
        """Version with invalid format fails."""
        manifest = valid_manifest_basic.copy()
        manifest["version"] = "1.0"  # Missing patch version
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_invalid_kind(self, manifest_schema, valid_manifest_basic):
        """Invalid plugin kind fails."""
        manifest = valid_manifest_basic.copy()
        manifest["kind"] = "invalid_kind"
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_valid_kinds(self, manifest_schema, valid_manifest_basic):
        """All valid kinds pass."""
        for kind in [
            "capability_source",
            "workflow_plugin",
            "approval_plugin",
            "policy_plugin",
            "perception_plugin",
            "learning_plugin",
            "generic",
        ]:
            manifest = valid_manifest_basic.copy()
            manifest["kind"] = kind
            validate(instance=manifest, schema=manifest_schema)


# Lifecycle tests
class TestManifestLifecycle:
    def test_lifecycle_defaults(self, manifest_schema, valid_manifest_basic):
        """Lifecycle uses sensible defaults."""
        manifest = valid_manifest_basic.copy()
        manifest["lifecycle"] = {}
        validate(instance=manifest, schema=manifest_schema)

    def test_invalid_isolation_mode(self, manifest_schema, valid_manifest_basic):
        """Invalid isolation mode fails."""
        manifest = valid_manifest_basic.copy()
        manifest["lifecycle"] = {"isolation_mode": "invalid"}
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_valid_isolation_modes(self, manifest_schema, valid_manifest_basic):
        """Valid isolation modes pass."""
        for mode in ["main", "sandbox"]:
            manifest = valid_manifest_basic.copy()
            manifest["lifecycle"] = {"isolation_mode": mode}
            validate(instance=manifest, schema=manifest_schema)


# Permissions tests
class TestManifestPermissions:
    def test_trust_tier_range(self, manifest_schema, valid_manifest_basic):
        """Trust tier must be 0-4."""
        for tier in [0, 1, 2, 3, 4]:
            manifest = valid_manifest_basic.copy()
            manifest["permissions"] = {"trust_tier": tier}
            validate(instance=manifest, schema=manifest_schema)

        manifest = valid_manifest_basic.copy()
        manifest["permissions"] = {"trust_tier": 5}
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_invalid_access_level(self, manifest_schema, valid_manifest_basic):
        """Invalid access level fails."""
        manifest = valid_manifest_basic.copy()
        manifest["permissions"] = {"access_level": "invalid"}
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)

    def test_valid_access_levels(self, manifest_schema, valid_manifest_basic):
        """Valid access levels pass."""
        for level in ["unrestricted", "scoped", "minimal"]:
            manifest = valid_manifest_basic.copy()
            manifest["permissions"] = {"access_level": level}
            validate(instance=manifest, schema=manifest_schema)


# Hook tests
class TestManifestHooks:
    def test_valid_hooks(self, manifest_schema, valid_manifest_basic):
        """Valid hook phases pass."""
        manifest = valid_manifest_basic.copy()
        manifest["hooks"] = [
            "on_plugin_initialize",
            "on_capability_execute_after",
            "on_policy_evaluate_before",
        ]
        validate(instance=manifest, schema=manifest_schema)

    def test_invalid_hook_phase(self, manifest_schema, valid_manifest_basic):
        """Invalid hook phase fails."""
        manifest = valid_manifest_basic.copy()
        manifest["hooks"] = ["invalid_hook"]
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)


# Additional properties test
class TestManifestAdditionalProperties:
    def test_no_additional_properties(self, manifest_schema, valid_manifest_basic):
        """Additional unknown properties fail."""
        manifest = valid_manifest_basic.copy()
        manifest["unknown_field"] = "value"
        with pytest.raises(ValidationError):
            validate(instance=manifest, schema=manifest_schema)


# Real-world schema compliance
class TestRealWorldScenarios:
    def test_multiplatform_plugin(self, manifest_schema):
        """Plugin targeting multiple Python versions."""
        manifest = {
            "id": "cross-platform-plugin",
            "kind": "generic",
            "name": "Cross-Platform Plugin",
            "version": "2.1.3",
            "requirements": {
                "python_version_min": "3.9",
                "dependencies": {
                    "requests": ">=2.28.0",
                    "pydantic": ">=1.10,<3",
                }
            },
        }
        validate(instance=manifest, schema=manifest_schema)

    def test_workflow_plugin_with_hooks(self, manifest_schema):
        """Workflow plugin with multiple hooks."""
        manifest = {
            "id": "saga-workflow",
            "kind": "workflow_plugin",
            "name": "Saga Workflow Plugin",
            "version": "1.0.0",
            "hooks": [
                "on_workflow_step_before",
                "on_workflow_step_after",
            ],
        }
        validate(instance=manifest, schema=manifest_schema)

    def test_policy_plugin_with_permission_boundaries(self, manifest_schema):
        """Policy plugin with permission and trust constraints."""
        manifest = {
            "id": "custom-policy",
            "kind": "policy_plugin",
            "name": "Custom Policy Engine",
            "version": "3.0.0",
            "permissions": {
                "access_level": "scoped",
                "requires_approval": True,
                "trust_tier": 3,
            },
        }
        validate(instance=manifest, schema=manifest_schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
