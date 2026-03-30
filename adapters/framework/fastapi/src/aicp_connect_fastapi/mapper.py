"""Map FastAPI routes to AICP capabilities."""

from typing import Any

from fastapi import FastAPI

from aicp import Capability, CapabilityKind, ProviderInfo
from aicp_connect_fastapi.inspect import create_default_mapping, inspect_routes
from aicp_connect_fastapi.types import AicpConfig, RouteMapping


def map_routes_to_capabilities(app: FastAPI, config: AicpConfig) -> list[Capability]:
    routes = inspect_routes(app)
    routes = [
        r for r in routes if not any(r["path"].startswith(exc) for exc in config.exclude_routes)
    ]

    capability_mappings = {}
    explicitly_mapped_routes = set()

    for mapping in config.route_mappings:
        capability_mappings[mapping.capability_name] = mapping
        explicitly_mapped_routes.add((mapping.route_path, mapping.method))

    for route in routes:
        route_key = (route["path"], route.get("methods", ["POST"])[0])
        if route_key in explicitly_mapped_routes:
            continue

        default = create_default_mapping(route)
        cap_name = default["capability_name"]
        if cap_name not in capability_mappings:
            capability_mappings[cap_name] = RouteMapping(
                route_path=route["path"],
                method=route.get("methods", ["POST"])[0],
                capability_name=cap_name,
                description=default["description"],
                kind=default["kind"],
                input_schema=default.get("input_schema", {}),
                output_schema=default.get("output_schema", {}),
            )

    capabilities = []
    for mapping in capability_mappings.values():
        kind = CapabilityKind.ACTION
        if mapping.kind == "query":
            kind = CapabilityKind.QUERY
        elif mapping.kind == "workflow":
            kind = CapabilityKind.WORKFLOW
        elif mapping.kind == "async_action":
            kind = CapabilityKind.ASYNC_ACTION

        input_schema = mapping.input_schema or {}
        if "properties" not in input_schema:
            input_schema["properties"] = {}
        if "required" in input_schema and input_schema["required"] is None:
            del input_schema["required"]

        output_schema = mapping.output_schema or {}
        if "properties" not in output_schema:
            output_schema["properties"] = {}

        capability = Capability(
            name=mapping.capability_name,
            description=mapping.description or f"Auto-mapped from {mapping.route_path}",
            kind=kind,
            input_schema=input_schema,
            output_schema=output_schema,
            provider=ProviderInfo(name=config.provider_name, type="fastapi", url=config.provider_url),
        )
        capabilities.append(capability)

    return capabilities


def create_discovery_response(capabilities: list[Capability], config: AicpConfig) -> dict[str, Any]:
    return {
        "version": config.version,
        "capabilities": [cap.model_dump(exclude_none=True, mode="json") for cap in capabilities],
        "policies": [],
        "workflows": [],
        "metadata": {
            "provider_name": config.provider_name,
            "provider_url": config.provider_url,
            "capability_count": len(capabilities),
            "policy_count": 0,
            "workflow_count": 0,
        },
    }
