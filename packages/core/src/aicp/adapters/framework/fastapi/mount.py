"""Mount AICP on a FastAPI application."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from aicp.adapters.framework.fastapi.mapper import (
    create_discovery_response,
    map_routes_to_capabilities,
)
from aicp.adapters.framework.fastapi.overlay import find_overlay_file, load_overlay, merge_overlay
from aicp.adapters.framework.fastapi.types import AicpConfig


def mount_aicp(
    app: FastAPI,
    config: AicpConfig | None = None,
    config_path: str | Path | None = None,
    **config_kwargs: Any,
) -> AicpConfig:
    """Mount AICP on a FastAPI application.

    This function:
    1. Creates or loads AICP configuration
    2. Inspects FastAPI routes
    3. Maps routes to capabilities
    4. Merges optional overlay
    5. Adds discovery endpoint

    Args:
        app: FastAPI application
        config: AicpConfig object (or None to use defaults)
        config_path: Path to aicp.yaml overlay file
        **config_kwargs: Additional configuration options (used if config is None)

    Returns:
        AicpConfig used for mounting
    """
    # Create base configuration
    if config is None:
        config = AicpConfig(**config_kwargs)

    # Load overlay if provided
    if config_path:
        overlay = load_overlay(config_path)
        if overlay:
            config = merge_overlay(config, overlay)
    else:
        # Try to find overlay in app root
        if hasattr(app, "root_path"):
            overlay_path = find_overlay_file(app.root_path or ".")
            if overlay_path:
                overlay = load_overlay(overlay_path)
                if overlay:
                    config = merge_overlay(config, overlay)

    # Map routes to capabilities
    capabilities = map_routes_to_capabilities(app, config)

    # Store capabilities in app state for discovery
    if not hasattr(app.state, "_aicp_config"):
        app.state._aicp_config = config
    if not hasattr(app.state, "_aicp_capabilities"):
        app.state._aicp_capabilities = capabilities

    # Add discovery endpoint
    if config.enable_discovery:

        @app.get(config.discovery_path)
        async def aicp_discovery():
            return create_discovery_response(
                app.state._aicp_capabilities,
                config,
            )

    return config


def get_aicp_config(app: FastAPI) -> AicpConfig | None:
    """Get AICP configuration from a mounted FastAPI app.

    Args:
        app: FastAPI application

    Returns:
        AicpConfig or None if not mounted
    """
    if hasattr(app.state, "_aicp_config"):
        return app.state._aicp_config
    return None


def get_aicp_capabilities(app: FastAPI) -> list:
    """Get AICP capabilities from a mounted FastAPI app.

    Args:
        app: FastAPI application

    Returns:
        List of capabilities or empty list if not mounted
    """
    if hasattr(app.state, "_aicp_capabilities"):
        return app.state._aicp_capabilities
    return []
