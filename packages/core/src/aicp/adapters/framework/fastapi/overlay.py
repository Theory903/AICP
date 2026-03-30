"""Compatibility wrapper for FastAPI overlay helpers."""

from aicp_connect_fastapi.overlay import find_overlay_file, load_overlay, merge_overlay

__all__ = ["load_overlay", "merge_overlay", "find_overlay_file"]
