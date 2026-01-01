"""FastAPI framework adapter for AICP.

This module provides tools to automatically expose FastAPI applications
as AICP-capable services with discovery endpoints.
"""

__version__ = "0.1.0"

from aicp.adapters.framework.fastapi.mount import mount_aicp
from aicp.adapters.framework.fastapi.types import AicpConfig, RouteMapping

__all__ = [
    "mount_aicp",
    "AicpConfig",
    "RouteMapping",
]
