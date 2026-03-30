"""Compatibility wrapper for FastAPI adapter mapping."""

from aicp_connect_fastapi.mapper import create_discovery_response, map_routes_to_capabilities

__all__ = ["map_routes_to_capabilities", "create_discovery_response"]
