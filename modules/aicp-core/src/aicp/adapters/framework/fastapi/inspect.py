"""Compatibility wrapper for FastAPI inspect helpers.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.inspect import (
        create_default_mapping,
        infer_capability_name,
        inspect_routes,
    )
except ImportError:  # pragma: no cover

    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "FastAPI inspect helpers are not available. Install the FastAPI adapter package to use these helpers."
        )

    inspect_routes = _missing_adapter
    infer_capability_name = _missing_adapter
    create_default_mapping = _missing_adapter


__all__ = [
    "inspect_routes",
    "infer_capability_name",
    "create_default_mapping",
]
