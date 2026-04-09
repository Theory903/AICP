"""GraphQL discovery and execution helpers for AICP."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from aicp.capability import (
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    ProviderInfo,
    RenderSpec,
)
from aicp.interfaces.discovery_source import DiscoverySource
from aicp.interfaces.executor import ExecutionResult, ExecutionStatus, Executor
from aicp.plugins import PluginMetadata, TransportPlugin, register_transport

try:  # pragma: no cover - exercised indirectly when aiohttp is installed
    import aiohttp
except ImportError:  # pragma: no cover
    aiohttp = None


INTROSPECTION_QUERY = """
query AicpGraphqlIntrospection {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      kind
      name
      fields(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
        args {
          name
          description
          defaultValue
          type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                  }
                }
              }
            }
          }
        }
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
""".strip()


@dataclass(slots=True)
class _GraphQLBinding:
    capability_name: str
    field_name: str
    operation: str
    selection_set: str | None


@register_transport("graphql")
class GraphQLTransport(TransportPlugin):
    """GraphQL transport for capability execution over HTTP."""

    def __init__(
        self,
        url: str | None = None,
        endpoint: str = "/graphql",
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.url = url
        self.endpoint = endpoint
        self.headers = dict(headers or {})
        self.timeout_seconds = timeout_seconds
        self._session: Any = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="graphql-transport",
            version="1.0.0",
            description="GraphQL transport for capability execution",
            tags=["graphql", "api", "query"],
        )

    @property
    def endpoint_url(self) -> str:
        """Return the fully qualified endpoint URL."""
        return self._build_url()

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize transport from config."""
        if not config:
            return

        self.url = config.get("url", self.url)
        self.endpoint = config.get("endpoint", self.endpoint)
        self.timeout_seconds = float(config.get("timeout_seconds", self.timeout_seconds))

        config_headers = config.get("headers")
        if isinstance(config_headers, dict):
            self.headers = {str(key): str(value) for key, value in config_headers.items()}

    async def shutdown(self) -> None:
        """Shutdown transport resources."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    def get_transport_type(self) -> str:
        return "graphql"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a GraphQL request and normalize the result shape."""
        started_at = time.perf_counter()
        query = request.get("query")
        if not query or not isinstance(query, str):
            return self._dump_result(
                ExecutionResult.failure(
                    error="Missing or invalid GraphQL query",
                    error_code="invalid_request",
                    execution_time_ms=self._elapsed_ms(started_at),
                )
            )

        try:
            payload = await self.send_raw(request)
        except RuntimeError as exc:
            return self._dump_result(
                ExecutionResult.failure(
                    error=str(exc),
                    error_code="unavailable_dependency",
                    execution_time_ms=self._elapsed_ms(started_at),
                    status=ExecutionStatus.UNAVAILABLE,
                )
            )
        except asyncio.TimeoutError:
            return self._dump_result(
                ExecutionResult.failure(
                    error="GraphQL request timed out",
                    error_code="timeout",
                    execution_time_ms=self._elapsed_ms(started_at),
                    status=ExecutionStatus.TIMEOUT,
                )
            )
        except ValueError as exc:
            return self._dump_result(
                ExecutionResult.failure(
                    error=str(exc),
                    error_code="invalid_response",
                    execution_time_ms=self._elapsed_ms(started_at),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._dump_result(
                ExecutionResult.failure(
                    error=f"Unexpected GraphQL execution failure: {exc}",
                    error_code="execution_failed",
                    execution_time_ms=self._elapsed_ms(started_at),
                )
            )

        status_code = payload.get("_http", {}).get("status_code")
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            status, error_code = self._classify_graphql_errors(errors, status_code)
            return self._dump_result(
                ExecutionResult.failure(
                    error=self._first_graphql_error_message(errors),
                    error_code=error_code,
                    execution_time_ms=self._elapsed_ms(started_at),
                    status=status,
                )
            )

        if "data" not in payload:
            return self._dump_result(
                ExecutionResult.failure(
                    error="GraphQL response did not contain a data field",
                    error_code="invalid_response",
                    execution_time_ms=self._elapsed_ms(started_at),
                )
            )

        return self._dump_result(
            ExecutionResult.success(
                data=payload.get("data"),
                execution_time_ms=self._elapsed_ms(started_at),
                format_hint="json",
            )
        )

    async def send_raw(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a GraphQL HTTP request and return the parsed body."""
        if aiohttp is None:
            raise RuntimeError("GraphQL transport requires aiohttp. Install the core 'http' extra to use it.")

        full_url = self._build_url()
        headers = self._build_headers()
        payload = {
            "query": request["query"],
            "variables": request.get("variables", {}),
            "operationName": request.get("operationName"),
        }

        session = await self._get_session()
        async with session.post(full_url, json=payload, headers=headers) as response:
            text = await response.text()
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON response from GraphQL server") from exc

        if not isinstance(parsed, dict):
            raise ValueError("GraphQL response must be a JSON object")

        normalized = dict(parsed)
        normalized["_http"] = {"status_code": response.status}
        return normalized

    async def receive(self) -> dict[str, Any]:
        """GraphQL over HTTP is request-response only."""
        raise NotImplementedError("GraphQL transport is request-response only. Use send().")

    async def _get_session(self) -> Any:
        """Get or create an aiohttp session."""
        if aiohttp is None:
            raise RuntimeError("GraphQL transport requires aiohttp. Install the core 'http' extra to use it.")

        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _build_url(self) -> str:
        if self.url:
            return f"{self.url.rstrip('/')}/{self.endpoint.lstrip('/')}"
        return self.endpoint

    def _build_headers(self) -> dict[str, str]:
        headers = dict(self.headers)
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Accept", "application/json")
        return headers

    def _dump_result(self, result: ExecutionResult) -> dict[str, Any]:
        return result.model_dump(exclude_none=True, mode="json")

    def _elapsed_ms(self, started_at: float) -> float:
        return (time.perf_counter() - started_at) * 1000.0

    def _first_graphql_error_message(self, errors: list[dict[str, Any]]) -> str:
        first_error = errors[0] if errors else {}
        message = first_error.get("message")
        return str(message).strip() if message else "GraphQL execution returned errors"

    def _classify_graphql_errors(
        self,
        errors: list[dict[str, Any]],
        status_code: int | None,
    ) -> tuple[ExecutionStatus, str]:
        code = ""
        first_error = errors[0] if errors else {}
        extensions = first_error.get("extensions")
        if isinstance(extensions, dict):
            extension_code = extensions.get("code")
            if extension_code is not None:
                code = str(extension_code).strip().upper()

        if status_code == 429 or code in {"RATE_LIMITED", "TOO_MANY_REQUESTS"}:
            return ExecutionStatus.RATE_LIMITED, "rate_limited"
        if code == "UNAUTHENTICATED":
            return ExecutionStatus.FAILURE, "authentication_failed"
        if code == "FORBIDDEN":
            return ExecutionStatus.FAILURE, "policy_denied"
        if code in {"BAD_USER_INPUT", "GRAPHQL_VALIDATION_FAILED"}:
            return ExecutionStatus.FAILURE, "validation_failed"
        if code == "NOT_FOUND":
            return ExecutionStatus.FAILURE, "resource_not_found"
        if status_code is not None and status_code >= 500:
            return ExecutionStatus.UNAVAILABLE, "server_error"
        if status_code is not None and status_code >= 400:
            return ExecutionStatus.FAILURE, "invalid_request"
        return ExecutionStatus.FAILURE, "graphql_execution_failed"


class GraphQLDiscoverySource(DiscoverySource):
    """Discover AICP capabilities from a GraphQL schema introspection response."""

    def __init__(
        self,
        name: str,
        transport: GraphQLTransport,
        namespace: str | None = None,
    ) -> None:
        self._name = name.strip() or "graphql"
        self._transport = transport
        self._namespace = _normalize_namespace(namespace)
        self._capabilities: list[Capability] | None = None
        self._bindings: dict[str, _GraphQLBinding] = {}

    @property
    def source_type(self) -> str:
        return "graphql"

    @property
    def source_name(self) -> str:
        return self._name

    @property
    def transport(self) -> GraphQLTransport:
        return self._transport

    async def discover(self) -> list[Capability]:
        if self._capabilities is None:
            self._capabilities = await self._discover_capabilities()
        return list(self._capabilities)

    async def refresh(self) -> list[Capability]:
        self._capabilities = None
        self._bindings = {}
        return await self.discover()

    async def get_binding(self, capability_name: str) -> _GraphQLBinding | None:
        if capability_name in self._bindings:
            return self._bindings[capability_name]

        await self.discover()
        return self._bindings.get(capability_name)

    async def _discover_capabilities(self) -> list[Capability]:
        response = await self._transport.send(
            {
                "query": INTROSPECTION_QUERY,
                "variables": {},
                "operationName": "AicpGraphqlIntrospection",
            }
        )

        if response.get("status") != ExecutionStatus.SUCCESS.value:
            raise self.discovery_error(
                str(response.get("error") or "GraphQL introspection failed"),
                details=response,
            )

        schema = response.get("data", {}).get("__schema")
        if not isinstance(schema, dict):
            raise self.discovery_error("GraphQL introspection did not return __schema", details=response)

        capabilities: list[Capability] = []
        seen_names: set[str] = set()
        types = schema.get("types")
        if not isinstance(types, list):
            return capabilities

        type_index = {
            type_info.get("name"): type_info
            for type_info in types
            if isinstance(type_info, dict) and type_info.get("name")
        }

        for operation, root_key in (("query", "queryType"), ("mutation", "mutationType")):
            root = schema.get(root_key)
            root_name = root.get("name") if isinstance(root, dict) else None
            root_type = type_index.get(root_name)
            if not isinstance(root_type, dict):
                continue

            fields = root_type.get("fields")
            if not isinstance(fields, list):
                continue

            for field in fields:
                if not isinstance(field, dict) or not field.get("name"):
                    continue
                capability, binding = self._capability_from_field(field, operation, seen_names)
                seen_names.add(capability.name)
                self._bindings[capability.name] = binding
                capabilities.append(capability)

        return capabilities

    def _capability_from_field(
        self,
        field: dict[str, Any],
        operation: str,
        seen_names: set[str],
    ) -> tuple[Capability, _GraphQLBinding]:
        field_name = str(field["name"])
        capability_name = self._unique_capability_name(
            _apply_namespace(_infer_capability_name(field_name, operation), self._namespace),
            field_name,
            seen_names,
        )

        input_properties: dict[str, Any] = {}
        required_fields: list[str] = []
        args = field.get("args")
        if isinstance(args, list):
            for argument in args:
                if not isinstance(argument, dict) or not argument.get("name"):
                    continue
                arg_name = str(argument["name"])
                input_properties[arg_name] = _graphql_type_to_json_schema(argument.get("type"))
                description = argument.get("description")
                if description:
                    input_properties[arg_name]["description"] = str(description)
                if _is_required_graphql_type(argument.get("type")):
                    required_fields.append(arg_name)

        output_payload = _graphql_type_to_json_schema(field.get("type"))
        description = field.get("description")
        if description:
            output_payload["description"] = str(description)

        tags = [
            "protocol:graphql",
            f"graphql:{operation}",
            f"graphql:field:{_to_snake_case(field_name)}",
        ]
        if field.get("isDeprecated"):
            tags.append("deprecated")

        kind = CapabilityKind.QUERY if operation == "query" else CapabilityKind.ACTION
        capability = Capability(
            name=capability_name,
            description=str(description or f"GraphQL {operation} field {field_name}"),
            kind=kind,
            input_schema=InputSchema(properties=input_properties, required=required_fields),
            output_schema=OutputSchema(**output_payload),
            provider=ProviderInfo(name=self.source_name, type="graphql", url=self._transport.endpoint_url),
            render=RenderSpec(format="json"),
            tags=tags,
            deprecated=bool(field.get("isDeprecated")),
            deprecation_message=(str(field["deprecationReason"]) if field.get("deprecationReason") else None),
        )
        binding = _GraphQLBinding(
            capability_name=capability_name,
            field_name=field_name,
            operation=operation,
            selection_set=_default_selection_set(field.get("type")),
        )
        return capability, binding

    def _unique_capability_name(
        self,
        inferred_name: str,
        field_name: str,
        seen_names: set[str],
    ) -> str:
        if inferred_name not in seen_names:
            return inferred_name

        fallback = _apply_namespace(f"graphql.{_to_snake_case(field_name)}", self._namespace)
        if fallback not in seen_names:
            return fallback

        suffix = 2
        candidate = f"{fallback}_{suffix}"
        while candidate in seen_names:
            suffix += 1
            candidate = f"{fallback}_{suffix}"
        return candidate


class GraphQLExecutor(Executor):
    """Execute discovered GraphQL capabilities with normalized results."""

    def __init__(
        self,
        transport: GraphQLTransport | None = None,
        source: GraphQLDiscoverySource | None = None,
    ) -> None:
        if source is None and transport is None:
            raise ValueError("GraphQLExecutor requires a transport or discovery source")
        resolved_transport = transport
        if resolved_transport is None:
            assert source is not None
            resolved_transport = source.transport
        self._source = source
        self._transport = resolved_transport

    @property
    def executor_type(self) -> str:
        return "graphql"

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        started_at = time.perf_counter()
        binding = await self._resolve_binding(capability_name)
        if binding is None:
            return ExecutionResult.failure(
                error=f"Capability not found: {capability_name}",
                error_code="capability_not_found",
                execution_time_ms=self._elapsed_ms(started_at),
            )

        safe_context = dict(context or {})
        selection_set = safe_context.get("selection_set")
        if selection_set is None:
            selection_set = binding.selection_set

        request = {
            "query": graphql_operation_for_field(
                field_name=binding.field_name,
                arguments=arguments,
                operation=binding.operation,
                selection_set=selection_set,
            ),
            "variables": arguments,
            "operationName": binding.field_name,
        }
        transport_result = await self._transport.send(request)
        return self._normalize_transport_result(transport_result, binding, started_at)

    async def _resolve_binding(self, capability_name: str) -> _GraphQLBinding | None:
        if self._source is None:
            return None
        return await self._source.get_binding(capability_name)

    def _normalize_transport_result(
        self,
        payload: dict[str, Any],
        binding: _GraphQLBinding,
        started_at: float,
    ) -> ExecutionResult:
        try:
            validated = ExecutionResult.model_validate(payload)
        except ValidationError:
            return ExecutionResult.failure(
                error="GraphQL transport returned an invalid execution payload",
                error_code="invalid_response",
                execution_time_ms=self._elapsed_ms(started_at),
            )

        if validated.is_success:
            next_payload = validated.next or {
                "action": "complete",
                "capability": binding.capability_name,
                "hint": None,
            }
            return ExecutionResult.success(
                data=validated.data,
                execution_time_ms=validated.execution_time_ms or self._elapsed_ms(started_at),
                next=next_payload,
                warnings=validated.warnings,
                rendered=validated.rendered,
                format_hint=validated.format_hint or "json",
                can_continue=validated.can_continue,
                continuation_hint=validated.continuation_hint,
            )

        return ExecutionResult.failure(
            error=validated.error or "GraphQL execution failed",
            error_code=validated.error_code,
            execution_time_ms=validated.execution_time_ms or self._elapsed_ms(started_at),
            next=validated.next,
            can_continue=validated.can_continue,
            continuation_hint=validated.continuation_hint,
            approval_request_id=validated.approval_request_id,
            approval_status=validated.approval_status,
            status=validated.status,
        )

    def _elapsed_ms(self, started_at: float) -> float:
        return (time.perf_counter() - started_at) * 1000.0


class GraphQLSchemaGenerator:
    """Generate a minimal GraphQL schema from AICP capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, dict[str, Any]] = {}

    def add_capability(
        self,
        name: str,
        description: str,
        input_fields: dict[str, Any] | None = None,
        output_type: str = "JSONString",
        kind: str = "action",
    ) -> None:
        self._capabilities[name] = {
            "description": description,
            "input": dict(input_fields or {}),
            "output": output_type or "JSONString",
            "kind": kind,
        }

    def generate_schema(self) -> str:
        query_fields: list[str] = []
        mutation_fields: list[str] = []
        custom_types: set[str] = set()

        for name, capability in self._capabilities.items():
            field_name = self._field_name(name)
            args = self._render_args(capability["input"])
            output_type = capability["output"]

            if output_type not in {"String", "Boolean", "Int", "Float", "ID", "JSONString"}:
                custom_types.add(output_type)

            line = f'  """{capability["description"]}"""\n  {field_name}{args}: {output_type}'
            if capability["kind"] == "query":
                query_fields.append(line)
            else:
                mutation_fields.append(line)

        schema_lines: list[str] = ['"""AICP Capability Schema"""', "scalar JSONString", ""]

        schema_lines.append("type Query {")
        schema_lines.extend(query_fields or ["  _empty: Boolean"])
        schema_lines.append("}")
        schema_lines.append("")

        schema_lines.append("type Mutation {")
        schema_lines.extend(mutation_fields or ["  _empty: Boolean"])
        schema_lines.append("}")
        schema_lines.append("")

        for type_name in sorted(custom_types):
            schema_lines.append(f"type {type_name} {{")
            schema_lines.append("  value: JSONString")
            schema_lines.append("}")
            schema_lines.append("")

        return "\n".join(schema_lines).rstrip()

    @staticmethod
    def _field_name(capability_name: str) -> str:
        field = capability_name.replace(".", "_").replace("-", "_")
        field = field.replace("{", "").replace("}", "")
        return field

    @staticmethod
    def _render_args(input_fields: dict[str, Any]) -> str:
        if not input_fields:
            return ""

        arg_parts: list[str] = []
        for name in input_fields:
            safe_name = str(name).replace("-", "_")
            arg_parts.append(f"{safe_name}: JSONString")

        return f"({', '.join(arg_parts)})"


def graphql_operation_for_field(
    field_name: str,
    arguments: dict[str, Any],
    *,
    operation: str = "mutation",
    selection_set: str | None = None,
) -> str:
    """Generate a GraphQL operation string for a root field."""
    safe_field_name = _sanitize_graphql_identifier(field_name)

    variable_defs: list[str] = []
    field_args: list[str] = []
    for key in arguments:
        safe_key = _sanitize_graphql_identifier(str(key))
        variable_defs.append(f"${safe_key}: JSONString")
        field_args.append(f"{safe_key}: ${safe_key}")

    variables_part = f"({', '.join(variable_defs)})" if variable_defs else ""
    args_part = f"({', '.join(field_args)})" if field_args else ""
    selection_block = ""
    if selection_set:
        indented = "\n".join(f"    {line}" for line in str(selection_set).splitlines())
        selection_block = f" {{\n{indented}\n  }}"

    return f"{operation} {safe_field_name}{variables_part} {{\n  {safe_field_name}{args_part}{selection_block}\n}}"


def graphql_query_from_capability(
    capability_name: str,
    arguments: dict[str, Any],
    *,
    operation: str = "mutation",
    selection_set: str = "success data error error_code",
) -> str:
    """Generate a GraphQL operation string from a capability name and arguments."""
    return graphql_operation_for_field(
        field_name=capability_name.replace(".", "_").replace("-", "_").replace("{", "").replace("}", ""),
        arguments=arguments,
        operation=operation,
        selection_set=selection_set,
    )


def _sanitize_graphql_identifier(value: str) -> str:
    return value.replace("-", "_").replace(".", "_").replace("{", "").replace("}", "")


def _to_snake_case(value: str) -> str:
    normalized = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    normalized = normalized.replace("-", "_")
    normalized = re.sub(r"__+", "_", normalized)
    return normalized.strip("_").lower()


def _infer_capability_name(field_name: str, operation: str) -> str:
    snake_name = _to_snake_case(field_name)
    prefixes = {
        "list_": "list",
        "get_": "get",
        "fetch_": "get",
        "create_": "create",
        "update_": "update",
        "delete_": "delete",
        "remove_": "delete",
        "search_": "search",
    }
    for prefix, action in prefixes.items():
        if snake_name.startswith(prefix):
            resource = snake_name[len(prefix) :] or "item"
            return f"{resource}.{action}"

    if operation == "query":
        return f"graphql.{snake_name}"
    return f"graphql.{snake_name}"


def _normalize_namespace(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    cleaned = namespace.strip().strip(".")
    return cleaned or None


def _apply_namespace(name: str, namespace: str | None) -> str:
    if not namespace:
        return name
    return f"{namespace}.{name}"


def _is_required_graphql_type(type_ref: Any) -> bool:
    return isinstance(type_ref, dict) and type_ref.get("kind") == "NON_NULL"


def _default_selection_set(type_ref: Any) -> str | None:
    named_kind = _named_graphql_kind(type_ref)
    if named_kind in {"OBJECT", "INTERFACE", "UNION"}:
        return "__typename"
    return None


def _named_graphql_kind(type_ref: Any) -> str | None:
    current = type_ref if isinstance(type_ref, dict) else None
    while isinstance(current, dict):
        kind = current.get("kind")
        if kind not in {"NON_NULL", "LIST"}:
            return str(kind) if kind is not None else None
        current = current.get("ofType")
    return None


def _named_graphql_type(type_ref: Any) -> str | None:
    current = type_ref if isinstance(type_ref, dict) else None
    while isinstance(current, dict):
        kind = current.get("kind")
        name = current.get("name")
        if kind not in {"NON_NULL", "LIST"}:
            return str(name) if name is not None else None
        current = current.get("ofType")
    return None


def _graphql_type_to_json_schema(type_ref: Any) -> dict[str, Any]:
    if not isinstance(type_ref, dict):
        return {"type": "object"}

    kind = type_ref.get("kind")
    name = type_ref.get("name")
    of_type = type_ref.get("ofType")

    if kind == "NON_NULL":
        return _graphql_type_to_json_schema(of_type)

    if kind == "LIST":
        return {
            "type": "array",
            "items": _graphql_type_to_json_schema(of_type),
            "x-graphql-type": _named_graphql_type(type_ref),
        }

    if kind == "SCALAR":
        scalar_map = {
            "String": {"type": "string"},
            "ID": {"type": "string"},
            "Int": {"type": "integer"},
            "Float": {"type": "number"},
            "Boolean": {"type": "boolean"},
        }
        if name in scalar_map:
            return scalar_map[str(name)]
        return {"type": "string", "x-graphql-type": name}

    if kind == "ENUM":
        return {"type": "string", "x-graphql-type": name}

    if kind in {"OBJECT", "INPUT_OBJECT", "INTERFACE", "UNION"}:
        return {"type": "object", "properties": {}, "required": [], "x-graphql-type": name}

    return {"type": "object", "x-graphql-type": name}


__all__ = [
    "GraphQLDiscoverySource",
    "GraphQLExecutor",
    "GraphQLSchemaGenerator",
    "GraphQLTransport",
    "INTROSPECTION_QUERY",
    "graphql_operation_for_field",
    "graphql_query_from_capability",
]
