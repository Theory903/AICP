import json
from pathlib import Path
from typing import Any, cast

import pytest
import referencing
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError
from referencing.jsonschema import SchemaRegistry

from aicp.plugins import HookType, PluginDependency, PluginManifest, PluginType

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "spec" / "schemas"


def _create_registry() -> SchemaRegistry:
    registry: SchemaRegistry = SchemaRegistry()
    for schema_file in SCHEMAS_DIR.glob("*.json"):
        with schema_file.open() as handle:
            schema = json.load(handle)
        schema_id = f"https://aicp.dev/schemas/{schema_file.stem.replace('.schema', '')}"
        schema_copy = dict(schema)
        schema_copy.pop("$id", None)
        resource = referencing.Resource.from_contents(schema_copy)
        registry = registry.with_resource(schema_id, resource)
        registry = registry.with_resource(schema_file.name, resource)
    return registry


def _validate_plugin_schema(data: dict) -> list[str]:
    schema_path = SCHEMAS_DIR / "plugin.schema.json"
    with schema_path.open() as handle:
        schema = json.load(handle)
    schema.pop("$id", None)
    validator = Draft202012Validator(schema, registry=_create_registry())
    return [f"{error.json_path}: {error.message}" for error in validator.iter_errors(data)]


def test_manifest_normalizes_lists_and_defaults() -> None:
    manifest = PluginManifest(
        id=" demo.echo ",
        name=" Demo Echo ",
        version=" 1.2.3 ",
        description=" Echo capability plugin ",
        author=" Demo Team ",
        plugin_type=PluginType.TOOL,
        hooks=[HookType.PRE_CAPABILITY, HookType.PRE_CAPABILITY, HookType.ON_STARTUP],
        capabilities=["demo.echo", " demo.echo ", "demo.echo.admin"],
        dependencies=[PluginDependency(id="base.runtime", version="^1.0.0")],
        config_schema={"type": "object", "properties": {"token": {"type": "string"}}},
        permissions=["capability:demo.echo", "capability:demo.echo"],
    )

    assert manifest.id == "demo.echo"
    assert manifest.name == "Demo Echo"
    assert manifest.version == "1.2.3"
    assert manifest.author == "Demo Team"
    assert manifest.hooks == [HookType.PRE_CAPABILITY, HookType.ON_STARTUP]
    assert manifest.capabilities == ["demo.echo", "demo.echo.admin"]
    assert manifest.permissions == ["capability:demo.echo"]
    assert manifest.entry_point == "plugin.py"
    assert manifest.enabled_by_default is True


def test_manifest_rejects_invalid_hook_name() -> None:
    with pytest.raises(PydanticValidationError):
        PluginManifest(
            id="demo.echo",
            name="Demo Echo",
            version="1.0.0",
            description="Echo capability plugin",
            author="Demo Team",
            plugin_type=PluginType.TOOL,
            hooks=cast(Any, ["before_tool"]),
            capabilities=["demo.echo"],
            dependencies=[],
            config_schema={"type": "object"},
        )


def test_manifest_conforms_to_plugin_schema() -> None:
    manifest = PluginManifest(
        id="demo.provider",
        name="Demo Provider",
        version="2.0.0",
        description="Provider plugin",
        author="Demo Team",
        plugin_type=PluginType.PROVIDER,
        hooks=[HookType.ON_STARTUP, HookType.ON_SHUTDOWN],
        capabilities=["demo.generate"],
        dependencies=[PluginDependency(id="shared.auth", version=">=1.0.0")],
        config_schema={
            "type": "object",
            "properties": {"api_key": {"type": "string"}},
            "required": ["api_key"],
        },
        permissions=["network:outbound", "capability:demo.generate"],
    )

    errors = _validate_plugin_schema(manifest.model_dump(mode="json", exclude_none=True))

    assert errors == []
