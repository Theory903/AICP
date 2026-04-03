"""Inspect FastAPI routes and extract capability information."""

from __future__ import annotations

from copy import deepcopy
import inspect
from typing import Any, get_args, get_origin

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.params import Depends as DependsMarker
from fastapi.routing import APIRoute
from pydantic import BaseModel

from aicp.risk import infer_risk, is_destructive, risk_to_default_effect


def inspect_routes(app: FastAPI) -> list[dict[str, Any]]:
    openapi_spec = app.openapi()
    routes: list[dict[str, Any]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        if path.startswith("/docs") or path.startswith("/openapi"):
            continue

        methods = _ordered_methods(route.methods)
        if not methods:
            continue

        endpoint = route.endpoint
        func_name = endpoint.__name__
        primary_method = methods[0]
        operation = _get_openapi_operation(openapi_spec, path, primary_method)

        kind = "query" if primary_method == "GET" else "action"
        risk = infer_risk(
            func_name,
            kind=kind,
            http_method=primary_method,
            func_name=func_name,
        )
        destructive = is_destructive(
            func_name,
            http_method=primary_method,
            func_name=func_name,
        )

        routes.append(
            {
                "path": path,
                "methods": methods,
                "func_name": func_name,
                "description": _route_description(endpoint, operation),
                "kind": kind,
                "input_schema": _extract_input_schema(operation, endpoint),
                "output_schema": _extract_output_schema(openapi_spec, route, operation),
                "endpoint": endpoint,
                "risk": risk.value,
                "destructive": destructive,
                "default_effect": risk_to_default_effect(risk),
                "tags": list(route.tags) if getattr(route, "tags", None) else [],
            }
        )

    return routes


def infer_capability_name(route: dict[str, Any]) -> str:
    path = route["path"].strip("/")
    func_name = route["func_name"]

    if path.startswith("api/"):
        path = path[4:]
    if path.startswith("v1/") or path.startswith("v2/"):
        idx = path.find("/")
        if idx > 0:
            path = path[idx + 1 :]

    parts = path.split("/") if path else []
    if not parts:
        return func_name

    name_parts: list[str] = []
    path_params = set()
    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            path_params.add(part[1:-1])
        else:
            name_parts.append(part)

    if not name_parts:
        return func_name

    base = ".".join(name_parts)
    method = route.get("methods", ["GET"])[0]
    if method != "GET":
        if method == "POST":
            base += ".create"
        elif method == "PUT":
            base += ".update"
        elif method == "PATCH":
            base += ".patch"
        elif method == "DELETE":
            base += ".delete"
    else:
        if path_params:
            base += ".get"
        else:
            base += ".list"

    return base


def create_default_mapping(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability_name": infer_capability_name(route),
        "description": route.get("description", ""),
        "kind": route.get("kind", "action"),
        "input_schema": route.get("input_schema", {}),
        "output_schema": route.get("output_schema", {}),
        "risk": route.get("risk", "low"),
        "destructive": route.get("destructive", False),
        "default_effect": route.get("default_effect", "allow"),
        "tags": route.get("tags", []),
    }


def _ordered_methods(methods: set[str] | list[str]) -> list[str]:
    preferred = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE"]
    normalized = {str(method).upper() for method in methods}
    return [method for method in preferred if method in normalized]


def _get_openapi_operation(
    openapi_spec: dict[str, Any], path: str, method: str
) -> dict[str, Any] | None:
    path_item = openapi_spec.get("paths", {}).get(path)
    if not isinstance(path_item, dict):
        return None
    operation = path_item.get(method.lower())
    return operation if isinstance(operation, dict) else None


def _route_description(endpoint: Any, operation: dict[str, Any] | None) -> str:
    if operation:
        if operation.get("description"):
            return str(operation["description"]).strip()
        if operation.get("summary"):
            return str(operation["summary"]).strip()

    description = endpoint.__doc__ or ""
    if description:
        return description.strip().split("\n")[0]
    return ""


def _extract_input_schema(
    operation: dict[str, Any] | None, endpoint: Any
) -> dict[str, Any]:
    if operation:
        schema = _extract_input_schema_from_openapi(operation)
        if schema["properties"]:
            return schema
    return _extract_input_schema_from_signature(endpoint)


def _extract_input_schema_from_openapi(operation: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        if not name:
            continue
        schema = parameter.get("schema") or {"type": "string"}
        resolved = _resolve_openapi_refs(schema, operation)
        prop = deepcopy(resolved if isinstance(resolved, dict) else {"type": "string"})
        if parameter.get("in") is not None:
            prop["x-location"] = str(parameter["in"])
        properties[str(name)] = prop
        if parameter.get("required"):
            required.append(str(name))

    request_body = operation.get("requestBody")
    if isinstance(request_body, dict):
        body_schema = _extract_media_schema(request_body.get("content"), operation)
        if body_schema is not None:
            body_schema = deepcopy(body_schema)
            body_schema["x-location"] = "body"
            properties["body"] = body_schema
            if request_body.get("required"):
                required.append("body")

    return {
        "type": "object",
        "properties": properties,
        "required": required or None,
    }


def _extract_input_schema_from_signature(endpoint: Any) -> dict[str, Any]:
    sig = inspect.signature(endpoint)
    properties: dict[str, Any] = {}
    required: list[str] = []
    body_model: type[BaseModel] | None = None

    for param_name, param in sig.parameters.items():
        if _is_dependency_only_param(param_name, param):
            continue

        annotation = param.annotation
        body_candidate = _extract_body_model(annotation)
        if body_candidate is not None:
            body_model = body_candidate
            continue

        properties[param_name] = {"type": _python_type_to_json_type(annotation)}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    if body_model is not None:
        body_properties: dict[str, Any] = {}
        body_required: list[str] = []
        for field_name, field_info in body_model.model_fields.items():
            body_properties[field_name] = {
                "type": _python_type_to_json_type(field_info.annotation)
            }
            if field_info.is_required():
                body_required.append(field_name)
        properties["body"] = {
            "type": "object",
            "properties": body_properties,
            "required": body_required or None,
            "x-location": "body",
        }
        required.append("body")

    return {
        "type": "object",
        "properties": properties,
        "required": required or None,
    }


def _extract_output_schema(
    openapi_spec: dict[str, Any], route: APIRoute, operation: dict[str, Any] | None
) -> dict[str, Any]:
    if operation:
        responses = operation.get("responses")
        if isinstance(responses, dict):
            for code in ("200", "201", "202", "203", "204", "default"):
                response = responses.get(code)
                if not isinstance(response, dict):
                    continue
                schema = _extract_media_schema(response.get("content"), openapi_spec)
                if schema is not None:
                    return schema

    response_model = getattr(route, "response_model", None)
    model = _extract_body_model(response_model)
    if model is not None:
        return model.model_json_schema()

    return {"type": "object", "properties": {}}


def _extract_media_schema(content: Any, spec: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None

    for media_type in ("application/json", "application/*+json", "text/plain"):
        media = content.get(media_type)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            schema = _resolve_openapi_refs(media["schema"], spec)
            if isinstance(schema, dict):
                return schema

    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            schema = _resolve_openapi_refs(media["schema"], spec)
            if isinstance(schema, dict):
                return schema

    return None


def _resolve_openapi_refs(node: Any, spec: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            if ref.startswith("#/"):
                current: Any = spec
                for token in ref[2:].split("/"):
                    token = token.replace("~1", "/").replace("~0", "~")
                    if not isinstance(current, dict):
                        return node
                    current = current.get(token)
                return _resolve_openapi_refs(current, spec)
        return {key: _resolve_openapi_refs(value, spec) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_openapi_refs(item, spec) for item in node]
    return node


def _extract_body_model(annotation: Any) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list and args:
        return _extract_body_model(args[0])
    if str(origin).endswith("Annotated") and args:
        return _extract_body_model(args[0])
    if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
        return args[0]
    return None


def _is_dependency_only_param(param_name: str, param: inspect.Parameter) -> bool:
    if param_name in {"self", "request", "response", "app", "background_tasks"}:
        return True

    annotation = param.annotation
    if annotation in {Request, Response, BackgroundTasks}:
        return True

    if isinstance(param.default, DependsMarker):
        return True

    origin = get_origin(annotation)
    if str(origin).endswith("Annotated"):
        args = get_args(annotation)
        if args:
            if args[0] in {Request, Response, BackgroundTasks}:
                return True
            if any(isinstance(meta, DependsMarker) for meta in args[1:]):
                return True

    return False


def _python_type_to_json_type(annotation: Any) -> str:
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is list:
        return "array"
    if annotation is dict:
        return "object"
    return "string"
