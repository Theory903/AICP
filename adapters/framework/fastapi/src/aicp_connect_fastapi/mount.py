"""Mount AICP on a FastAPI application."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from aicp_connect_fastapi.mapper import create_discovery_response, map_routes_to_capabilities
from aicp_connect_fastapi.overlay import find_overlay_file, load_overlay, merge_overlay
from aicp_connect_fastapi.types import AicpConfig


def mount_aicp(
    app: FastAPI,
    config: AicpConfig | None = None,
    config_path: str | Path | None = None,
    **config_kwargs: Any,
) -> AicpConfig:
    if config is None:
        config = AicpConfig(**config_kwargs)

    if config_path:
        overlay = load_overlay(config_path)
        if overlay:
            config = merge_overlay(config, overlay)
    else:
        if hasattr(app, "root_path"):
            overlay_path = find_overlay_file(app.root_path or ".")
            if overlay_path:
                overlay = load_overlay(overlay_path)
                if overlay:
                    config = merge_overlay(config, overlay)

    capabilities = map_routes_to_capabilities(app, config)

    if not hasattr(app.state, "_aicp_config"):
        app.state._aicp_config = config
    if not hasattr(app.state, "_aicp_capabilities"):
        app.state._aicp_capabilities = capabilities

    if config.enable_discovery:

        @app.get(config.discovery_path)
        async def aicp_discovery():
            return create_discovery_response(app.state._aicp_capabilities, config)

    return config


def get_aicp_config(app: FastAPI) -> AicpConfig | None:
    if hasattr(app.state, "_aicp_config"):
        return app.state._aicp_config
    return None


def get_aicp_capabilities(app: FastAPI) -> list:
    if hasattr(app.state, "_aicp_capabilities"):
        return app.state._aicp_capabilities
    return []
