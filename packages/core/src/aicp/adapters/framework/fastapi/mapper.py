"""Compatibility wrapper for FastAPI adapter mapping.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.mapper import (
        create_discovery_response,
        map_routes_to_capabilities,
    )
except ImportError as exc:  # pragma: no cover
    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "FastAPI mapping helpers are not available. "
            "Install the FastAPI adapter package to use these helpers."
        ) from exc

    map_routes_to_capabilities = _missing_adapter
    create_discovery_response = _missing_adapter


__all__ = [
    "map_routes_to_capabilities",
    "create_discovery_response",
]