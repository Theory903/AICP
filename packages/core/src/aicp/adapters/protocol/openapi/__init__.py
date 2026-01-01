"""OpenAPI discovery source.

Converts OpenAPI specifications into AICP capabilities.
This is the highest-value adapter - converts REST APIs to AICP capabilities.
"""

from typing import Any
from urllib.parse import urlparse

from aicp.capability import (
    Capability,
    CapabilityKind,
    ContinuationSpec,
    InputSchema,
    OutputSchema,
    RenderSpec,
)
from aicp.interfaces.discovery_source import DiscoverySource


class OpenAPIDiscoverySource(DiscoverySource):
    """Discovers capabilities from OpenAPI specifications.

    Supports OpenAPI 2.0 and 3.0. Each operation becomes a capability
    with kind inferred from HTTP method.
    """

    def __init__(
        self,
        name: str,
        spec: dict[str, Any],
        spec_url: str | None = None,
        base_url: str | None = None,
    ):
        self._name = name
        self._spec = spec
        self._spec_url = spec_url
        self._base_url_override = base_url
        self._cached_capabilities: list[Capability] | None = None

    @property
    def source_type(self) -> str:
        return "openapi"

    @property
    def source_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        title = self._spec.get("info", {}).get("title", "OpenAPI")
        version = self._spec.get("info", {}).get("version", "")
        return f"{title} v{version}"

    async def discover(self) -> list[Capability]:
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        capabilities = []

        # Determine base URL
        base_url = self._base_url_override
        if not base_url:
            if self._spec.get("servers"):
                base_url = self._spec["servers"][0].get("url", "/")
            elif self._spec_url:
                parsed = urlparse(self._spec_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
            else:
                base_url = "/"

        for path, path_item in self._spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                capability = self._convert_operation(path, method, operation, base_url)
                if capability:
                    capabilities.append(capability)

        self._cached_capabilities = capabilities
        return capabilities

    async def refresh(self) -> list[Capability]:
        self._cached_capabilities = None
        return await self.discover()

    def _convert_operation(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        base_url: str,
    ) -> Capability | None:
        operation_id = operation.get("operationId")
        if not operation_id:
            return None

        # Infer kind from HTTP method
        kind = self._infer_kind(method, operation)

        # Extract input schema
        inputs = self._extract_inputs(path, operation)

        # Extract output schema
        outputs = self._extract_outputs(operation)

        # Extract tags for categorization
        tags = operation.get("tags", [])
        tags.append(f"method:{method.lower()}")

        return Capability(
            name=operation_id,
            description=operation.get("summary") or operation.get("description", ""),
            kind=kind,
            input_schema=inputs,
            output_schema=outputs,
            tags=tags,
            provider_name=self._source_name,
            provider_type=self._source_type,
            render=RenderSpec(format="json" if outputs.type == "object" else "text"),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=self._suggest_continuations(operation),
            ),
        )

    def _infer_kind(self, method: str, operation: dict[str, Any]) -> CapabilityKind:
        """Infer capability kind from HTTP method and operation."""
        method_lower = method.lower()

        if method_lower == "get":
            return CapabilityKind.QUERY

        # Check for async patterns
        if operation.get("x-async") or operation.get("callbacks"):
            return CapabilityKind.ASYNC_ACTION

        return CapabilityKind.ACTION

    def _extract_inputs(self, path: str, operation: dict[str, Any]) -> InputSchema:
        properties = {}
        required = []

        # Path parameters
        for param in operation.get("parameters", []):
            if param.get("in") == "path":
                name = param.get("name")
                if name:
                    properties[name] = {
                        "type": param.get("type", "string"),
                        "description": param.get("description", ""),
                    }
                    if param.get("required", False):
                        required.append(name)

        # Request body (OpenAPI 3.0)
        if "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
            if schema:
                properties["body"] = schema
                required.append("body")

        return InputSchema(
            type="object",
            properties=properties,
            required=required if required else None,
        )

    def _extract_outputs(self, operation: dict[str, Any]) -> OutputSchema:
        responses = operation.get("responses", {})

        # Get success response (200, 201)
        success = responses.get("200") or responses.get("201") or responses.get("default")
        if not success:
            return OutputSchema(type="object")

        # Extract schema from response
        if "content" in success:
            content = success.get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
        elif "schema" in success:  # OpenAPI 2.0
            schema = success.get("schema", {})
        else:
            return OutputSchema(type="object")

        return OutputSchema(
            type=schema.get("type", "object"),
            properties=schema.get("properties", {}),
        )

    def _suggest_continuations(self, operation: dict[str, Any]) -> list[str]:
        """Suggest next capabilities based on operation patterns."""
        suggestions = []

        # GET -> suggest related GETs
        # POST -> suggest GET for created resource
        # etc.

        return suggestions
