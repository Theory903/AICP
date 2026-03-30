"""Compatibility wrapper for the Connect FastAPI adapter."""

from aicp_connect_fastapi import AicpConfig, RouteMapping, mount_aicp

__all__ = ["mount_aicp", "AicpConfig", "RouteMapping"]
