"""OpenAPI Connect adapter for AICP."""

from __future__ import annotations

from copy import deepcopy
import re
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

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}
ACTION_WORDS = {
    "activate",
    "approve",
    "assign",
    "create",
    "deactivate",
    "delete",
    "follow",
    "get",
    "list",
    "login",
    "promote",
    "publish",
    "register",
    "unassign",
    "unfollow",
    "update",
}
HIGH_IMPACT_ACTIONS = {
    "activate",
    "approve",
    "deactivate",
    "delete",
    "promote",
    "publish",
    "unassign",
    "unfollow",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "in",
    "of",
    "or",
    "the",
    "to",
    "with",
}


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
        self.warnings: list[str] = []

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
        return f"{title} v{version}".strip()

    async def discover(self) -> list[Capability]:
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        self.warnings = []
        capabilities: list[Capability] = []

        for path, path_item in self._spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue

            try:
                resolved_path_item = self._resolve_refs(path_item)
            except Exception as exc:
                self.warnings.append(f"Skipping path {path}: {exc}")
                continue
            path_parameters = resolved_path_item.get("parameters", [])

            for method, operation in resolved_path_item.items():
                if method.lower() not in HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue

                try:
                    capability = self._convert_operation(
                        path=path,
                        method=method,
                        operation=operation,
                        path_parameters=path_parameters,
                    )
                except Exception as exc:
                    self.warnings.append(
                        f"Skipping operation {method.upper()} {path}: {exc}"
                    )
                    continue
                capabilities.append(capability)

                callbacks = operation.get("callbacks")
                if isinstance(callbacks, dict):
                    try:
                        capabilities.extend(
                            self._convert_callbacks(
                                parent_capability=capability.name,
                                callbacks=callbacks,
                            )
                        )
                    except Exception as exc:
                        self.warnings.append(
                            f"Skipping callbacks for {capability.name}: {exc}"
                        )

        self._apply_inferred_continuations(capabilities)
        self._cached_capabilities = capabilities
        return capabilities

    async def refresh(self) -> list[Capability]:
        self._cached_capabilities = None
        return await self.discover()

    def _resolve_base_url(self, operation: dict[str, Any] | None = None) -> str | None:
        if self._base_url_override:
            return self._normalize_provider_url(self._base_url_override)

        if (
            operation
            and isinstance(operation.get("servers"), list)
            and operation["servers"]
        ):
            server = operation["servers"][0]
            if isinstance(server, dict) and server.get("url"):
                return self._normalize_provider_url(server["url"])

        if isinstance(self._spec.get("servers"), list) and self._spec["servers"]:
            server = self._spec["servers"][0]
            if isinstance(server, dict) and server.get("url"):
                return self._normalize_provider_url(server["url"])

        if self._spec_url:
            parsed = urlparse(self._spec_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"

        return None

    def _convert_operation(
        self,
        *,
        path: str,
        method: str,
        operation: dict[str, Any],
        path_parameters: list[dict[str, Any]] | None,
    ) -> Capability:
        operation = self._resolve_refs(operation)

        name = self._make_operation_name(path, method, operation)
        outputs = self._extract_outputs(operation)

        tags = self._normalize_operation_tags(operation, path, method)
        tags.append(f"method:{method.lower()}")
        tags.append(self._infer_risk_tag(method, operation))
        tags.extend(self._extract_security_tags(operation))
        tags.extend(self._extract_header_tags(operation))
        if self._is_destructive_operation(method, operation, name):
            tags.append("destructive")
        if self._is_approval_candidate(method, operation, name):
            tags.append("governance:approval_candidate")
        if operation.get("callbacks"):
            tags.append("has_callbacks")
        if self._has_links(operation):
            tags.append("has_links")
        if operation.get("deprecated"):
            tags.append("deprecated")

        continuation = self._build_continuation(operation)

        capability = Capability(
            name=name,
            description=self._build_description(operation, method, path),
            kind=self._infer_kind(method, operation),
            input_schema=self._extract_inputs(
                path, method, operation, path_parameters or []
            ),
            output_schema=outputs,
            tags=self._dedupe_strings(tags),
            provider=ProviderInfo(
                name=self.source_name,
                type=self.source_type,
                url=self._resolve_base_url(operation),
            ),
            render=RenderSpec(
                format="json" if outputs.type in {"object", "array"} else "text"
            ),
            continuation=continuation,
            deprecated=bool(operation.get("deprecated", False)),
            deprecation_message="Marked deprecated in OpenAPI spec"
            if operation.get("deprecated")
            else None,
        )

        return capability

    def _convert_callbacks(
        self,
        *,
        parent_capability: str,
        callbacks: dict[str, Any],
    ) -> list[Capability]:
        """Convert callback definitions into derived capabilities."""
        results: list[Capability] = []
        resolved_callbacks = self._resolve_refs(callbacks)

        for callback_name, callback_map in resolved_callbacks.items():
            if not isinstance(callback_map, dict):
                continue

            for callback_expr, path_item in callback_map.items():
                if not isinstance(path_item, dict):
                    continue

                for method, operation in path_item.items():
                    if method.lower() not in HTTP_METHODS or not isinstance(
                        operation, dict
                    ):
                        continue

                    callback_operation = deepcopy(operation)
                    callback_operation.setdefault(
                        "summary",
                        f"Callback {callback_name}: {method.upper()} {callback_expr}",
                    )

                    capability = self._convert_operation(
                        path=callback_expr,
                        method=method,
                        operation=callback_operation,
                        path_parameters=[],
                    )

                    capability.name = (
                        callback_operation.get("operationId")
                        or f"{parent_capability}.callback.{callback_name}.{method.lower()}"
                    )
                    capability.tags = self._dedupe_strings(
                        [*capability.tags, "callback", f"callback:{callback_name}"]
                    )

                    results.append(capability)

        return results

    def _infer_kind(self, method: str, operation: dict[str, Any]) -> CapabilityKind:
        if method.lower() == "get":
            return CapabilityKind.QUERY
        if operation.get("x-async") or operation.get("callbacks"):
            return CapabilityKind.ASYNC_ACTION
        return CapabilityKind.ACTION

    def _extract_inputs(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        path_parameters: list[dict[str, Any]],
    ) -> InputSchema:
        properties: dict[str, Any] = {}
        required: list[str] = []

        parameters = self._merge_parameters(
            path_parameters, operation.get("parameters", [])
        )

        for param in parameters:
            name = param.get("name")
            if not name:
                continue

            schema = self._resolve_refs(param.get("schema", {"type": "string"}))
            prop = deepcopy(schema)

            if param.get("description") and "description" not in prop:
                prop["description"] = param["description"]

            if param.get("in"):
                prop["x-location"] = param["in"]

            properties[name] = prop

            if param.get("required", False):
                required.append(name)

        if "requestBody" in operation:
            request_body = self._resolve_refs(operation["requestBody"])
            body_schema = self._extract_content_schema(request_body.get("content"))
            if body_schema:
                body_schema = deepcopy(body_schema)
                body_schema["x-location"] = "body"
                if request_body.get("description") and "description" not in body_schema:
                    body_schema["description"] = request_body["description"]
                properties["body"] = body_schema
                if request_body.get("required", False):
                    required.append("body")

        return InputSchema(
            type="object",
            properties=properties,
            required=self._dedupe_strings(required),
            description=operation.get("description") or operation.get("summary"),
            **{
                "x-aicp-http": {
                    "path": path,
                    "method": method.upper(),
                }
            },
        )

    def _extract_outputs(self, operation: dict[str, Any]) -> OutputSchema:
        responses = self._resolve_refs(operation.get("responses", {}))
        chosen = self._pick_best_response(responses)

        if not chosen:
            return OutputSchema(type="object")

        output_schema = self._extract_content_schema(chosen.get("content")) or {
            "type": "object"
        }
        output_schema = deepcopy(output_schema)

        headers = chosen.get("headers")
        if isinstance(headers, dict) and headers:
            output_schema.setdefault("x-response-headers", {})
            for header_name, header_def in self._resolve_refs(headers).items():
                if not isinstance(header_def, dict):
                    continue
                output_schema["x-response-headers"][header_name] = self._resolve_refs(
                    header_def.get("schema", {"type": "string"})
                )

        return OutputSchema(
            type=output_schema.get("type", "object"),
            properties=output_schema.get("properties", {}),
            description=chosen.get("description"),
            **{
                k: v
                for k, v in output_schema.items()
                if k not in {"type", "properties", "description"}
            },
        )

    def _pick_best_response(self, responses: dict[str, Any]) -> dict[str, Any] | None:
        for code in ("200", "201", "202", "203", "204", "default"):
            response = responses.get(code)
            if isinstance(response, dict):
                return response

        for response in responses.values():
            if isinstance(response, dict):
                return response

        return None

    def _extract_content_schema(
        self, content: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not content or not isinstance(content, dict):
            return None

        resolved_content = self._resolve_refs(content)
        if not isinstance(resolved_content, dict):
            return None

        preferred_media = [
            "application/json",
            "application/*+json",
            "application/xml",
            "text/plain",
        ]

        for media_type in preferred_media:
            if media_type in resolved_content:
                schema = self._extract_media_schema(resolved_content[media_type])
                if schema:
                    return schema

        for media_obj in resolved_content.values():
            schema = self._extract_media_schema(media_obj)
            if schema:
                return schema

        return None

    def _extract_media_schema(
        self, media_obj: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not media_obj or not isinstance(media_obj, dict):
            return None

        resolved_media_obj = self._resolve_refs(media_obj)
        if not isinstance(resolved_media_obj, dict):
            return None

        schema = resolved_media_obj.get("schema")
        if isinstance(schema, dict):
            return self._resolve_refs(schema)

        examples = resolved_media_obj.get("examples")
        if isinstance(examples, dict):
            for ex in examples.values():
                if isinstance(ex, dict) and "value" in ex:
                    return self._infer_schema_from_example(ex["value"])

        if "example" in resolved_media_obj:
            return self._infer_schema_from_example(resolved_media_obj["example"])

        return None

    def _make_operation_name(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> str:
        explicit_name = operation.get("x-aicp-name")
        if explicit_name:
            return self._normalize_capability_name(str(explicit_name))

        operation_id = operation.get("operationId")
        if operation_id:
            normalized = self._normalize_operation_id(str(operation_id))
            if normalized is not None:
                return normalized

        return self._derive_operation_name(path, method, operation)

    def _merge_parameters(
        self,
        path_parameters: list[dict[str, Any]],
        op_parameters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str], dict[str, Any]] = {}

        for param in path_parameters:
            resolved = self._resolve_refs(param)
            key = (str(resolved.get("name", "")), str(resolved.get("in", "")))
            merged[key] = resolved

        for param in op_parameters:
            resolved = self._resolve_refs(param)
            key = (str(resolved.get("name", "")), str(resolved.get("in", "")))
            merged[key] = resolved

        return list(merged.values())

    def _build_continuation(self, operation: dict[str, Any]) -> ContinuationSpec | None:
        linked_ops: list[str] = []

        responses = self._resolve_refs(operation.get("responses", {}))
        for response in responses.values():
            if not isinstance(response, dict):
                continue
            links = response.get("links")
            if not isinstance(links, dict):
                continue

            for _, link_def in links.items():
                resolved = self._resolve_refs(link_def)
                operation_id = resolved.get("operationId")
                if operation_id:
                    linked_ops.append(str(operation_id))

        linked_ops = self._dedupe_strings(linked_ops)
        if not linked_ops:
            return None

        return ContinuationSpec(
            can_continue=True,
            next_capabilities=linked_ops,
            next_hint="Related follow-up operations discovered from OpenAPI links",
        )

    def _apply_inferred_continuations(self, capabilities: list[Capability]) -> None:
        available = {cap.name for cap in capabilities}

        for capability in capabilities:
            if capability.kind == CapabilityKind.QUERY:
                continue
            if capability.continuation is not None:
                continue

            next_capabilities: list[str] = []
            namespace, _, action = capability.name.partition(".")

            for candidate in (f"{namespace}.get", f"{namespace}.list"):
                if candidate in available:
                    next_capabilities.append(candidate)

            related_object = self._related_object_namespace(action)
            if related_object and related_object != namespace:
                for candidate in (f"{related_object}.get", f"{related_object}.list"):
                    if candidate in available:
                        next_capabilities.append(candidate)

            next_capabilities = self._dedupe_strings(next_capabilities)
            if not next_capabilities:
                continue

            capability.continuation = ContinuationSpec(
                can_continue=True,
                next_capabilities=next_capabilities,
                next_hint=self._continuation_hint(action),
            )

    def _has_links(self, operation: dict[str, Any]) -> bool:
        responses = operation.get("responses", {})
        if not isinstance(responses, dict):
            return False

        for response in responses.values():
            if (
                isinstance(response, dict)
                and isinstance(response.get("links"), dict)
                and response["links"]
            ):
                return True
        return False

    def _extract_security_tags(self, operation: dict[str, Any]) -> list[str]:
        schemes = self._spec.get("components", {}).get("securitySchemes", {})
        tags: list[str] = []

        for requirement in operation.get("security", []) or []:
            if not isinstance(requirement, dict):
                continue

            for scheme_name, scopes in requirement.items():
                scheme = self._resolve_refs(schemes.get(scheme_name, {}))
                scheme_type = scheme.get("type")

                if scheme_type == "http" and scheme.get("scheme") == "bearer":
                    tags.append("auth:bearer")
                elif scheme_type == "apiKey":
                    tags.append("auth:api_key")
                elif scheme_type == "oauth2":
                    tags.append("auth:oauth2")
                elif scheme_type:
                    tags.append(f"auth:{scheme_type}")

                if isinstance(scopes, list):
                    for scope in scopes:
                        tags.append(f"scope:{scope}")

        return tags

    def _extract_header_tags(self, operation: dict[str, Any]) -> list[str]:
        tags: list[str] = []

        for param in self._merge_parameters([], operation.get("parameters", [])):
            if param.get("in") == "header" and param.get("name"):
                tags.append(f"header:{str(param['name']).strip().lower()}")

        return tags

    def _resolve_refs(self, node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                if not ref.startswith("#/"):
                    return node
                resolved = self._resolve_ref_path(ref)
                merged = deepcopy(resolved)
                for key, value in node.items():
                    if key != "$ref":
                        merged[key] = self._resolve_refs(value)
                return self._resolve_refs(merged)

            return {k: self._resolve_refs(v) for k, v in node.items()}

        if isinstance(node, list):
            return [self._resolve_refs(item) for item in node]

        return node

    def _resolve_ref_path(self, ref: str) -> Any:
        current: Any = self._spec
        for token in ref[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or token not in current:
                raise ValueError(f"Unresolvable ref: {ref}")
            current = current[token]
        return deepcopy(current)

    def _infer_schema_from_example(self, value: Any) -> dict[str, Any]:
        value_type = self._json_type_from_value(value)

        if value_type == "object":
            assert isinstance(value, dict)
            return {
                "type": "object",
                "properties": {
                    k: self._infer_schema_from_example(v) for k, v in value.items()
                },
                "required": list(value.keys()),
            }

        if value_type == "array":
            assert isinstance(value, list)
            return {
                "type": "array",
                "items": self._infer_schema_from_example(value[0]) if value else {},
            }

        return {"type": value_type}

    def _json_type_from_value(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int) and not isinstance(value, bool):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    def _normalize_provider_url(self, value: Any) -> str | None:
        raw = str(value).strip()
        if not raw:
            return None
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            return raw
        return None

    def _normalize_operation_tags(
        self,
        operation: dict[str, Any],
        path: str,
        method: str,
    ) -> list[str]:
        raw_tags = operation.get("tags") or []
        tags = [self._normalize_tag(tag) for tag in raw_tags if str(tag).strip()]
        if tags:
            return tags

        namespace, _, _ = self._derive_operation_name(
            path, method, operation
        ).partition(".")
        return [self._normalize_tag(namespace)] if namespace else []

    def _normalize_tag(self, value: str) -> str:
        normalized = str(value).strip().lower()
        if ":" in normalized:
            prefix, _, suffix = normalized.partition(":")
            return f"{prefix}:{self._slugify(suffix, separator='-')}"
        return self._slugify(normalized, separator="-")

    def _infer_risk_tag(self, method: str, operation: dict[str, Any]) -> str:
        verb, _ = self._summary_action_parts(operation)
        risk = "low"
        normalized_method = method.lower()

        if normalized_method in {"post", "put", "patch"}:
            risk = "medium"
        if normalized_method == "delete":
            risk = "high"
        if verb in HIGH_IMPACT_ACTIONS and risk == "low":
            risk = "medium"

        return f"risk:{risk}"

    def _is_destructive_operation(
        self, method: str, operation: dict[str, Any], name: str
    ) -> bool:
        verb, _ = self._summary_action_parts(operation)
        return (
            method.lower() == "delete"
            or verb in {"delete", "unassign", "unfollow"}
            or name.endswith(".delete")
        )

    def _is_approval_candidate(
        self, method: str, operation: dict[str, Any], name: str
    ) -> bool:
        verb, _ = self._summary_action_parts(operation)
        return (
            self._is_destructive_operation(method, operation, name)
            or verb in HIGH_IMPACT_ACTIONS
        )

    def _build_description(
        self, operation: dict[str, Any], method: str, path: str
    ) -> str:
        summary = str(operation.get("summary") or "").strip()
        description = str(operation.get("description") or "").strip()
        if summary and description and summary.lower() != description.lower():
            return f"{summary.rstrip('.')}. {description.rstrip('.')} .".replace(
                " .", "."
            )
        if description:
            return description
        if summary:
            return summary
        return f"{method.upper()} {path}"

    def _normalize_operation_id(self, operation_id: str) -> str | None:
        op_id = operation_id.strip()
        if not op_id:
            return None
        if (
            re.search(r"_api_v\d+_", op_id)
            or "__" in op_id
            or re.search(r"_(get|post|put|patch|delete)$", op_id)
        ):
            return None
        return self._normalize_capability_name(op_id)

    def _derive_operation_name(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> str:
        segments = [segment for segment in path.strip("/").split("/") if segment]
        filtered_segments = [
            segment for segment in segments if not self._is_api_prefix_segment(segment)
        ]
        static_segments = [
            self._normalize_name_segment(segment)
            for segment in filtered_segments
            if not self._is_path_param(segment)
        ]
        namespace = static_segments[0] if static_segments else "root"
        last_static = static_segments[-1] if static_segments else namespace
        has_path_param = any(
            self._is_path_param(segment) for segment in filtered_segments
        )
        tail_is_action = (
            len(static_segments) > 1 and last_static in ACTION_WORDS and has_path_param
        )
        verb, obj = self._summary_action_parts(operation)
        singular_namespace = self._singularize(namespace)

        if method.lower() == "get":
            if tail_is_action:
                action = last_static
            elif len(static_segments) == 1 and has_path_param:
                action = "get"
            elif len(static_segments) > 1 and last_static != namespace:
                action = f"list_{self._pluralize(last_static)}"
            else:
                action = "list"
        elif method.lower() == "post":
            if verb and verb != "create":
                action = (
                    verb if not obj or obj == singular_namespace else f"{verb}_{obj}"
                )
            elif len(static_segments) > 1 and last_static != namespace:
                action = f"create_{self._singularize(last_static)}"
            else:
                action = "create"
        elif method.lower() in {"put", "patch"}:
            if tail_is_action:
                action = last_static
            elif verb and verb != "update":
                action = (
                    verb if not obj or obj == singular_namespace else f"{verb}_{obj}"
                )
            elif len(static_segments) > 1 and last_static != namespace:
                action = f"update_{self._singularize(last_static)}"
            else:
                action = "update"
        elif method.lower() == "delete":
            if tail_is_action:
                action = last_static
            elif verb and verb != "delete":
                action = (
                    verb if not obj or obj == singular_namespace else f"{verb}_{obj}"
                )
            elif len(static_segments) > 1 and last_static != namespace:
                action = f"delete_{self._singularize(last_static)}"
            else:
                action = "delete"
        else:
            action = method.lower()

        return f"{namespace}.{action}"

    def _summary_action_parts(
        self, operation: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        summary = str(operation.get("summary") or "").strip().lower()
        if not summary:
            return None, None

        tokens = [
            self._normalize_name_segment(token)
            for token in re.findall(r"[A-Za-z0-9]+", summary)
        ]
        if not tokens:
            return None, None

        verb = tokens[0] if tokens[0] in ACTION_WORDS else None
        if verb is None:
            return None, None

        object_tokens: list[str] = []
        for token in tokens[1:]:
            if token in STOP_WORDS:
                break
            object_tokens.append(self._singularize(token))

        obj = "_".join(object_tokens) if object_tokens else None
        return verb, obj

    def _normalize_capability_name(self, value: str) -> str:
        parts = [
            self._slugify(part, separator="_")
            for part in str(value).replace("/", ".").split(".")
        ]
        parts = [part for part in parts if part]
        return ".".join(parts)

    def _normalize_name_segment(self, value: str) -> str:
        raw = value.strip("{}")
        return self._slugify(raw, separator="_")

    def _slugify(self, value: str, *, separator: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", separator, str(value).strip().lower())
        cleaned = re.sub(rf"{re.escape(separator)}+", separator, cleaned)
        return cleaned.strip(separator)

    def _pluralize(self, value: str) -> str:
        if value.endswith("s"):
            return value
        if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
            return f"{value[:-1]}ies"
        return f"{value}s"

    def _singularize(self, value: str) -> str:
        if value.endswith("ies") and len(value) > 3:
            return f"{value[:-3]}y"
        if value.endswith("s") and not value.endswith("ss"):
            return value[:-1]
        return value

    def _is_path_param(self, segment: str) -> bool:
        return segment.startswith("{") and segment.endswith("}")

    def _is_api_prefix_segment(self, segment: str) -> bool:
        normalized = segment.strip().lower()
        return normalized == "api" or re.fullmatch(r"v\d+", normalized) is not None

    def _related_object_namespace(self, action: str) -> str | None:
        if "_" not in action:
            return None
        obj = action.split("_", 1)[1]
        if not obj:
            return None
        return self._pluralize(obj)

    def _continuation_hint(self, action: str) -> str:
        if action.startswith("create"):
            return "Review the newly created resource after creation."
        if action.startswith(("update", "activate", "assign", "unassign", "delete")):
            return "Review the updated resource after this action."
        return "Check related resources after this action."


__all__ = ["OpenAPIDiscoverySource"]
