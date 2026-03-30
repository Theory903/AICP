"""HAR importer for AICP Connect."""

import json
from typing import Any
from urllib.parse import urlparse

from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema, ProviderInfo


class HarImporter:
    """Import HAR sessions as AICP capabilities."""

    def __init__(self, name: str, har: dict[str, Any]):
        self._name = name
        self._har = har
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        by_name: dict[str, Capability] = {}
        entries = self._har.get("log", {}).get("entries", [])
        for entry in entries:
            capability = self._entry_to_capability(entry)
            if capability is None:
                continue
            if capability.name not in by_name:
                by_name[capability.name] = capability
            else:
                existing = by_name[capability.name]
                existing.input_schema.properties.update(capability.input_schema.properties)

        self._cached_capabilities = list(by_name.values())
        return self._cached_capabilities

    def _entry_to_capability(self, entry: dict[str, Any]) -> Capability | None:
        request = entry.get("request") or {}
        method = request.get("method", "GET").upper()
        raw_url = request.get("url")
        if not raw_url:
            return None

        parsed = urlparse(raw_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            name = "root.list" if method == "GET" else "root.call"
        else:
            resource = path_parts[0]
            if method == "GET":
                suffix = "get" if len(path_parts) > 1 and path_parts[1].isdigit() else "list"
            else:
                suffix = path_parts[-1] if len(path_parts) > 1 else method.lower()
            name = f"{resource}.{suffix}"

        properties: dict[str, Any] = {}
        required: list[str] = []

        for query in request.get("queryString", []) or []:
            query_name = query.get("name")
            if query_name:
                properties[query_name] = {"type": "string"}

        post_data = request.get("postData") or {}
        if post_data.get("text"):
            try:
                parsed_body = json.loads(post_data["text"])
            except json.JSONDecodeError:
                parsed_body = None
            if parsed_body is not None:
                properties["body"] = {
                    "type": "object",
                    "properties": {
                        key: {"type": self._json_type(value)} for key, value in parsed_body.items()
                    },
                }
            else:
                properties["body"] = {"type": "string"}
            required.append("body")

        kind = CapabilityKind.QUERY if method == "GET" else CapabilityKind.ACTION
        tags = ["har", f"method:{method.lower()}"]
        tags.extend(self._extract_header_tags(request))
        return Capability(
            name=name,
            description=f"Imported from HAR: {method} {parsed.path}",
            kind=kind,
            input_schema=InputSchema(type="object", properties=properties, required=required),
            output_schema=OutputSchema(type="object", properties={}),
            tags=sorted(set(tags)),
            provider=ProviderInfo(name=self._name, type="har"),
        )

    def _extract_header_tags(self, request: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for header in request.get("headers", []) or []:
            name = header.get("name", "").strip().lower()
            value = header.get("value", "")
            if not name:
                continue
            tags.append(f"header:{name}")
            if name == "authorization" and value.lower().startswith("bearer "):
                tags.append("auth:bearer")
        return tags

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


__all__ = ["HarImporter"]
