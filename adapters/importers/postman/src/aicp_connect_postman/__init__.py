"""Postman collection importer for AICP Connect."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from aicp.capability import (
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    ProviderInfo,
    RenderSpec,
)

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}


class PostmanCollectionImporter:
    """Import Postman collections as AICP capabilities."""

    def __init__(self, name: str, collection: dict[str, Any]):
        self._name = name
        self._collection = collection
        self._cached_capabilities: list[Capability] | None = None

    async def discover(self) -> list[Capability]:
        """Discover capabilities from the collection."""
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        items = self._flatten_items(self._collection.get("item", []))
        capabilities: list[Capability] = []

        for folder_path, item in items:
            capability = self._item_to_capability(item, folder_path)
            if capability is not None:
                capabilities.append(capability)

        capabilities = self._make_capability_names_unique(capabilities)

        self._cached_capabilities = capabilities
        return capabilities

    def _make_capability_names_unique(
        self,
        capabilities: list[Capability],
    ) -> list[Capability]:
        """Ensure discovered capability names are unique and deterministic."""
        counts: dict[str, int] = {}
        unique_capabilities: list[Capability] = []

        for capability in capabilities:
            count = counts.get(capability.name, 0) + 1
            counts[capability.name] = count

            if count == 1:
                unique_capabilities.append(capability)
                continue

            unique_capabilities.append(
                capability.model_copy(update={"name": f"{capability.name}_{count}"})
            )

        return unique_capabilities

    def _flatten_items(
        self,
        items: list[dict[str, Any]],
        folder_path: list[str] | None = None,
    ) -> list[tuple[list[str], dict[str, Any]]]:
        """Flatten nested Postman folders into leaf request items."""
        flattened: list[tuple[list[str], dict[str, Any]]] = []
        current_path = folder_path or []

        for item in items:
            if not isinstance(item, dict):
                continue

            if "request" in item:
                flattened.append((current_path, item))
                continue

            child_items = item.get("item")
            if isinstance(child_items, list):
                folder_name = str(item.get("name", "")).strip()
                next_path = current_path + ([folder_name] if folder_name else [])
                flattened.extend(self._flatten_items(child_items, next_path))

        return flattened

    def _item_to_capability(
        self,
        item: dict[str, Any],
        folder_path: list[str],
    ) -> Capability | None:
        """Convert a Postman request item into a capability."""
        request = item.get("request")
        if not isinstance(request, dict):
            return None

        method = str(request.get("method", "GET")).upper().strip()
        if method not in HTTP_METHODS:
            return None

        url = self._normalize_url(request.get("url"))
        item_name = str(item.get("name", "")).strip() or "run"

        capability_name = self._build_capability_name(
            method=method,
            url=url,
            item_name=item_name,
            folder_path=folder_path,
        )

        input_schema = self._extract_inputs(request, url)
        output_schema = self._extract_outputs(item)
        kind = self._infer_kind(method, capability_name)

        tags = [
            "postman",
            f"method:{method.lower()}",
            *[f"folder:{self._slugify(part)}" for part in folder_path if part.strip()],
        ]
        tags.extend(self._extract_request_tags(request))
        if self._is_destructive(method, capability_name):
            tags.append("destructive")

        description = self._build_description(item, request)

        provider = ProviderInfo(
            name=self._name,
            type="postman",
            url=self._extract_base_url(url),
        )

        render = RenderSpec(
            format="json" if output_schema.type in {"object", "array"} else "text"
        )

        return Capability(
            name=capability_name,
            description=description,
            kind=kind,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=self._dedupe_strings(tags),
            provider=provider,
            render=render,
        )

    def _normalize_url(self, url: Any) -> dict[str, Any]:
        """Normalize Postman URL into a dict shape."""
        if isinstance(url, str):
            return {"raw": url}

        if isinstance(url, dict):
            return deepcopy(url)

        return {}

    def _build_capability_name(
        self,
        *,
        method: str,
        url: dict[str, Any],
        item_name: str,
        folder_path: list[str],
    ) -> str:
        """Build a stable capability name."""
        path_parts = self._extract_path_parts(url)

        normalized_path_parts: list[str] = []
        for part in path_parts:
            if self._is_path_variable(part):
                normalized_path_parts.append(self._slugify(part.lstrip(":")))
            else:
                normalized_path_parts.append(self._slugify(part))

        if normalized_path_parts:
            base_name = ".".join(part for part in normalized_path_parts if part)
        elif folder_path:
            base_name = ".".join(
                self._slugify(part) for part in folder_path if part.strip()
            )
        else:
            base_name = "api"

        leaf_name = self._slugify(item_name)
        method_name = method.lower()

        # Avoid silly duplication like pets.list_pets.list_pets
        if leaf_name and not base_name.endswith(leaf_name):
            return f"{base_name}.{leaf_name}"

        return f"{base_name}.{method_name}"

    def _extract_inputs(
        self, request: dict[str, Any], url: dict[str, Any]
    ) -> InputSchema:
        """Extract input schema from Postman request."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for variable in self._extract_url_variables(url):
            key = variable["key"]
            properties[key] = {
                "type": "string",
                "description": variable.get("description"),
                "x-location": "path",
            }
            if variable.get("required", True):
                required.append(key)

        for query in self._extract_query_params(url):
            key = query["key"]
            prop = {
                "type": self._infer_type_from_placeholder(query.get("value")),
                "description": query.get("description"),
                "x-location": "query",
            }
            if "enum" in query:
                prop["enum"] = query["enum"]
            properties[key] = prop
            if query.get("required", False):
                required.append(key)

        for header in request.get("header", []) or []:
            if not isinstance(header, dict):
                continue
            key = str(header.get("key", "")).strip()
            if not key:
                continue
            properties[f"header_{self._slugify(key)}"] = {
                "type": self._infer_type_from_placeholder(header.get("value")),
                "description": header.get("description"),
                "x-location": "header",
                "x-header-name": key,
            }

        body = request.get("body")
        if isinstance(body, dict):
            body_properties, body_required = self._extract_body_schema(body)
            for key, value in body_properties.items():
                properties[key] = value
            required.extend(body_required)

        return InputSchema(
            type="object",
            properties=properties,
            required=list(dict.fromkeys(required)),
            description=str(request.get("description", "")).strip() or None,
        )

    def _extract_body_schema(
        self, body: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        """Extract body schema by Postman body mode."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        mode = str(body.get("mode", "")).strip()

        if mode == "raw":
            raw = body.get("raw")
            body_schema = self._schema_from_raw_payload(raw)
            if body_schema is not None:
                body_schema["x-location"] = "body"
                body_schema["x-body-mode"] = "raw"
                properties["body"] = body_schema
                required.append("body")
            return properties, required

        if mode == "formdata":
            schema = {
                "type": "object",
                "properties": {},
                "x-location": "body",
                "x-body-mode": "formdata",
            }
            for field in body.get("formdata", []) or []:
                if not isinstance(field, dict):
                    continue
                key = str(field.get("key", "")).strip()
                if not key or field.get("disabled"):
                    continue

                field_type = str(field.get("type", "text")).strip().lower()
                prop: dict[str, Any] = {
                    "description": field.get("description"),
                }

                if field_type == "file":
                    prop["type"] = "string"
                    prop["format"] = "binary"
                else:
                    prop["type"] = self._infer_type_from_placeholder(field.get("value"))

                schema["properties"][key] = prop
                if not field.get("disabled", False):
                    required.append(f"body.{key}")

            properties["body"] = schema
            return properties, required

        if mode == "urlencoded":
            schema = {
                "type": "object",
                "properties": {},
                "x-location": "body",
                "x-body-mode": "urlencoded",
            }
            for field in body.get("urlencoded", []) or []:
                if not isinstance(field, dict):
                    continue
                key = str(field.get("key", "")).strip()
                if not key or field.get("disabled"):
                    continue
                schema["properties"][key] = {
                    "type": self._infer_type_from_placeholder(field.get("value")),
                    "description": field.get("description"),
                }
                required.append(f"body.{key}")

            properties["body"] = schema
            return properties, required

        if mode == "graphql":
            graphql = body.get("graphql", {})
            schema = {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "variables": {"type": "object"},
                },
                "x-location": "body",
                "x-body-mode": "graphql",
            }
            if isinstance(graphql, dict):
                if graphql.get("query"):
                    schema["properties"]["query"]["example"] = graphql.get("query")
                if graphql.get("variables"):
                    schema["properties"]["variables"] = self._schema_from_unknown(
                        graphql.get("variables")
                    )
            properties["body"] = schema
            required.append("body")
            return properties, required

        if mode == "file":
            properties["body"] = {
                "type": "string",
                "format": "binary",
                "x-location": "body",
                "x-body-mode": "file",
            }
            required.append("body")
            return properties, required

        return properties, required

    def _extract_outputs(self, item: dict[str, Any]) -> OutputSchema:
        """Infer output schema from saved Postman responses."""
        responses = item.get("response", [])
        if not isinstance(responses, list) or not responses:
            return OutputSchema(type="object", properties={})

        preferred = self._pick_best_response(responses)
        body = preferred.get("body") if isinstance(preferred, dict) else None
        inferred = self._schema_from_raw_payload(body)

        if inferred is None:
            return OutputSchema(type="object", properties={})

        return OutputSchema(
            type=inferred.get("type", "object"),
            properties=inferred.get("properties", {}),
            description=str(preferred.get("name", "")).strip() or None,
            **{
                k: v
                for k, v in inferred.items()
                if k not in {"type", "properties", "description"}
            },
        )

    def _pick_best_response(self, responses: list[dict[str, Any]]) -> dict[str, Any]:
        """Pick the most useful saved response."""
        ordered_codes = [200, 201, 202, 203, 204]
        by_code: dict[int, dict[str, Any]] = {}

        for response in responses:
            if not isinstance(response, dict):
                continue
            code = response.get("code")
            if isinstance(code, int) and code not in by_code:
                by_code[code] = response

        for code in ordered_codes:
            if code in by_code:
                return by_code[code]

        for response in responses:
            if isinstance(response, dict):
                return response

        return {}

    def _build_description(self, item: dict[str, Any], request: dict[str, Any]) -> str:
        """Build a description from item/request metadata."""
        request_description = request.get("description")
        if isinstance(request_description, str) and request_description.strip():
            return request_description.strip()

        item_description = item.get("description")
        if isinstance(item_description, str) and item_description.strip():
            return item_description.strip()

        return str(item.get("name", "")).strip()

    def _extract_request_tags(self, request: dict[str, Any]) -> list[str]:
        """Extract auth/header/body metadata as tags."""
        tags: list[str] = []

        auth = request.get("auth") or {}
        if isinstance(auth, dict):
            auth_type = str(auth.get("type", "")).strip().lower()
            if auth_type:
                if auth_type == "apikey":
                    tags.append("auth:api_key")
                else:
                    tags.append(f"auth:{auth_type}")

                if auth_type == "oauth2":
                    tags.extend(self._extract_oauth2_scope_tags(auth))
                elif auth_type == "bearer":
                    tags.append("auth:token")
                elif auth_type == "basic":
                    tags.append("auth:username_password")

        for header in request.get("header", []) or []:
            if not isinstance(header, dict):
                continue
            key = str(header.get("key", "")).strip().lower()
            if key:
                tags.append(f"header:{key}")

        body = request.get("body")
        if isinstance(body, dict):
            mode = str(body.get("mode", "")).strip().lower()
            if mode:
                tags.append(f"body:{mode}")

        return tags

    def _extract_oauth2_scope_tags(self, auth: dict[str, Any]) -> list[str]:
        """Extract OAuth2 scopes from Postman auth config."""
        tags: list[str] = []
        oauth2 = auth.get("oauth2")

        if not isinstance(oauth2, list):
            return tags

        for entry in oauth2:
            if not isinstance(entry, dict):
                continue
            if entry.get("key") != "scope":
                continue

            value = str(entry.get("value", "")).strip()
            if not value:
                continue

            for scope in value.split():
                cleaned = scope.strip()
                if cleaned:
                    tags.append(f"scope:{cleaned}")

        return tags

    def _extract_path_parts(self, url: dict[str, Any]) -> list[str]:
        """Extract URL path parts."""
        path = url.get("path")
        if isinstance(path, list):
            return [str(part).strip() for part in path if str(part).strip()]

        raw = url.get("raw")
        if isinstance(raw, str) and raw.strip():
            raw = raw.strip()
            raw = re.sub(r"^[a-z]+://[^/]+", "", raw, flags=re.IGNORECASE)
            raw = raw.split("?", 1)[0]
            return [part for part in raw.strip("/").split("/") if part]

        return []

    def _extract_url_variables(self, url: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract path variables from Postman URL."""
        variables: list[dict[str, Any]] = []

        for variable in url.get("variable", []) or []:
            if not isinstance(variable, dict):
                continue
            key = str(variable.get("key", "")).strip()
            if not key:
                continue
            variables.append(
                {
                    "key": key,
                    "description": variable.get("description"),
                    "required": True,
                }
            )

        if variables:
            return variables

        for part in self._extract_path_parts(url):
            if self._is_path_variable(part):
                variables.append(
                    {
                        "key": part.lstrip(":"),
                        "description": None,
                        "required": True,
                    }
                )

        return variables

    def _extract_query_params(self, url: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract query params from Postman URL."""
        queries: list[dict[str, Any]] = []

        for query in url.get("query", []) or []:
            if not isinstance(query, dict):
                continue
            key = str(query.get("key", "")).strip()
            if not key or query.get("disabled"):
                continue
            queries.append(
                {
                    "key": key,
                    "value": query.get("value"),
                    "description": query.get("description"),
                    "required": bool(query.get("disabled", False)) is False
                    and bool(query.get("required", False)),
                }
            )

        return queries

    def _extract_base_url(self, url: dict[str, Any]) -> str | None:
        """Extract a rough base URL if present."""
        raw = url.get("raw")
        if not isinstance(raw, str) or not raw.strip():
            return None

        raw = raw.strip()
        if raw.startswith("{{"):
            return None

        match = re.match(r"^(https?://[^/]+)", raw, flags=re.IGNORECASE)
        return match.group(1) if match else None

    def _schema_from_raw_payload(self, raw: Any) -> dict[str, Any] | None:
        """Infer schema from raw request/response payload."""
        if raw is None:
            return None

        if isinstance(raw, (dict, list)):
            return self._schema_from_unknown(raw)

        if not isinstance(raw, str):
            return {"type": "string"}

        raw = raw.strip()
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"type": "string"}

        return self._schema_from_unknown(parsed)

    def _schema_from_unknown(self, value: Any) -> dict[str, Any]:
        """Infer schema recursively from arbitrary data."""
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

    def _infer_kind(self, method: str, capability_name: str) -> CapabilityKind:
        """Infer capability kind."""
        if method == "GET":
            return CapabilityKind.QUERY

        if method == "DELETE":
            return CapabilityKind.ACTION

        if "batch" in capability_name or "bulk" in capability_name:
            return CapabilityKind.BATCH_ACTION

        return CapabilityKind.ACTION

    def _is_destructive(self, method: str, capability_name: str) -> bool:
        """Infer whether a capability is destructive."""
        if method == "DELETE":
            return True

        destructive_terms = {"delete", "remove", "destroy", "purge", "revoke", "clear"}
        lowered = capability_name.lower()
        return any(term in lowered for term in destructive_terms)

    def _is_path_variable(self, value: str) -> bool:
        """Check whether a path segment is a path variable."""
        value = value.strip()
        return value.startswith(":") or (
            value.startswith("{{") and value.endswith("}}")
        )

    def _infer_type_from_placeholder(self, value: Any) -> str:
        """Infer a basic type from placeholder-ish values."""
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

    def _slugify(self, value: str) -> str:
        """Convert text into a capability-safe segment."""
        value = value.strip().lower()
        value = value.replace("{{", "").replace("}}", "")
        value = value.replace(":", "")
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "capability"

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        """Deduplicate strings while preserving order."""
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)

        return result


__all__ = ["PostmanCollectionImporter"]
