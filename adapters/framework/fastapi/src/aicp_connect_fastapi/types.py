"""Types for FastAPI Connect adapter."""

from typing import Any

from pydantic import BaseModel, Field


class RouteMapping(BaseModel):
    """Maps a FastAPI route to an AICP capability."""

    route_path: str
    method: str = "POST"
    capability_name: str
    description: str = ""
    kind: str = "action"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AicpConfig(BaseModel):
    """Configuration for AICP on a FastAPI app."""

    version: str = "0.1.0"
    provider_name: str = "fastapi"
    provider_url: str | None = None

    route_mappings: list[RouteMapping] = Field(default_factory=list)

    exclude_routes: list[str] = Field(
        default_factory=lambda: ["/docs", "/openapi.json", "/redoc", "/health"]
    )
    route_prefix: str = ""

    enable_discovery: bool = True
    discovery_path: str = "/.well-known/aicp"

    default_render_format: str = "json"
    default_continuation_hint: str | None = None
