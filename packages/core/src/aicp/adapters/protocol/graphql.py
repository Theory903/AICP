"""GraphQL transport adapter for AICP.

Provides GraphQL-based capability execution.
"""

from __future__ import annotations

import json
from typing import Any

import aiohttp

from aicp.plugins import PluginMetadata, TransportPlugin, register_transport


@register_transport("graphql")
class GraphQLTransport(TransportPlugin):
    """GraphQL transport for capability execution.

    Executes capabilities as GraphQL queries/mutations over HTTP.
    """

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
        self._session: aiohttp.ClientSession | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="graphql-transport",
            version="1.0.0",
            description="GraphQL transport for capability execution",
            tags=["graphql", "api", "query"],
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize transport from config."""
        if not config:
            return

        self.url = config.get("url", self.url)
        self.endpoint = config.get("endpoint", self.endpoint)
        self.timeout_seconds = float(config.get("timeout_seconds", self.timeout_seconds))

        config_headers = config.get("headers")
        if isinstance(config_headers, dict):
            self.headers = {str(k): str(v) for k, v in config_headers.items()}

    def shutdown(self) -> None:
        """Shutdown transport.

        Session cleanup is async, so callers should prefer close().
        """
        pass

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    def get_transport_type(self) -> str:
        return "graphql"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a GraphQL request.

        Expected request format:
        {
            "query": "...",
            "variables": {...},
            "operationName": "OptionalOperationName"
        }
        """
        query = request.get("query")
        if not query or not isinstance(query, str):
            return {
                "success": False,
                "error": "Missing or invalid GraphQL query",
                "error_code": "invalid_request",
            }

        full_url = self._build_url()
        headers = self._build_headers()

        payload = {
            "query": query,
            "variables": request.get("variables", {}),
            "operationName": request.get("operationName"),
        }

        try:
            session = await self._get_session()
            async with session.post(
                full_url,
                json=payload,
                headers=headers,
            ) as response:
                text = await response.text()

                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Invalid JSON response from GraphQL server",
                        "error_code": "invalid_response",
                        "status_code": response.status,
                        "raw_response": text,
                    }

                if response.status >= 400:
                    return {
                        "success": False,
                        "error": f"GraphQL HTTP error: {response.status}",
                        "error_code": "http_error",
                        "status_code": response.status,
                        "errors": result.get("errors"),
                        "data": result.get("data"),
                    }

                if result.get("errors"):
                    return {
                        "success": False,
                        "error": "GraphQL execution returned errors",
                        "error_code": "graphql_errors",
                        "errors": result["errors"],
                        "data": result.get("data"),
                    }

                return {
                    "success": True,
                    "data": result.get("data"),
                    "extensions": result.get("extensions"),
                }

        except aiohttp.ClientError as exc:
            return {
                "success": False,
                "error": f"GraphQL transport error: {exc}",
                "error_code": "transport_error",
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Unexpected GraphQL execution failure: {exc}",
                "error_code": "unexpected_error",
            }

    async def receive(self) -> dict[str, Any]:
        """Receive response.

        GraphQL over HTTP is request-response, so receive() is not supported.
        """
        raise NotImplementedError("GraphQL transport is request-response only. Use send().")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _build_url(self) -> str:
        """Build the full GraphQL endpoint URL."""
        if self.url:
            return f"{self.url.rstrip('/')}/{self.endpoint.lstrip('/')}"
        return self.endpoint

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self.headers)
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Accept", "application/json")
        return headers


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
        """Add a capability to the schema registry."""
        self._capabilities[name] = {
            "description": description,
            "input": dict(input_fields or {}),
            "output": output_type or "JSONString",
            "kind": kind,
        }

    def generate_schema(self) -> str:
        """Generate a GraphQL schema string."""
        query_fields: list[str] = []
        mutation_fields: list[str] = []
        custom_types: set[str] = set()

        for name, capability in self._capabilities.items():
            field_name = self._field_name(name)
            args = self._render_args(capability["input"])
            output_type = capability["output"]

            if output_type not in {"String", "Boolean", "Int", "Float", "ID", "JSONString"}:
                custom_types.add(output_type)

            line = f'  """{capability["description"]}"""\\n  {field_name}{args}: {output_type}'
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
        """Convert capability name to a GraphQL-safe field name."""
        field = capability_name.replace(".", "_").replace("-", "_")
        field = field.replace("{", "").replace("}", "")
        return field

    @staticmethod
    def _render_args(input_fields: dict[str, Any]) -> str:
        """Render GraphQL arguments from a flat input field mapping."""
        if not input_fields:
            return ""

        arg_parts: list[str] = []
        for name in input_fields.keys():
            safe_name = str(name).replace("-", "_")
            arg_parts.append(f"{safe_name}: JSONString")

        return f"({', '.join(arg_parts)})"


def graphql_query_from_capability(
    capability_name: str,
    arguments: dict[str, Any],
    *,
    operation: str = "mutation",
    selection_set: str = "success data error error_code",
) -> str:
    """Generate a GraphQL operation string from a capability name and arguments."""
    field_name = capability_name.replace(".", "_").replace("-", "_").replace("{", "").replace("}", "")

    variable_defs: list[str] = []
    field_args: list[str] = []

    for key in arguments.keys():
        safe_key = str(key).replace("-", "_")
        variable_defs.append(f"${safe_key}: JSONString")
        field_args.append(f"{safe_key}: ${safe_key}")

    variables_part = f"({', '.join(variable_defs)})" if variable_defs else ""
    args_part = f"({', '.join(field_args)})" if field_args else ""

    return (
        f"{operation} {field_name}{variables_part} {{\n"
        f"  {field_name}{args_part} {{\n"
        f"    {selection_set}\n"
        f"  }}\n"
        f"}}"
    )