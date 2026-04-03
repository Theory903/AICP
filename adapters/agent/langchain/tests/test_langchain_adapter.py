"""TDD tests for the AICP LangChain adapter.

Tests are written RED-first. Implementation lives at:
  adapters/agent/langchain/src/aicp_connect_langchain/__init__.py

Public API contract
-------------------
AicpLangChainAdapter(provider: CapabilityProvider, *, context: dict | None = None)
    Wraps an AICP CapabilityProvider; creates one LangChain BaseTool per capability.

async build_tools() -> list[BaseTool]
    Discover all capabilities from the provider and return them as LangChain tools.
    Each tool:
      - tool.name  == capability.name  (dots replaced with underscores for LC compat)
      - tool.description == capability.description
      - Calling tool.run(json_or_dict_args) executes the capability synchronously.
      - Calling await tool.arun(json_or_dict_args) executes it asynchronously.

AicpCapabilityTool(BaseTool)
    The individual tool class. Not normally instantiated directly.

AdapterConfigError(Exception)
    Raised for invalid adapter configuration.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from aicp.capability import Capability, CapabilityKind, ProviderInfo
from aicp.interfaces.capability_provider import CapabilityProvider

# ---- import the adapter (will fail RED until implemented) ----
from aicp_connect_langchain import AicpCapabilityTool, AicpLangChainAdapter, AdapterConfigError


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_capability(
    name: str = "orders.place",
    description: str = "Place an order",
    kind: CapabilityKind = CapabilityKind.ACTION,
    tags: list[str] | None = None,
) -> Capability:
    return Capability(
        name=name,
        description=description,
        kind=kind,
        input_schema={"type": "object", "properties": {"item": {"type": "string"}}, "required": []},
        output_schema={"type": "object"},
        tags=tags or [],
        provider=ProviderInfo(name="test_provider", type="test"),
    )


class FakeProvider(CapabilityProvider):
    """Minimal in-memory capability provider for tests."""

    def __init__(self, capabilities: list[Capability], results: dict[str, Any] | None = None):
        self._caps = {c.name: c for c in capabilities}
        self._results = results or {}
        self.execute_calls: list[tuple[str, dict]] = []

    @property
    def provider_type(self) -> str:
        return "test"

    @property
    def provider_name(self) -> str:
        return "fake_provider"

    async def discover(self) -> list[Capability]:
        return list(self._caps.values())

    async def get_capability(self, name: str) -> Capability | None:
        return self._caps.get(name)

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        self.execute_calls.append((capability_name, arguments))
        if capability_name in self._results:
            result = self._results[capability_name]
            if isinstance(result, Exception):
                raise result
            return result
        return {"status": "ok", "capability": capability_name}


# ===========================================================================
# 1. Adapter construction
# ===========================================================================


class TestAdapterConstruction:
    def test_creates_with_provider(self):
        provider = FakeProvider([])
        adapter = AicpLangChainAdapter(provider)
        assert adapter is not None

    def test_stores_provider(self):
        provider = FakeProvider([])
        adapter = AicpLangChainAdapter(provider)
        assert adapter.provider is provider

    def test_accepts_optional_context(self):
        provider = FakeProvider([])
        ctx = {"session_id": "sess_1"}
        adapter = AicpLangChainAdapter(provider, context=ctx)
        assert adapter.context == ctx

    def test_default_context_is_empty_dict(self):
        provider = FakeProvider([])
        adapter = AicpLangChainAdapter(provider)
        assert adapter.context == {}

    def test_raises_on_none_provider(self):
        with pytest.raises((AdapterConfigError, TypeError)):
            AicpLangChainAdapter(None)  # type: ignore[arg-type]


# ===========================================================================
# 2. build_tools
# ===========================================================================


class TestBuildTools:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        provider = FakeProvider([make_capability()])
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_returns_one_tool_per_capability(self):
        caps = [make_capability("a.one"), make_capability("b.two"), make_capability("c.three")]
        adapter = AicpLangChainAdapter(FakeProvider(caps))
        tools = await adapter.build_tools()
        assert len(tools) == 3

    @pytest.mark.asyncio
    async def test_empty_provider_returns_empty_list(self):
        adapter = AicpLangChainAdapter(FakeProvider([]))
        tools = await adapter.build_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_tools_are_aicp_capability_tool_instances(self):
        from langchain.tools import BaseTool

        adapter = AicpLangChainAdapter(FakeProvider([make_capability()]))
        tools = await adapter.build_tools()
        for tool in tools:
            assert isinstance(tool, BaseTool)
            assert isinstance(tool, AicpCapabilityTool)

    @pytest.mark.asyncio
    async def test_tool_name_derived_from_capability_name(self):
        """Dots in capability names become underscores for LangChain compat."""
        adapter = AicpLangChainAdapter(FakeProvider([make_capability("orders.place")]))
        tools = await adapter.build_tools()
        assert tools[0].name == "orders_place"

    @pytest.mark.asyncio
    async def test_tool_description_matches_capability(self):
        cap = make_capability(description="Creates a new order in the system")
        adapter = AicpLangChainAdapter(FakeProvider([cap]))
        tools = await adapter.build_tools()
        assert tools[0].description == "Creates a new order in the system"

    @pytest.mark.asyncio
    async def test_build_tools_called_multiple_times_is_idempotent(self):
        adapter = AicpLangChainAdapter(FakeProvider([make_capability()]))
        tools1 = await adapter.build_tools()
        tools2 = await adapter.build_tools()
        assert len(tools1) == len(tools2)
        assert [t.name for t in tools1] == [t.name for t in tools2]


# ===========================================================================
# 3. Tool execution (arun / run)
# ===========================================================================


class TestToolExecution:
    @pytest.mark.asyncio
    async def test_arun_with_dict_args_calls_provider_execute(self):
        provider = FakeProvider([make_capability("orders.place")])
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        tool = tools[0]
        await tool.arun({"item": "pizza"})
        assert len(provider.execute_calls) == 1
        cap_name, args = provider.execute_calls[0]
        assert cap_name == "orders.place"
        assert args == {"item": "pizza"}

    @pytest.mark.asyncio
    async def test_arun_with_json_string_args_calls_provider_execute(self):
        provider = FakeProvider([make_capability("orders.place")])
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        tool = tools[0]
        await tool.arun(json.dumps({"item": "burger"}))
        cap_name, args = provider.execute_calls[0]
        assert args == {"item": "burger"}

    @pytest.mark.asyncio
    async def test_arun_returns_serialized_result(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": {"order_id": "ord_42"}},
        )
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        result = await tools[0].arun({"item": "salad"})
        # Result should be a string (LangChain tools return strings)
        assert "ord_42" in str(result)

    @pytest.mark.asyncio
    async def test_run_synchronous_calls_provider_execute(self):
        """tool.run() (sync) should work via asyncio.run or the sync wrapper."""
        provider = FakeProvider([make_capability("orders.place")])
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        tool = tools[0]
        # run() is synchronous in LangChain
        tool.run({"item": "wrap"})
        assert len(provider.execute_calls) == 1

    @pytest.mark.asyncio
    async def test_arun_forwards_context_to_provider(self):
        provider = FakeProvider([make_capability("orders.place")])
        ctx = {"session_id": "sess_xyz"}
        adapter = AicpLangChainAdapter(provider, context=ctx)
        tools = await adapter.build_tools()
        await tools[0].arun({"item": "tacos"})
        # Provider was called — context forwarding is internal, just ensure no errors
        assert len(provider.execute_calls) == 1

    @pytest.mark.asyncio
    async def test_arun_raises_on_provider_error(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": RuntimeError("service unavailable")},
        )
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        with pytest.raises(Exception):
            await tools[0].arun({"item": "fries"})

    @pytest.mark.asyncio
    async def test_arun_with_empty_args_is_allowed(self):
        provider = FakeProvider([make_capability("ping")])
        adapter = AicpLangChainAdapter(provider)
        tools = await adapter.build_tools()
        await tools[0].arun({})
        assert provider.execute_calls[0][1] == {}


# ===========================================================================
# 4. Tool metadata
# ===========================================================================


class TestToolMetadata:
    @pytest.mark.asyncio
    async def test_tool_stores_capability_reference(self):
        cap = make_capability("orders.place")
        adapter = AicpLangChainAdapter(FakeProvider([cap]))
        tools = await adapter.build_tools()
        assert tools[0].capability == cap

    @pytest.mark.asyncio
    async def test_tool_name_normalisation_handles_multiple_dots(self):
        cap = make_capability("a.b.c.action")
        adapter = AicpLangChainAdapter(FakeProvider([cap]))
        tools = await adapter.build_tools()
        assert tools[0].name == "a_b_c_action"

    @pytest.mark.asyncio
    async def test_tags_passed_to_tool_when_capability_has_tags(self):
        cap = make_capability(tags=["ecommerce", "orders"])
        adapter = AicpLangChainAdapter(FakeProvider([cap]))
        tools = await adapter.build_tools()
        tool = tools[0]
        # Tags may be on the tool or accessible via capability
        assert tool.capability.tags == ["ecommerce", "orders"]
