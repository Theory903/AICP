"""Compatibility wrapper for FastAPI inspect helpers."""

from aicp_connect_fastapi.inspect import create_default_mapping, infer_capability_name, inspect_routes

__all__ = ["inspect_routes", "infer_capability_name", "create_default_mapping"]
