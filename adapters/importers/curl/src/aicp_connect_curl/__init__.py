"""cURL importer for AICP Connect."""

import json
import shlex
from typing import Any
from urllib.parse import parse_qs, urlparse

from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema, ProviderInfo


class CurlImporter:
    """Import a cURL command as an AICP capability."""

    def __init__(self, name: str, curl_command: str):
        self._name = name
        self._curl_command = curl_command
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        capability = self._parse_command()
        self._cached_capabilities = [capability]
        return self._cached_capabilities

    def _parse_command(self) -> Capability:
        tokens = shlex.split(self._curl_command)
        method = "GET"
        url = None
        body_text = None
        headers: list[str] = []

        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            if token == "-X" and idx + 1 < len(tokens):
                method = tokens[idx + 1].upper()
                idx += 2
                continue
            if token in {"-d", "--data", "--data-raw"} and idx + 1 < len(tokens):
                body_text = tokens[idx + 1]
                idx += 2
                continue
            if token in {"-H", "--header"} and idx + 1 < len(tokens):
                headers.append(tokens[idx + 1])
                idx += 2
                continue
            if token.startswith("http://") or token.startswith("https://"):
                url = token
            idx += 1

        if url is None:
            raise ValueError("No URL found in cURL command")

        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        resource = path_parts[0] if path_parts else "root"
        if method == "GET":
            suffix = "get" if len(path_parts) > 1 and path_parts[1].isdigit() else "list"
        else:
            suffix = path_parts[-1] if len(path_parts) > 1 else method.lower()
        name = f"{resource}.{suffix}"

        properties: dict[str, Any] = {}
        required: list[str] = []

        for key in parse_qs(parsed.query).keys():
            properties[key] = {"type": "string"}

        if body_text:
            try:
                parsed_body = json.loads(body_text)
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
        tags = ["curl", f"method:{method.lower()}"]
        tags.extend(self._extract_header_tags(headers))
        return Capability(
            name=name,
            description=f"Imported from cURL: {method} {parsed.path}",
            kind=kind,
            input_schema=InputSchema(type="object", properties=properties, required=required),
            output_schema=OutputSchema(type="object", properties={}),
            tags=sorted(set(tags)),
            provider=ProviderInfo(name=self._name, type="curl"),
        )

    def _extract_header_tags(self, headers: list[str]) -> list[str]:
        tags: list[str] = []
        for header in headers:
            if ":" not in header:
                continue
            key, value = header.split(":", 1)
            key = key.strip().lower()
            value = value.strip().lower()
            if not key:
                continue
            tags.append(f"header:{key}")
            if key == "authorization" and value.startswith("bearer "):
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


__all__ = ["CurlImporter"]
