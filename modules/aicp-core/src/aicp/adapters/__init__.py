"""AICP Adapters.

Protocol, framework, and agent adapters for AICP.

Directory structure:
- protocol/: Protocol adapters (HTTP, MCP, OpenAPI)
- framework/: Framework adapters (FastAPI, Express, etc.)
- agent/: Agent adapters (LangChain, etc.)
"""

# Protocol adapters - with optional dependencies
try:
    from aicp.adapters.protocol.http import AIOHTTP_AVAILABLE, HttpExecutionAdapter

    if not AIOHTTP_AVAILABLE:
        HttpExecutionAdapter = None  # type: ignore
except ImportError:
    HttpExecutionAdapter = None  # type: ignore

try:
    from aicp.adapters.protocol.mcp import McpAdapter
except ImportError:
    McpAdapter = None  # type: ignore

__all__ = [
    "HttpExecutionAdapter",
    "McpAdapter",
]
