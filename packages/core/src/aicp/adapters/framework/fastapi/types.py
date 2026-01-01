"""Types for FastAPI adapter."""

from typing import Any

from pydantic import BaseModel


class RouteMapping(BaseModel):
    """Maps a FastAPI route to an AICP capability."""

    route_path: str
    method: str = "POST"
    capability_name: str
    description: str = ""
    kind: str = "action"
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}


class AicpConfig(BaseModel):
    """Configuration for AICP on a FastAPI app."""

    version: str = "0.1.0"
    provider_name: str = "fastapi"
    provider_url: str | None = None

    route_mappings: list[RouteMapping] = []

    exclude_routes: list[str] = ["/docs", "/openapi.json", "/redoc", "/health"]
    route_prefix: str = ""

    enable_discovery: bool = True
    discovery_path: str = "/.well-known/aicp"

    default_render_format: str = "json"
    default_continuation_hint: str | None = None
