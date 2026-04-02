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
    RenderSpec,
)

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
UPLOAD_METHOD_HINTS = {"PUT", "POST"}
DESTRUCTIVE_TERMS = {"delete", "remove", "destroy", "purge", "revoke", "clear"}


@dataclass
class CurlRequest:
    """Parsed cURL request representation."""

    urls: list[str] = field(default_factory=list)
    method: str | None = None
    headers: list[tuple[str, str]] = field(default_factory=list)
    data_fields: list[str] = field(default_factory=list)
    form_fields: list[str] = field(default_factory=list)
    upload_file: str | None = None
    user: str | None = None
    proxy_user: str | None = None
    auth_mode: str | None = None
    proxy: str | None = None
    proxy_mode: str | None = None
    cookie_input: str | None = None
    cookie_output: str | None = None
    user_agent: str | None = None
    referer: str | None = None
    output_file: str | None = None
    remote_name: bool = False
    include_headers: bool = False
    head_only: bool = False
    insecure_tls: bool = False
    interface: str | None = None
    range_value: str | None = None
    limit_rate: str | None = None
    config_file: str | None = None
    follow_redirects: bool = False
    extra_tags: list[str] = field(default_factory=list)


class CurlImporter:
    """Import cURL command(s) as AICP capabilities."""

    def __init__(self, name: str, curl_command: str):
        self._name = name
        self._curl_command = curl_command
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        """Parse the cURL command and convert it into AICP capabilities."""
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        requests = self._parse_command(self._curl_command)
        capabilities: list[Capability] = []

        for index, request in enumerate(requests, start=1):
            for url_index, url in enumerate(request.urls, start=1):
                capability = self._request_to_capability(
                    request=request,
                    url=url,
                    request_index=index,
                    url_index=url_index,
                    multi_request=len(requests) > 1 or len(request.urls) > 1,
                )
                capabilities.append(capability)

        self._cached_capabilities = capabilities
        return capabilities

    def _parse_command(self, command_text: str) -> list[CurlRequest]:
        """Parse a curl command into one or more request specs."""
        tokens = shlex.split(command_text.strip())
        if not tokens:
            raise ValueError("Empty cURL command")

        if tokens[0] != "curl":
            if tokens[0].endswith("/curl") or tokens[0].endswith("\\curl"):
                tokens[0] = "curl"
            else:
                raise ValueError("Command must start with 'curl'")

        request = CurlRequest()
        i = 1

        while i < len(tokens):
            token = tokens[i]

            if token in {"-X", "--request"}:
                i += 1
                request.method = tokens[i].upper()
            elif token in {"-H", "--header"}:
                i += 1
                request.headers.append(self._parse_header(tokens[i]))
            elif token in {
                "-d",
                "--data",
                "--data-raw",
                "--data-binary",
                "--data-urlencode",
            }:
                i += 1
                request.data_fields.append(tokens[i])
            elif token in {"-F", "--form", "--form-string"}:
                i += 1
                request.form_fields.append(tokens[i])
            elif token in {"-T", "--upload-file"}:
                i += 1
                request.upload_file = tokens[i]
            elif token in {"-u", "--user"}:
                i += 1
                request.user = tokens[i]
            elif token in {"-U", "--proxy-user"}:
                i += 1
                request.proxy_user = tokens[i]
            elif token == "--anyauth":
                request.auth_mode = "anyauth"
            elif token == "--basic":
                request.auth_mode = "basic"
            elif token == "--digest":
                request.auth_mode = "digest"
            elif token == "--ntlm":
                request.auth_mode = "ntlm"
            elif token in {"-x", "--proxy"}:
                i += 1
                request.proxy = tokens[i]
                request.proxy_mode = "http"
            elif token == "--proxy1.0":
                i += 1
                request.proxy = tokens[i]
                request.proxy_mode = "http1.0"
            elif token == "--socks4":
                i += 1
                request.proxy = tokens[i]
                request.proxy_mode = "socks4"
            elif token == "--socks5":
                i += 1
                request.proxy = tokens[i]
                request.proxy_mode = "socks5"
            elif token in {"-b", "--cookie"}:
                i += 1
                request.cookie_input = tokens[i]
            elif token in {"-c", "--cookie-jar"}:
                i += 1
                request.cookie_output = tokens[i]
            elif token in {"-A", "--user-agent"}:
                i += 1
                request.user_agent = tokens[i]
            elif token in {"-e", "--referer"}:
                i += 1
                request.referer = tokens[i]
            elif token in {"-o", "--output"}:
                i += 1
                request.output_file = tokens[i]
            elif token in {"-O", "--remote-name"}:
                request.remote_name = True
            elif token in {"-I", "--head"}:
                request.head_only = True
            elif token in {"-i", "--include"}:
                request.include_headers = True
            elif token in {"-L", "--location"}:
                request.follow_redirects = True
            elif token in {"-k", "--insecure"}:
                request.insecure_tls = True
            elif token == "--interface":
                i += 1
                request.interface = tokens[i]
            elif token in {"-r", "--range"}:
                i += 1
                request.range_value = tokens[i]
            elif token in {"--limit-rate"}:
                i += 1
                request.limit_rate = tokens[i]
            elif token in {"-K", "--config"}:
                i += 1
                request.config_file = tokens[i]
            elif token.startswith("-"):
                request.extra_tags.append(self._flag_to_tag(token))
            else:
                if self._looks_like_url(token):
                    request.urls.append(token)
                else:
                    request.extra_tags.append(f"arg:{self._slugify(token)}")

            i += 1

        if not request.urls:
            raise ValueError("No URL found in cURL command")

        if request.head_only and request.method is None:
            request.method = "HEAD"

        if request.method is None:
            request.method = self._infer_method(request)

        return [request]

    def _request_to_capability(
        self,
        *,
        request: CurlRequest,
        url: str,
        request_index: int,
        url_index: int,
        multi_request: bool,
    ) -> Capability:
        """Convert one parsed request + URL into a capability."""
        parsed = urlparse(url)
        method = (request.method or "GET").upper()

        name = self._build_capability_name(
            url=url,
            method=method,
            request_index=request_index,
            url_index=url_index,
            multi_request=multi_request,
        )

        input_schema = self._build_input_schema(request, url)
        output_schema = self._build_output_schema(request, parsed)
        tags = self._build_tags(request, parsed, method, name)

        return Capability(
            name=name,
            description=f"{method} {url}",
            kind=self._infer_kind(method, request, name),
            input_schema=input_schema,
            output_schema=output_schema,
            tags=tags,
            provider=ProviderInfo(
                name=self._name,
                type="curl",
                url=f"{parsed.scheme}://{parsed.netloc}"
                if parsed.scheme and parsed.netloc
                else None,
            ),
            render=RenderSpec(
                format="json" if output_schema.type in {"object", "array"} else "text"
            ),
        )

    def _build_capability_name(
        self,
        *,
        url: str,
        method: str,
        request_index: int,
        url_index: int,
        multi_request: bool,
    ) -> str:
        parsed = urlparse(url)
        path_parts = [
            self._slugify(part) for part in parsed.path.split("/") if part.strip()
        ]
        host_part = (
            self._slugify(parsed.netloc.split("@")[-1].split(":")[0]) or "remote"
        )

        if path_parts:
            base = ".".join([host_part, *path_parts])
        else:
            base = f"{host_part}.root"

        if multi_request:
            return f"{base}.{method.lower()}_{request_index}_{url_index}"

        return f"{base}.{method.lower()}"

    def _build_input_schema(self, request: CurlRequest, url: str) -> InputSchema:
        """Build input schema from parsed cURL flags."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        parsed = urlparse(url)

        for name, _ in parse_qsl(parsed.query, keep_blank_values=True):
            properties[name] = {
                "type": "string",
                "x-location": "query",
            }

        for path_var in self._extract_path_variables(parsed.path):
            properties[path_var] = {
                "type": "string",
                "x-location": "path",
            }
            required.append(path_var)

        for header_name, header_value in request.headers:
            properties[f"header_{self._slugify(header_name)}"] = {
                "type": self._infer_scalar_type(header_value),
                "x-location": "header",
                "x-header-name": header_name,
            }

        if request.user:
            properties["auth_user"] = {
                "type": "string",
                "x-location": "auth",
            }

        if request.proxy_user:
            properties["proxy_auth_user"] = {
                "type": "string",
                "x-location": "proxy_auth",
            }

        if request.data_fields:
            body_schema = self._schema_from_data_fields(request.data_fields)
            body_schema["x-location"] = "body"
            body_schema["x-body-mode"] = "data"
            properties["body"] = body_schema
            required.append("body")

        if request.form_fields:
            body_schema = self._schema_from_form_fields(request.form_fields)
            body_schema["x-location"] = "body"
            body_schema["x-body-mode"] = "form"
            properties["body"] = body_schema
            required.append("body")

        if request.upload_file:
            properties["body"] = {
                "type": "string",
                "format": "binary",
                "x-location": "body",
                "x-body-mode": "upload",
            }
            required.append("body")

        if request.cookie_input:
            properties["cookies"] = {
                "type": "string",
                "x-location": "cookie",
            }

        if request.range_value:
            properties["range"] = {
                "type": "string",
                "x-location": "header",
                "x-header-name": "Range",
            }

        if request.user_agent:
            properties["user_agent"] = {
                "type": "string",
                "x-location": "header",
                "x-header-name": "User-Agent",
            }

        if request.referer:
            properties["referer"] = {
                "type": "string",
                "x-location": "header",
                "x-header-name": "Referer",
            }

        return InputSchema(
            type="object",
            properties=properties,
            required=sorted(set(required)),
            description="Imported from cURL command",
        )

    def _build_output_schema(self, request: CurlRequest, parsed: Any) -> OutputSchema:
        """Build best-effort output schema."""
        properties: dict[str, Any] = {}

        if request.include_headers or request.head_only:
            properties["headers"] = {
                "type": "object",
            }

        if parsed.scheme in {"http", "https"}:
            properties["body"] = {"type": "object"}
        else:
            properties["body"] = {"type": "string"}

        if request.output_file or request.remote_name:
            properties["saved_to_file"] = {"type": "boolean"}

        return OutputSchema(
            type="object",
            properties=properties,
            description="Best-effort output inferred from cURL flags",
        )

    def _build_tags(
        self, request: CurlRequest, parsed: Any, method: str, capability_name: str
    ) -> list[str]:
        """Build capability tags."""
        tags = [
            "curl",
            f"method:{method.lower()}",
            f"scheme:{parsed.scheme or 'unknown'}",
        ]

        if request.auth_mode:
            tags.append(f"auth:{request.auth_mode}")
        elif request.user:
            tags.append("auth:basic")

        if request.proxy:
            tags.append("proxy")
            if request.proxy_mode:
                tags.append(f"proxy:{request.proxy_mode}")

        if request.cookie_input or request.cookie_output:
            tags.append("cookies")

        if request.follow_redirects:
            tags.append("redirects")

        if request.insecure_tls:
            tags.append("tls:insecure")

        if request.head_only:
            tags.append("head_only")

        if request.include_headers:
            tags.append("include_headers")

        if request.output_file or request.remote_name:
            tags.append("downloads")

        if request.upload_file:
            tags.append("uploads")

        if request.form_fields:
            tags.append("body:form")
        elif request.data_fields:
            tags.append("body:data")

        if self._is_destructive(method, capability_name):
            tags.append("destructive")

        tags.extend(request.extra_tags)
        return self._dedupe_strings(tags)

    def _infer_kind(
        self, method: str, request: CurlRequest, capability_name: str
    ) -> CapabilityKind:
        if method == "GET" or method == "HEAD":
            return CapabilityKind.QUERY

        if request.upload_file and method in UPLOAD_METHOD_HINTS:
            return CapabilityKind.ACTION

        if "batch" in capability_name or "bulk" in capability_name:
            return CapabilityKind.BATCH_ACTION

        return CapabilityKind.ACTION

    def _infer_method(self, request: CurlRequest) -> str:
        """Infer HTTP method from curl flags."""
        if request.head_only:
            return "HEAD"
        if request.upload_file:
            return "PUT"
        if request.form_fields or request.data_fields:
            return "POST"
        return "GET"

    def _schema_from_data_fields(self, fields: list[str]) -> dict[str, Any]:
        """Infer schema from -d / --data style flags."""
        if len(fields) == 1:
            payload = fields[0].strip()

            parsed_json = self._try_parse_json(payload)
            if parsed_json is not None:
                return self._schema_from_unknown(parsed_json)

            parsed_pairs = self._try_parse_form_pairs(payload)
            if parsed_pairs is not None:
                return {
                    "type": "object",
                    "properties": {
                        key: {"type": self._infer_scalar_type(value)}
                        for key, value in parsed_pairs.items()
                    },
                    "required": list(parsed_pairs.keys()),
                }

            return {"type": "string"}

        return {
            "type": "array",
            "items": {"type": "string"},
        }

    def _schema_from_form_fields(self, fields: list[str]) -> dict[str, Any]:
        """Infer schema from -F / --form fields."""
        properties: dict[str, Any] = {}

        for field in fields:
            if "=" not in field:
                continue

            key, value = field.split("=", 1)
            key = key.strip()
            value = value.strip()

            prop: dict[str, Any] = {}
            if value.startswith("@"):
                prop["type"] = "string"
                prop["format"] = "binary"
            else:
                prop["type"] = self._infer_scalar_type(value)

            properties[key] = prop

        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }

    def _schema_from_unknown(self, value: Any) -> dict[str, Any]:
        """Infer JSON-schema-ish structure from a Python value."""
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
                "items": self._schema_from_unknown(value[0]),
            }
        if isinstance(value, dict):
            return {
                "type": "object",
                "properties": {
                    str(key): self._schema_from_unknown(item)
                    for key, item in value.items()
                },
                "required": list(value.keys()),
            }
        return {"type": "string"}

    def _try_parse_json(self, value: str) -> Any | None:
        try:
            return json.loads(value)
        except Exception:
            return None

    def _try_parse_form_pairs(self, value: str) -> dict[str, str] | None:
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

    def _extract_path_variables(self, path: str) -> list[str]:
        variables: list[str] = []

        for part in path.split("/"):
            part = part.strip()
            if not part:
                continue
            if part.startswith("{") and part.endswith("}"):
                variables.append(self._slugify(part[1:-1]))
            elif part.startswith(":"):
                variables.append(self._slugify(part[1:]))

        return variables

    def _parse_header(self, value: str) -> tuple[str, str]:
        if ":" not in value:
            return value.strip(), ""
        name, header_value = value.split(":", 1)
        return name.strip(), header_value.strip()

    def _looks_like_url(self, token: str) -> bool:
        return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", token))

    def _is_destructive(self, method: str, capability_name: str) -> bool:
        if method == "DELETE":
            return True
        lowered = capability_name.lower()
        return any(term in lowered for term in DESTRUCTIVE_TERMS)

    def _infer_scalar_type(self, value: Any) -> str:
        if value is None:
            return "string"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int) and not isinstance(value, bool):
            return "integer"
        if isinstance(value, float):
            return "number"

        text = str(value).strip()
        if not text:
            return "string"

        lowered = text.lower()
        if lowered in {"true", "false"}:
            return "boolean"
        if re.fullmatch(r"-?\d+", text):
            return "integer"
        if re.fullmatch(r"-?\d+\.\d+", text):
            return "number"
        return "string"

    def _flag_to_tag(self, flag: str) -> str:
        return f"flag:{self._slugify(flag.lstrip('-'))}"

    def _slugify(self, value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "value"

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result


__all__ = ["CurlImporter"]
