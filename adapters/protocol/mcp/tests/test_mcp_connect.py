"""Tests for the Connect MCP adapter package."""

import pytest

from aicp_connect_mcp import McpAdapter


@pytest.mark.asyncio
async def test_mcp_adapter_discovers_capabilities_with_provider_metadata(monkeypatch) -> None:
    adapter = McpAdapter(
        name="demo-mcp",
        mcp_config={"mcpServers": {"filesystem": {"transport": "stdio"}}},
    )

    async def fake_list_tools(server_name, config):
        assert server_name == "filesystem"
        return [
            {
                "name": "read_file",
                "description": "Read a file",
                "inputSchema": {"properties": {"path": {"type": "string"}}},
            }
        ]

    monkeypatch.setattr(adapter, "_list_tools", fake_list_tools)

    capabilities = await adapter.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.name == "filesystem.read_file"
    assert capability.provider is not None
    assert capability.provider.name == "demo-mcp"
    assert capability.provider.type == "mcp"


@pytest.mark.asyncio
async def test_mcp_adapter_executes_server_tool(monkeypatch) -> None:
    adapter = McpAdapter(
        name="demo-mcp",
        mcp_config={"mcpServers": {"filesystem": {"transport": "stdio"}}},
    )

    async def fake_call_tool(server_name, config, tool_name, arguments):
        return {"server": server_name, "tool": tool_name, "arguments": arguments}

    monkeypatch.setattr(adapter, "_call_tool", fake_call_tool)

    result = await adapter.execute("filesystem.read_file", {"path": "README.md"})

    assert result["server"] == "filesystem"
    assert result["tool"] == "read_file"
    assert result["arguments"]["path"] == "README.md"


@pytest.mark.asyncio
async def test_core_mcp_import_is_backed_by_connect_package(monkeypatch) -> None:
    from aicp.adapters.protocol.mcp import McpAdapter as CoreMcpAdapter

    adapter = CoreMcpAdapter(
        name="demo-mcp",
        mcp_config={"mcpServers": {"memory": {"transport": "stdio"}}},
    )

    async def fake_list_tools(server_name, config):
        return [{"name": "search", "description": "Search memory", "inputSchema": {"properties": {}}}]

    monkeypatch.setattr(adapter, "_list_tools", fake_list_tools)
    capabilities = await adapter.discover()

    assert len(capabilities) == 1
    assert capabilities[0].name == "memory.search"
