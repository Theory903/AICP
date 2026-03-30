"""FastAPI Connect adapter for AICP."""

from aicp_connect_fastapi.mount import mount_aicp
from aicp_connect_fastapi.types import AicpConfig, RouteMapping

__all__ = ["mount_aicp", "AicpConfig", "RouteMapping"]
