"""Compatibility wrapper for FastAPI mount helpers.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.mount import (
        get_aicp_capabilities,
        get_aicp_config,
        mount_aicp,
    )
except ImportError:  # pragma: no cover
    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "FastAPI mount helpers are not available. "
            "Install the FastAPI adapter package to use these helpers."
        )

    mount_aicp = _missing_adapter
    get_aicp_config = _missing_adapter
    get_aicp_capabilities = _missing_adapter


__all__ = [
    "mount_aicp",
    "get_aicp_config",
    "get_aicp_capabilities",
]
