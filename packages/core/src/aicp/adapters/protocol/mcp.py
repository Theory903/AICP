"""Compatibility wrapper for the Connect MCP adapter.

This module preserves the old import path while delegating to the
real MCP adapter package.
"""

from __future__ import annotations

try:
    from aicp_connect_mcp import McpAdapter
except ImportError as exc:  # pragma: no cover
    class McpAdapter:  # type: ignore[no-redef]
        """Fallback shim when the MCP adapter package is not installed."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError(
                "MCP adapter support is not available. "
                "Install the MCP adapter package to use McpAdapter."
            ) from exc


__all__ = ["McpAdapter"]