"""OpenAPI Connect adapter for AICP."""

from typing import Any
from urllib.parse import urlparse

from aicp.capability import (
    Capability,
    CapabilityKind,
    ContinuationSpec,
    InputSchema,
    OutputSchema,
    ProviderInfo,
    RenderSpec,
)
from aicp.interfaces.discovery_source import DiscoverySource


class OpenAPIDiscoverySource(DiscoverySource):
    """Discover AICP capabilities from OpenAPI specifications."""

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
        base_url = self._resolve_base_url()

        for path, path_item in self._spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                    continue

                capability = self._convert_operation(path, method, operation, base_url)
                if capability is not None:
                    capabilities.append(capability)

        self._cached_capabilities = capabilities
        return capabilities

    async def refresh(self) -> list[Capability]:
        self._cached_capabilities = None
        return await self.discover()

    def _resolve_base_url(self) -> str:
        if self._base_url_override:
            return self._base_url_override
        if self._spec.get("servers"):
            return self._spec["servers"][0].get("url", "/")
        if self._spec_url:
            parsed = urlparse(self._spec_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return "/"

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

        outputs = self._extract_outputs(operation)
        tags = [*operation.get("tags", []), f"method:{method.lower()}"]
        tags.extend(self._extract_security_tags(operation))
        tags.extend(self._extract_header_tags(operation))

        return Capability(
            name=operation_id,
            description=operation.get("summary") or operation.get("description", ""),
            kind=self._infer_kind(method, operation),
            input_schema=self._extract_inputs(path, operation),
            output_schema=outputs,
            tags=sorted(set(tags)),
            provider=ProviderInfo(name=self.source_name, type=self.source_type, url=base_url),
            render=RenderSpec(format="json" if outputs.type == "object" else "text"),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=self._suggest_continuations(operation),
            ),
        )

    def _infer_kind(self, method: str, operation: dict[str, Any]) -> CapabilityKind:
        if method.lower() == "get":
            return CapabilityKind.QUERY
        if operation.get("x-async") or operation.get("callbacks"):
            return CapabilityKind.ASYNC_ACTION
        return CapabilityKind.ACTION

    def _extract_inputs(self, path: str, operation: dict[str, Any]) -> InputSchema:
        del path
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in operation.get("parameters", []):
            name = param.get("name")
            schema = param.get("schema", {})
            if name:
                properties[name] = {
                    "type": schema.get("type", param.get("type", "string")),
                    "description": param.get("description", ""),
                }
                if param.get("required", False):
                    required.append(name)

        if "requestBody" in operation:
            content = operation["requestBody"].get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
            if schema:
                properties["body"] = schema
                if operation["requestBody"].get("required", True):
                    required.append("body")

        return InputSchema(type="object", properties=properties, required=required)

    def _extract_outputs(self, operation: dict[str, Any]) -> OutputSchema:
        responses = operation.get("responses", {})
        success = responses.get("200") or responses.get("201") or responses.get("default")
        if not success:
            return OutputSchema(type="object")

        if "content" in success:
            content = success.get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
        elif "schema" in success:
            schema = success.get("schema", {})
        else:
            schema = {}

        return OutputSchema(
            type=schema.get("type", "object"),
            properties=schema.get("properties", {}),
        )

    def _suggest_continuations(self, operation: dict[str, Any]) -> list[str]:
        del operation
        return []

    def _extract_security_tags(self, operation: dict[str, Any]) -> list[str]:
        schemes = self._spec.get("components", {}).get("securitySchemes", {})
        tags: list[str] = []
        for requirement in operation.get("security", []) or []:
            for scheme_name in requirement.keys():
                scheme = schemes.get(scheme_name, {})
                scheme_type = scheme.get("type")
                if scheme_type == "http" and scheme.get("scheme") == "bearer":
                    tags.append("auth:bearer")
                elif scheme_type == "apiKey":
                    tags.append("auth:api_key")
        return tags

    def _extract_header_tags(self, operation: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for param in operation.get("parameters", []):
            if param.get("in") == "header" and param.get("name"):
                tags.append(f"header:{param['name'].strip().lower()}")
        return tags


__all__ = ["OpenAPIDiscoverySource"]
