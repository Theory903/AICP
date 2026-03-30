"""Compatibility wrapper for FastAPI overlay helpers.

This module preserves the old import path while delegating to the
FastAPI adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_fastapi.overlay import (
        find_overlay_file,
        load_overlay,
        merge_overlay,
    )
except ImportError as exc:  # pragma: no cover
    def _missing_adapter(*args, **kwargs):
        raise RuntimeError(
            "FastAPI overlay helpers are not available. "
            "Install the FastAPI adapter package to use these helpers."
        ) from exc

    find_overlay_file = _missing_adapter
    load_overlay = _missing_adapter
    merge_overlay = _missing_adapter


__all__ = [
    "find_overlay_file",
    "load_overlay",
    "merge_overlay",
]
