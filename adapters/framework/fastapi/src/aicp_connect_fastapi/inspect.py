"""Inspect FastAPI routes and extract capability information."""

import inspect
from typing import Any, get_args, get_origin

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel


def inspect_routes(app: FastAPI) -> list[dict[str, Any]]:
    routes = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        methods = list(route.methods)

        if path.startswith("/docs") or path.startswith("/openapi"):
            continue

        endpoint = route.endpoint
        func_name = endpoint.__name__

        description = endpoint.__doc__ or ""
        if description:
            description = description.strip().split("\n")[0]

        sig = inspect.signature(endpoint)
        input_props = {}
        required = []
        body_model = None

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "request", "app"):
                continue

            if param.annotation is not inspect.Parameter.empty:
                annotation = param.annotation

                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    body_model = annotation
                    continue

                origin = get_origin(annotation)
                if origin is not None:
                    args = get_args(annotation)
                    if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                        body_model = args[0]
                        continue

            param_type = "string"
            if param.annotation is not inspect.Parameter.empty:
                annotation = param.annotation
                if annotation is str:
                    param_type = "string"
                elif annotation is int:
                    param_type = "integer"
                elif annotation is float:
                    param_type = "number"
                elif annotation is bool:
                    param_type = "boolean"
                elif annotation is list:
                    param_type = "array"
                elif annotation is dict:
                    param_type = "object"

            input_props[param_name] = {"type": param_type}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        if body_model:
            for field_name, field_info in body_model.model_fields.items():
                field_type = field_info.annotation

                if field_type is str:
                    json_type = "string"
                elif field_type is int:
                    json_type = "integer"
                elif field_type is float:
                    json_type = "number"
                elif field_type is bool:
                    json_type = "boolean"
                elif field_type is list:
                    json_type = "array"
                elif field_type is dict:
                    json_type = "object"
                else:
                    json_type = "string"

                input_props[field_name] = {"type": json_type}

                if field_info.is_required():
                    required.append(field_name)

        kind = "action"
        if "GET" in methods:
            kind = "query"

        routes.append(
            {
                "path": path,
                "methods": methods,
                "func_name": func_name,
                "description": description,
                "kind": kind,
                "input_schema": {
                    "type": "object",
                    "properties": input_props,
                    "required": required if required else None,
                },
                "output_schema": {"type": "object"},
                "endpoint": endpoint,
            }
        )

    return routes


def infer_capability_name(route: dict[str, Any]) -> str:
    path = route["path"]
    func_name = route["func_name"]

    path = path.strip("/")
    if path.startswith("api/"):
        path = path[4:]
    if path.startswith("v1/") or path.startswith("v2/"):
        idx = path.find("/")
        if idx > 0:
            path = path[idx + 1 :]

    parts = path.split("/")
    if not parts or parts[0] == "":
        return func_name

    name_parts = []
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
    }
