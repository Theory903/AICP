"""Compatibility wrapper for FastAPI mount helpers."""

from aicp_connect_fastapi.mount import get_aicp_capabilities, get_aicp_config, mount_aicp

__all__ = ["mount_aicp", "get_aicp_config", "get_aicp_capabilities"]
