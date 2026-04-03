"""MCP Connect adapter for AICP."""

import asyncio
import json
from typing import Any

from aicp.capability import Capability, CapabilityKind, ProviderInfo
from aicp.interfaces.capability_provider import CapabilityProvider


class McpAdapter(CapabilityProvider):
    """Expose MCP tools as AICP capabilities."""

    def __init__(self, name: str, mcp_config: dict[str, Any]):
        self._name = name
        self._config = mcp_config
        self._capabilities: dict[str, Capability] = {}
        self._process: asyncio.subprocess.Process | None = None

    @property
    def provider_type(self) -> str:
        return "mcp"

    @property
    def provider_name(self) -> str:
        return self._name

    async def discover(self) -> list[Capability]:
        if self._capabilities:
            return list(self._capabilities.values())

        servers = self._config.get("mcpServers", {})
        for server_name, server_config in servers.items():
            tools = await self._list_tools(server_name, server_config)
            for tool in tools:
                cap = Capability(
                    name=f"{server_name}.{tool['name']}",
                    description=tool.get("description", ""),
                    kind=CapabilityKind.ACTION,
                    input_schema={
                        "type": "object",
                        "properties": tool.get("inputSchema", {}).get("properties", {}),
                        "required": [],
                    },
                    output_schema={"type": "object", "properties": {}},
                    tags=["mcp", server_name],
                    provider=ProviderInfo(name=self._name, type="mcp"),
                )
                self._capabilities[cap.name] = cap

        return list(self._capabilities.values())

    async def get_capability(self, name: str) -> Capability | None:
        if not self._capabilities:
            await self.discover()
        return self._capabilities.get(name)

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        del context
        parts = capability_name.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid MCP capability name: {capability_name}")

        server_name, tool_name = parts
        servers = self._config.get("mcpServers", {})
        server_config = servers.get(server_name)

        if not server_config:
            raise ValueError(f"MCP server not found: {server_name}")

        return await self._call_tool(server_name, server_config, tool_name, arguments)

    async def _list_tools(self, server_name: str, config: dict[str, Any]) -> list[dict]:
        try:
            result = await self._send_request(server_name, config, "tools/list", {})
            return result.get("tools", [])
        except Exception:
            return []

    async def _call_tool(
        self,
        server_name: str,
        config: dict[str, Any],
        tool_name: str,
        arguments: dict,
    ) -> Any:
        return await self._send_request(
            server_name,
            config,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    async def _send_request(
        self,
        server_name: str,
        config: dict,
        method: str,
        params: dict,
    ) -> dict:
        del server_name
        transport = config.get("transport", "stdio")

        if transport == "stdio":
            return await self._stdio_request(config, method, params)
        if transport == "http":
            return await self._http_request(config, method, params)
        raise ValueError(f"Unsupported MCP transport: {transport}")

    async def _stdio_request(self, config: dict, method: str, params: dict) -> dict:
        if not self._process:
            command = config.get("command", "npx")
            args = config.get("args", [])
            self._process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        request = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        )
        self._process.stdin.write(request.encode() + b"\n")
        await self._process.stdin.drain()

        response_line = await self._process.stdout.readline()
        return json.loads(response_line.decode())

    async def _http_request(self, config: dict, method: str, params: dict) -> dict:
        import aiohttp

        url = config.get("url", "http://localhost:3000")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{url}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            ) as response:
                return await response.json()


__all__ = ["McpAdapter"]
