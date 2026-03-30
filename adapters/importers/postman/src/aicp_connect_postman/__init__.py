"""Postman collection importer for AICP Connect."""

import json
import re
from typing import Any

from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema, ProviderInfo


class PostmanCollectionImporter:
    """Import Postman collections as AICP capabilities."""

    def __init__(self, name: str, collection: dict[str, Any]):
        self._name = name
        self._collection = collection
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        items = self._flatten_items(self._collection.get("item", []))
        capabilities = []
        for item in items:
            capability = self._item_to_capability(item)
            if capability is not None:
                capabilities.append(capability)

        self._cached_capabilities = capabilities
        return capabilities

    def _flatten_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flattened = []
        for item in items:
            if "request" in item:
                flattened.append(item)
            elif "item" in item:
                flattened.extend(self._flatten_items(item.get("item", [])))
        return flattened

    def _item_to_capability(self, item: dict[str, Any]) -> Capability | None:
        request = item.get("request")
        if not request:
            return None

        method = request.get("method", "GET").upper()
        url = request.get("url", {})
        path_parts = url.get("path", []) if isinstance(url, dict) else []
        path_params = []
        normalized_parts = []
        for part in path_parts:
            if isinstance(part, str) and part.startswith(":"):
                path_params.append(part[1:])
            else:
                normalized_parts.append(part)

        base_name = ".".join(normalized_parts) if normalized_parts else self._slugify(item.get("name", "capability"))
        capability_name = f"{base_name}.{self._slugify(item.get('name', 'run'))}"

        properties = {param: {"type": "string"} for param in path_params}
        required = list(path_params)

        body = request.get("body", {})
        if body.get("mode") == "raw" and body.get("raw"):
            try:
                parsed = json.loads(body["raw"])
            except json.JSONDecodeError:
                parsed = None
            if parsed is not None:
                properties["body"] = {
                    "type": "object",
                    "properties": {
                        key: {"type": self._json_type(value)} for key, value in parsed.items()
                    },
                }
            else:
                properties["body"] = {"type": "string"}
            required.append("body")

        kind = CapabilityKind.QUERY if method == "GET" else CapabilityKind.ACTION
        tags = ["postman", f"method:{method.lower()}"]
        tags.extend(self._extract_request_tags(request))
        return Capability(
            name=capability_name,
            description=item.get("name", ""),
            kind=kind,
            input_schema=InputSchema(type="object", properties=properties, required=required),
            output_schema=OutputSchema(type="object", properties={}),
            tags=sorted(set(tags)),
            provider=ProviderInfo(name=self._name, type="postman"),
        )

    def _extract_request_tags(self, request: dict[str, Any]) -> list[str]:
        tags: list[str] = []

        auth = request.get("auth") or {}
        auth_type = auth.get("type")
        if auth_type:
            if auth_type == "apikey":
                tags.append("auth:api_key")
            else:
                tags.append(f"auth:{auth_type}")

        for header in request.get("header", []) or []:
            key = header.get("key", "").strip().lower()
            if key:
                tags.append(f"header:{key}")

        return tags

    def _slugify(self, value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "capability"

    def _json_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"


__all__ = ["PostmanCollectionImporter"]
