"""OpenAPI mapping command for the AICP CLI.

Handles:
- OpenAPI 3.0.x and 3.1.x
- local $ref resolution
- requestBody / parameters / responses
- examples-only schemas
- callbacks
- links
- security requirements
- server URL inference
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from aicp.capability import (
    Capability,
    CapabilityKind,
    ContinuationSpec,
    InputSchema,
    OutputSchema,
    ProviderInfo,
)
from aicp_connect_openapi import OpenAPIDiscoverySource

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def _normalize(value: Any) -> Any:
    """Normalize values for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True, mode="json")

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(value, "__dict__"):
        return {
            k: _normalize(v) for k, v in vars(value).items() if not k.startswith("_")
        }

    return str(value)


def _load_openapi_spec(file_path: Path) -> dict[str, Any]:
    """Load an OpenAPI spec from YAML or JSON."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            if file_path.suffix.lower() in {".yaml", ".yml"}:
                try:
                    import yaml
                except ImportError as exc:
                    raise RuntimeError(
                        "PyYAML is required to read YAML OpenAPI files"
                    ) from exc
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error reading file: {exc}") from exc

    if not isinstance(spec, dict):
        raise ValueError("OpenAPI spec root must be a JSON/YAML object")

    if "openapi" not in spec:
        raise ValueError("Missing required top-level 'openapi' field")

    if "paths" not in spec or not isinstance(spec["paths"], dict):
        raise ValueError("Missing or invalid top-level 'paths' field")

    return spec


def _resolve_local_ref(spec: dict[str, Any], node: Any) -> Any:
    """Resolve local #/... refs recursively."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            if not ref.startswith("#/"):
                return node
            resolved = _resolve_ref_path(spec, ref)
            merged = deepcopy(resolved)
            # sibling keys override only where present, except $ref
            for key, value in node.items():
                if key != "$ref":
                    merged[key] = _resolve_local_ref(spec, value)
            return _resolve_local_ref(spec, merged)

        return {k: _resolve_local_ref(spec, v) for k, v in node.items()}

    if isinstance(node, list):
        return [_resolve_local_ref(spec, item) for item in node]

    return node


def _resolve_ref_path(spec: dict[str, Any], ref: str) -> Any:
    """Resolve a local JSON Pointer ref."""
    current: Any = spec
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"Unresolvable ref: {ref}")
        current = current[token]
    return deepcopy(current)


def _json_type_from_value(value: Any) -> str:
    """Infer JSON schema type from an example value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _infer_schema_from_example(value: Any) -> dict[str, Any]:
    """Infer a JSON-schema-ish shape from example data."""
    inferred_type = _json_type_from_value(value)

    if inferred_type == "object":
        assert isinstance(value, dict)
        props = {k: _infer_schema_from_example(v) for k, v in value.items()}
        return {
            "type": "object",
            "properties": props,
            "required": list(value.keys()),
        }

    if inferred_type == "array":
        assert isinstance(value, list)
        if not value:
            return {"type": "array", "items": {}}
        return {
            "type": "array",
            "items": _infer_schema_from_example(value[0]),
        }

    return {"type": inferred_type}


def _best_media_schema(
    media_obj: dict[str, Any] | None, spec: dict[str, Any]
) -> dict[str, Any] | None:
    """Extract best-effort schema from media type object."""
    if not media_obj:
        return None

    media_obj = _resolve_local_ref(spec, media_obj)

    if "schema" in media_obj and isinstance(media_obj["schema"], dict):
        return _resolve_local_ref(spec, media_obj["schema"])

    examples = media_obj.get("examples")
    if isinstance(examples, dict):
        for ex in examples.values():
            if isinstance(ex, dict) and "value" in ex:
                return _infer_schema_from_example(ex["value"])

    example = media_obj.get("example")
    if example is not None:
        return _infer_schema_from_example(example)

    return None


def _extract_content_schema(
    content: dict[str, Any] | None, spec: dict[str, Any]
) -> dict[str, Any] | None:
    """Choose the best schema from content media types."""
    if not content or not isinstance(content, dict):
        return None

    preferred_media = [
        "application/json",
        "application/*+json",
        "application/xml",
        "text/plain",
    ]

    for media_type in preferred_media:
        if media_type in content:
            schema = _best_media_schema(content[media_type], spec)
            if schema:
                return schema

    for media_obj in content.values():
        schema = _best_media_schema(media_obj, spec)
        if schema:
            return schema

    return None


def _merge_parameters(
    path_parameters: list[dict[str, Any]] | None,
    op_parameters: list[dict[str, Any]] | None,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge path-level and operation-level parameters, with operation taking precedence."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for source in path_parameters or []:
        param = _resolve_local_ref(spec, source)
        key = (param.get("name", ""), param.get("in", ""))
        merged[key] = param

    for source in op_parameters or []:
        param = _resolve_local_ref(spec, source)
        key = (param.get("name", ""), param.get("in", ""))
        merged[key] = param

    return list(merged.values())


def _parameter_to_property(
    parameter: dict[str, Any], spec: dict[str, Any]
) -> tuple[str, dict[str, Any], bool]:
    """Convert an OpenAPI parameter into an input property."""
    name = parameter["name"]
    required = bool(parameter.get("required", False))
    schema = _resolve_local_ref(spec, parameter.get("schema", {"type": "string"}))
    prop = deepcopy(schema)

    if "description" in parameter and "description" not in prop:
        prop["description"] = parameter["description"]

    location = parameter.get("in")
    if location:
        prop["x-location"] = location

    return name, prop, required


def _request_body_to_property(
    request_body: dict[str, Any], spec: dict[str, Any]
) -> tuple[str, dict[str, Any], bool]:
    """Convert requestBody into a synthetic body property."""
    request_body = _resolve_local_ref(spec, request_body)
    schema = _extract_content_schema(request_body.get("content"), spec) or {
        "type": "object"
    }
    if "description" in request_body and "description" not in schema:
        schema["description"] = request_body["description"]
    schema["x-location"] = "body"
    required = bool(request_body.get("required", False))
    return "body", schema, required


def _response_to_output_schema(
    responses: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    """Build a best-effort output schema from responses."""
    responses = _resolve_local_ref(spec, responses)
    preferred_codes = ["200", "201", "202", "203", "204", "default"]

    chosen_response: dict[str, Any] | None = None
    for code in preferred_codes:
        response = responses.get(code)
        if isinstance(response, dict):
            chosen_response = response
            break

    if chosen_response is None:
        for response in responses.values():
            if isinstance(response, dict):
                chosen_response = response
                break

    if chosen_response is None:
        return {"type": "object"}

    schema = _extract_content_schema(chosen_response.get("content"), spec)
    if schema:
        output = deepcopy(schema)
    else:
        output = {"type": "object"}

    headers = chosen_response.get("headers")
    if isinstance(headers, dict) and headers:
        resolved_headers = _resolve_local_ref(spec, headers)
        output.setdefault("x-response-headers", {})
        for header_name, header_def in resolved_headers.items():
            header_schema = header_def.get("schema", {"type": "string"})
            output["x-response-headers"][header_name] = _resolve_local_ref(
                spec, header_schema
            )

    links = chosen_response.get("links")
    if isinstance(links, dict) and links:
        output["x-links"] = _resolve_local_ref(spec, links)

    return output


def _operation_kind(method: str) -> CapabilityKind:
    """Map HTTP method to capability kind."""
    return CapabilityKind.QUERY if method.lower() == "get" else CapabilityKind.ACTION


def _make_capability_name(path: str, method: str, operation: dict[str, Any]) -> str:
    """Generate a stable capability name."""
    operation_id = operation.get("operationId")
    if operation_id:
        return operation_id

    cleaned = path.strip("/") or "root"
    cleaned = cleaned.replace("/", ".").replace("{", "").replace("}", "")
    cleaned = cleaned.replace("-", "_")
    return f"{cleaned}.{method.lower()}"


def _extract_security(
    operation: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any] | None:
    """Extract security requirements and related scheme metadata."""
    security = operation.get("security")
    if not security:
        return None

    schemes = spec.get("components", {}).get("securitySchemes", {})
    resolved: list[dict[str, Any]] = []

    for sec_req in security:
        if not isinstance(sec_req, dict):
            continue
        for scheme_name, scopes in sec_req.items():
            scheme = schemes.get(scheme_name, {})
            resolved.append(
                {
                    "scheme_name": scheme_name,
                    "type": scheme.get("type"),
                    "scheme": scheme.get("scheme"),
                    "bearerFormat": scheme.get("bearerFormat"),
                    "scopes": scopes if isinstance(scopes, list) else [],
                    "description": scheme.get("description"),
                }
            )

    return {"requirements": resolved} if resolved else None


def _extract_tags(operation: dict[str, Any]) -> list[str]:
    """Build tags from operation tags and semantic markers."""
    tags = []
    for tag in operation.get("tags", []):
        if isinstance(tag, str):
            tags.append(tag)

    if operation.get("deprecated"):
        tags.append("deprecated")

    return tags


def _make_continuation_from_links(
    operation_name: str,
    responses: dict[str, Any],
    spec: dict[str, Any],
) -> ContinuationSpec | None:
    """Build continuation hints from OpenAPI links."""
    responses = _resolve_local_ref(spec, responses)
    linked_ops: list[str] = []

    for response in responses.values():
        if not isinstance(response, dict):
            continue
        links = response.get("links")
        if not isinstance(links, dict):
            continue
        for _, link_def in links.items():
            link_def = _resolve_local_ref(spec, link_def)
            operation_id = link_def.get("operationId")
            if operation_id and operation_id not in linked_ops:
                linked_ops.append(operation_id)

    if not linked_ops:
        return None

    return ContinuationSpec(
        can_continue=True,
        next_capabilities=linked_ops,
        next_hint=f"Related follow-up operations discovered for {operation_name}",
    )


def _server_base_url(
    spec: dict[str, Any], operation: dict[str, Any] | None = None
) -> str | None:
    """Resolve base URL from operation-level or top-level servers."""
    op_servers = operation.get("servers") if operation else None
    for servers in (op_servers, spec.get("servers")):
        if isinstance(servers, list) and servers:
            first = servers[0]
            if isinstance(first, dict) and first.get("url"):
                return first["url"]
    return None


def _capability_from_operation(
    *,
    spec: dict[str, Any],
    path: str,
    method: str,
    operation: dict[str, Any],
    path_parameters: list[dict[str, Any]] | None,
) -> Capability:
    """Create a capability from an OpenAPI operation."""
    operation = _resolve_local_ref(spec, operation)
    name = _make_capability_name(path, method, operation)

    properties: dict[str, Any] = {}
    required: list[str] = []

    parameters = _merge_parameters(path_parameters, operation.get("parameters"), spec)
    for parameter in parameters:
        param_name, param_schema, is_required = _parameter_to_property(parameter, spec)
        properties[param_name] = param_schema
        if is_required:
            required.append(param_name)

    if "requestBody" in operation:
        body_name, body_schema, body_required = _request_body_to_property(
            operation["requestBody"], spec
        )
        properties[body_name] = body_schema
        if body_required:
            required.append(body_name)

    input_schema = InputSchema(
        type="object",
        properties=properties,
        required=sorted(set(required)),
        description=operation.get("description") or operation.get("summary"),
    )

    output_schema = OutputSchema(
        type="object",
        properties=_response_to_output_schema(operation.get("responses", {}), spec).get(
            "properties", {}
        ),
        description=(operation.get("responses", {}).get("200", {}) or {}).get(
            "description"
        )
        or operation.get("summary"),
    )

    # Keep richer raw output schema content if available
    full_output = _response_to_output_schema(operation.get("responses", {}), spec)
    output_schema.type = full_output.get("type", "object")
    output_schema.properties = full_output.get("properties", {})

    provider = ProviderInfo(
        name=spec.get("info", {}).get("title"),
        type="openapi",
        url=_server_base_url(spec, operation),
    )

    continuation = _make_continuation_from_links(
        name, operation.get("responses", {}), spec
    )

    tags = _extract_tags(operation)
    security = _extract_security(operation, spec)
    if security:
        tags.append("secured")
    if operation.get("callbacks"):
        tags.append("has_callbacks")
    if continuation:
        tags.append("has_links")

    capability = Capability(
        name=name,
        description=operation.get("summary")
        or operation.get("description")
        or f"{method.upper()} {path}",
        kind=_operation_kind(method),
        input_schema=input_schema,
        output_schema=output_schema,
        tags=tags,
        continuation=continuation,
        provider=provider,
        deprecated=bool(operation.get("deprecated", False)),
        deprecation_message="Marked deprecated in OpenAPI spec"
        if operation.get("deprecated")
        else None,
    )

    # attach extra metadata for downstream exporters if they preserve unknown attrs externally
    capability.__dict__["path"] = path
    capability.__dict__["method"] = method.upper()
    capability.__dict__["x_security"] = security
    capability.__dict__["x_callbacks"] = (
        _resolve_local_ref(spec, operation.get("callbacks", {}))
        if operation.get("callbacks")
        else None
    )
    capability.__dict__["x_servers"] = operation.get("servers") or spec.get("servers")
    capability.__dict__["x_operation_id"] = operation.get("operationId")

    return capability


def _callback_capabilities(
    *,
    spec: dict[str, Any],
    parent_name: str,
    callbacks: dict[str, Any],
) -> list[Capability]:
    """Extract callback operations as derived capabilities."""
    derived: list[Capability] = []

    callbacks = _resolve_local_ref(spec, callbacks)

    for callback_name, callback_map in callbacks.items():
        if not isinstance(callback_map, dict):
            continue

        for callback_expr, callback_path_item in callback_map.items():
            if not isinstance(callback_path_item, dict):
                continue

            for method, operation in callback_path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(
                    operation, dict
                ):
                    continue

                op_name = (
                    operation.get("operationId")
                    or f"{parent_name}.callback.{callback_name}.{method.lower()}"
                )
                op_copy = deepcopy(operation)
                op_copy.setdefault(
                    "summary",
                    f"Callback {callback_name}: {method.upper()} {callback_expr}",
                )

                cap = _capability_from_operation(
                    spec=spec,
                    path=callback_expr,
                    method=method,
                    operation=op_copy,
                    path_parameters=[],
                )
                cap.name = op_name
                cap.tags = list(
                    dict.fromkeys([*cap.tags, "callback", f"callback:{callback_name}"])
                )
                derived.append(cap)

    return derived


def discover_openapi_capabilities(
    spec: dict[str, Any], source_name: str
) -> list[Capability]:
    """Discover capabilities from an OpenAPI document with richer feature support."""
    spec = _resolve_local_ref(spec, spec)
    capabilities: list[Capability] = []

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        path_parameters = path_item.get("parameters", [])

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            capability = _capability_from_operation(
                spec=spec,
                path=path,
                method=method,
                operation=operation,
                path_parameters=path_parameters,
            )
            capabilities.append(capability)

            callbacks = operation.get("callbacks")
            if isinstance(callbacks, dict):
                capabilities.extend(
                    _callback_capabilities(
                        spec=spec,
                        parent_name=capability.name,
                        callbacks=callbacks,
                    )
                )

    return capabilities


async def cmd_map_openapi(args) -> int:
    """Map OpenAPI specification to capabilities."""
    file_arg = getattr(args, "file", None)
    if not file_arg:
        print(json.dumps({"error": "Missing OpenAPI file path"}))
        return 1

    file_path = Path(file_arg)
    if not file_path.exists():
        print(json.dumps({"error": f"File not found: {file_path}"}))
        return 1

    try:
        spec = _load_openapi_spec(file_path)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "file": str(file_path)}, indent=2))
        return 1

    name = getattr(args, "name", None) or file_path.stem

    # Keep adapter path if available, but fall back to richer local discovery
    capabilities: list[Capability]
    try:
        source = OpenAPIDiscoverySource(
            name=name,
            spec=spec,
            base_url=getattr(args, "base_url", None),
        )
        capabilities = await source.discover()
        if not capabilities:
            capabilities = discover_openapi_capabilities(spec, name)
    except Exception:
        capabilities = discover_openapi_capabilities(spec, name)

    if not capabilities:
        print(
            json.dumps(
                {
                    "source": name,
                    "source_type": "openapi",
                    "capability_count": 0,
                    "capabilities": [],
                },
                indent=2,
            )
        )
        return 0

    output = {
        "source": name,
        "source_type": "openapi",
        "openapi_version": spec.get("openapi"),
        "title": spec.get("info", {}).get("title"),
        "version": spec.get("info", {}).get("version"),
        "server": _server_base_url(spec),
        "capability_count": len(capabilities),
        "capabilities": [_normalize(cap) for cap in capabilities],
    }

    output_json = json.dumps(output, indent=2, default=str)

    output_arg = getattr(args, "output", None)
    if output_arg:
        try:
            output_path = Path(output_arg)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_json, encoding="utf-8")
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "error": f"Failed to write output file: {exc}",
                        "path": str(output_arg),
                    },
                    indent=2,
                )
            )
            return 1

        print(f"Mapped {len(capabilities)} capabilities to {output_path}")
        return 0

    print(output_json)
    return 0
