"""cURL importer for AICP Connect."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlparse

from aicp.capability import (
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    ProviderInfo,
)


@dataclass(slots=True)
class ParsedCurlRequest:
    """Parsed representation of a cURL command."""

    method: str = "GET"
    url: str | None = None
    headers: list[tuple[str, str]] = field(default_factory=list)
    body_text: str | None = None
    form_fields: list[str] = field(default_factory=list)
    auth: str | None = None
    proxy: str | None = None
    output_file: str | None = None
    follow_redirects: bool = False
    insecure: bool = False


class CurlImporter:
    """Import a cURL command as one AICP capability."""

    def __init__(self, name: str, curl_command: str):
        self._name = name
        self._curl_command = curl_command
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        """Parse the configured cURL command into capabilities."""
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        capability = self._parse_command()
        self._cached_capabilities = [capability]
        return self._cached_capabilities

    def _parse_command(self) -> Capability:
        """Parse the curl command and convert it into a capability."""
        tokens = shlex.split(self._curl_command.strip())
        if not tokens:
            raise ValueError("Empty cURL command")
        if tokens[0] != "curl":
            raise ValueError("Command must start with 'curl'")

        parsed = self._parse_tokens(tokens[1:])

        if parsed.url is None:
            raise ValueError("No URL found in cURL command")

        parsed_url = urlparse(parsed.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL in cURL command: {parsed.url}")

        method = self._infer_method(parsed.method, parsed.body_text, parsed.form_fields)
        name = self._build_capability_name(parsed_url, method)
        input_schema = self._build_input_schema(parsed, parsed_url)
        output_schema = self._build_output_schema(parsed, parsed_url)
        tags = self._build_tags(parsed, parsed_url, method)

        kind = (
            CapabilityKind.QUERY if method in {"GET", "HEAD"} else CapabilityKind.ACTION
        )

        return Capability(
            name=name,
            description=f"Imported from cURL: {method} {parsed_url.path or '/'}",
            kind=kind,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=tags,
            provider=ProviderInfo(
                name=self._name,
                type="curl",
                url=f"{parsed_url.scheme}://{parsed_url.netloc}",
            ),
        )

    def _parse_tokens(self, tokens: list[str]) -> ParsedCurlRequest:
        """Parse command-line tokens into a structured request."""
        parsed = ParsedCurlRequest()
        idx = 0

        while idx < len(tokens):
            token = tokens[idx]

            if token in {"-X", "--request"}:
                parsed.method = self._require_value(tokens, idx, token).upper()
                idx += 2
                continue

            if token in {
                "-d",
                "--data",
                "--data-raw",
                "--data-binary",
                "--data-urlencode",
            }:
                parsed.body_text = self._require_value(tokens, idx, token)
                idx += 2
                continue

            if token in {"-F", "--form", "--form-string"}:
                parsed.form_fields.append(self._require_value(tokens, idx, token))
                idx += 2
                continue

            if token in {"-H", "--header"}:
                header = self._require_value(tokens, idx, token)
                parsed.headers.append(self._parse_header(header))
                idx += 2
                continue

            if token in {"-u", "--user"}:
                parsed.auth = self._require_value(tokens, idx, token)
                idx += 2
                continue

            if token in {"-x", "--proxy"}:
                parsed.proxy = self._require_value(tokens, idx, token)
                idx += 2
                continue

            if token in {"-o", "--output"}:
                parsed.output_file = self._require_value(tokens, idx, token)
                idx += 2
                continue

            if token in {"-L", "--location"}:
                parsed.follow_redirects = True
                idx += 1
                continue

            if token in {"-k", "--insecure"}:
                parsed.insecure = True
                idx += 1
                continue

            if self._looks_like_url(token):
                parsed.url = token
                idx += 1
                continue

            idx += 1

        return parsed

    def _build_capability_name(self, parsed_url, method: str) -> str:
        """Build a stable capability name from URL and HTTP method."""
        path_parts = [
            self._slugify(part) for part in parsed_url.path.split("/") if part.strip()
        ]
        host_part = (
            self._slugify(parsed_url.netloc.split("@")[-1].split(":")[0]) or "remote"
        )

        if not path_parts:
            resource = "root"
            action = method.lower()
        else:
            resource = path_parts[0]
            action = self._infer_action_name(path_parts, method)

        return f"{host_part}.{resource}.{action}"

    def _infer_action_name(self, path_parts: list[str], method: str) -> str:
        """Infer a readable action name."""
        if method == "GET":
            if len(path_parts) == 1:
                return "list"
            if self._looks_like_identifier(path_parts[-1]):
                return "get"
            return path_parts[-1]

        if method == "POST":
            if len(path_parts) == 1:
                return "create"
            return path_parts[-1]

        if method in {"PUT", "PATCH"}:
            if self._looks_like_identifier(path_parts[-1]) and len(path_parts) >= 2:
                return f"update_{path_parts[-2]}"
            return f"update_{path_parts[-1]}"

        if method == "DELETE":
            if self._looks_like_identifier(path_parts[-1]) and len(path_parts) >= 2:
                return f"delete_{path_parts[-2]}"
            return f"delete_{path_parts[-1]}"

        return method.lower()

    def _build_input_schema(self, parsed: ParsedCurlRequest, parsed_url) -> InputSchema:
        """Build the capability input schema from parsed request parts."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for key, _value in parse_qsl(parsed_url.query, keep_blank_values=True):
            properties[key] = {
                "type": "string",
                "description": f"Query parameter: {key}",
            }

        path_parts = [part for part in parsed_url.path.split("/") if part.strip()]
        for idx, part in enumerate(path_parts):
            if self._looks_like_identifier(part):
                param_name = f"path_param_{idx + 1}"
                properties[param_name] = {
                    "type": "string",
                    "description": f"Path parameter inferred from segment '{part}'",
                }

        if parsed.headers:
            properties["headers"] = {
                "type": "object",
                "properties": {
                    name: {"type": "string"} for name, _value in parsed.headers
                },
                "description": "Optional request headers",
            }

        if parsed.auth:
            properties["auth"] = {
                "type": "string",
                "description": "Authentication credentials from curl -u/--user",
            }

        if parsed.proxy:
            properties["proxy"] = {
                "type": "string",
                "description": "Proxy server",
            }

        if parsed.form_fields:
            properties["form"] = self._build_form_schema(parsed.form_fields)
            required.append("form")

        elif parsed.body_text is not None:
            body_schema = self._build_body_schema(parsed.body_text)
            properties["body"] = body_schema
            required.append("body")

        return InputSchema(
            type="object",
            properties=properties,
            required=required,
            description="Inputs inferred from cURL command",
        )

    def _build_output_schema(
        self, parsed: ParsedCurlRequest, parsed_url
    ) -> OutputSchema:
        """Build a best-effort output schema."""
        properties: dict[str, Any] = {
            "status_code": {"type": "integer"},
            "body": {
                "type": "object"
                if parsed_url.scheme in {"http", "https"}
                else "string",
            },
        }

        if parsed.output_file:
            properties["saved_to_file"] = {"type": "boolean"}

        return OutputSchema(
            type="object",
            properties=properties,
            description="Best-effort output inferred from cURL command",
        )

    def _build_body_schema(self, body_text: str) -> dict[str, Any]:
        """Infer schema for a request body."""
        parsed_json = self._try_parse_json(body_text)
        if parsed_json is not None:
            return self._schema_from_value(parsed_json)

        parsed_form = self._try_parse_form_urlencoded(body_text)
        if parsed_form is not None:
            return {
                "type": "object",
                "properties": {key: {"type": "string"} for key in parsed_form.keys()},
            }

        return {"type": "string"}

    def _build_form_schema(self, form_fields: list[str]) -> dict[str, Any]:
        """Infer schema for multipart form fields."""
        properties: dict[str, Any] = {}

        for field in form_fields:
            if "=" not in field:
                continue
            key, value = field.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if value.startswith("@"):
                properties[key] = {"type": "string", "format": "binary"}
            else:
                properties[key] = {"type": "string"}

        return {
            "type": "object",
            "properties": properties,
            "description": "Multipart form payload inferred from cURL command",
        }

    def _build_tags(
        self, parsed: ParsedCurlRequest, parsed_url, method: str
    ) -> list[str]:
        """Build tags for the imported capability."""
        tags = [
            "curl",
            f"method:{method.lower()}",
            f"scheme:{parsed_url.scheme.lower()}",
        ]

        if parsed.auth:
            tags.append("auth:basic")

        for header_name, header_value in parsed.headers:
            tags.append(f"header:{header_name.lower()}")
            if (
                header_name.lower() == "authorization"
                and header_value.lower().startswith("bearer ")
            ):
                tags.append("auth:bearer")

        if parsed.follow_redirects:
            tags.append("redirects")

        if parsed.insecure:
            tags.append("tls:insecure")

        if parsed.proxy:
            tags.append("proxy")

        if parsed.form_fields:
            tags.append("body:form")
        elif parsed.body_text is not None:
            tags.append("body:data")

        return sorted(set(tags))

    def _infer_method(
        self, explicit_method: str, body_text: str | None, form_fields: list[str]
    ) -> str:
        """Infer HTTP method from curl flags."""
        method = (explicit_method or "GET").upper()
        if method == "GET" and (body_text is not None or form_fields):
            return "POST"
        return method

    def _parse_header(self, header: str) -> tuple[str, str]:
        """Parse a single header line."""
        if ":" not in header:
            return header.strip(), ""
        key, value = header.split(":", 1)
        return key.strip(), value.strip()

    def _require_value(self, tokens: list[str], idx: int, flag: str) -> str:
        """Require a following token value for a flag."""
        if idx + 1 >= len(tokens):
            raise ValueError(f"Missing value for {flag}")
        return tokens[idx + 1]

    def _looks_like_url(self, token: str) -> bool:
        """Check if a token looks like a URL."""
        return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", token))

    def _looks_like_identifier(self, value: str) -> bool:
        """Heuristic for resource IDs in paths."""
        if value.isdigit():
            return True
        if re.fullmatch(r"[0-9a-fA-F-]{8,}", value):
            return True
        return False

    def _try_parse_json(self, value: str) -> Any | None:
        """Try to parse JSON body text."""
        try:
            return json.loads(value)
        except Exception:
            return None

    def _try_parse_form_urlencoded(self, value: str) -> dict[str, str] | None:
        """Try to parse x-www-form-urlencoded style body text."""
        if "=" not in value:
            return None
        result: dict[str, str] = {}
        for part in value.split("&"):
            if "=" not in part:
                return None
            key, raw_value = part.split("=", 1)
            key = key.strip()
            if not key:
                return None
            result[key] = raw_value
        return result

    def _schema_from_value(self, value: Any) -> dict[str, Any]:
        """Infer a JSON-schema-ish structure from a Python value."""
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "boolean"}
        if isinstance(value, int) and not isinstance(value, bool):
            return {"type": "integer"}
        if isinstance(value, float):
            return {"type": "number"}
        if isinstance(value, str):
            return {"type": "string"}
        if isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}
            return {
                "type": "array",
                "items": self._schema_from_value(value[0]),
            }
        if isinstance(value, dict):
            return {
                "type": "object",
                "properties": {
                    str(key): self._schema_from_value(item)
                    for key, item in value.items()
                },
                "required": list(value.keys()),
            }
        return {"type": "string"}

    def _slugify(self, value: str) -> str:
        """Convert a string into a safe capability segment."""
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "value"


__all__ = ["CurlImporter"]
