"""Compatibility wrapper for the Connect FastAPI adapter.

This module preserves the old import path while delegating to the
FastAPI adapter package. If the adapter is not installed, the imports
will fail with a clear error message.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi import AicpConfig, RouteMapping, mount_aicp
except ImportError:  # pragma: no cover
    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "FastAPI adapter is not installed. "
            "Install the FastAPI adapter package to use these helpers."
        )

    mount_aicp = _missing_adapter
    AicpConfig = _missing_adapter
    RouteMapping = _missing_adapter


__all__ = [
    "mount_aicp",
    "AicpConfig",
    "RouteMapping",
]
