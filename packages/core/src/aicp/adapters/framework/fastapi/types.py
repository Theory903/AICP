"""Compatibility wrapper for FastAPI adapter types.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.types import AicpConfig, RouteMapping
except ImportError:  # pragma: no cover

    class _MissingType:
        def __init__(self, name: str):
            self.name = name

        def __repr__(self) -> str:
            return f"<{self.name} (not installed)>"

    AicpConfig = _MissingType("AicpConfig")
    RouteMapping = _MissingType("RouteMapping")


__all__ = [
    "AicpConfig",
    "RouteMapping",
]
