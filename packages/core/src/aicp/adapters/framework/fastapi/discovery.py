"""Compatibility wrapper for FastAPI discovery helpers.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.discovery import create_discovery_handler
except ImportError as exc:  # pragma: no cover
    def create_discovery_handler(*args, **kwargs):
        """Raise a clear error when the FastAPI adapter is not installed."""
        raise RuntimeError(
            "FastAPI discovery support is not available. "
            "Install the FastAPI adapter package to use create_discovery_handler()."
        ) from exc


__all__ = ["create_discovery_handler"]