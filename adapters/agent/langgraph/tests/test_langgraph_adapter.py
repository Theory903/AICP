"""TDD tests for the AICP LangGraph adapter.

Tests are written RED-first. Implementation lives at:
  adapters/agent/langgraph/src/aicp_connect_langgraph/__init__.py

Public API contract
-------------------
AicpLangGraphAdapter(provider: CapabilityProvider, *, context: dict | None = None)
    Wraps an AICP CapabilityProvider; creates LangGraph-compatible node callables.

async build_nodes() -> dict[str, Callable[[State], Awaitable[dict]]]
    Discover all capabilities and return a dict mapping node_name → async_fn.
    - Node name = capability.name with dots replaced by underscores.
    - Calling node_fn(state) invokes the capability with state["input"] as args,
      and returns {"output": result, "capability": capability_name}.

async build_tool_node() -> Callable
    Returns a single "tool_node" async function that reads state["capability_name"]
    and state["input"] and dispatches to the appropriate capability.

AdapterConfigError(Exception)
    Raised for invalid adapter configuration.
"""

from __future__ import annotations

from typing import Any

import pytest

from aicp.capability import Capability, CapabilityKind, ProviderInfo
from aicp.interfaces.capability_provider import CapabilityProvider

# ---- import the adapter (RED until implemented) ----
from aicp_connect_langgraph import AdapterConfigError, AicpLangGraphAdapter


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_capability(
    name: str = "orders.place",
    description: str = "Place an order",
) -> Capability:
    return Capability(
        name=name,
        description=description,
        kind=CapabilityKind.ACTION,
        input_schema={"type": "object", "properties": {}, "required": []},
        output_schema={"type": "object"},
        tags=[],
        provider=ProviderInfo(name="test", type="test"),
    )


class FakeProvider(CapabilityProvider):
    def __init__(self, capabilities: list[Capability], results: dict[str, Any] | None = None):
        self._caps = {c.name: c for c in capabilities}
        self._results = results or {}
        self.execute_calls: list[tuple[str, dict]] = []

    @property
    def provider_type(self) -> str:
        return "test"

    @property
    def provider_name(self) -> str:
        return "fake"

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
            r = self._results[capability_name]
            if isinstance(r, Exception):
                raise r
            return r
        return {"status": "ok"}


# ===========================================================================
# 1. Adapter construction
# ===========================================================================


class TestAdapterConstruction:
    def test_creates_with_provider(self):
        adapter = AicpLangGraphAdapter(FakeProvider([]))
        assert adapter is not None

    def test_stores_provider(self):
        provider = FakeProvider([])
        adapter = AicpLangGraphAdapter(provider)
        assert adapter.provider is provider

    def test_default_context_is_empty_dict(self):
        adapter = AicpLangGraphAdapter(FakeProvider([]))
        assert adapter.context == {}

    def test_accepts_context(self):
        ctx = {"session_id": "sess_A"}
        adapter = AicpLangGraphAdapter(FakeProvider([]), context=ctx)
        assert adapter.context == ctx

    def test_raises_on_none_provider(self):
        with pytest.raises((AdapterConfigError, TypeError)):
            AicpLangGraphAdapter(None)  # type: ignore[arg-type]


# ===========================================================================
# 2. build_nodes
# ===========================================================================


class TestBuildNodes:
    @pytest.mark.asyncio
    async def test_returns_dict(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability()]))
        nodes = await adapter.build_nodes()
        assert isinstance(nodes, dict)

    @pytest.mark.asyncio
    async def test_one_entry_per_capability(self):
        caps = [make_capability("a.one"), make_capability("b.two")]
        adapter = AicpLangGraphAdapter(FakeProvider(caps))
        nodes = await adapter.build_nodes()
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_empty_provider_returns_empty_dict(self):
        adapter = AicpLangGraphAdapter(FakeProvider([]))
        nodes = await adapter.build_nodes()
        assert nodes == {}

    @pytest.mark.asyncio
    async def test_node_names_use_underscores_for_dots(self):
        cap = make_capability("orders.place")
        adapter = AicpLangGraphAdapter(FakeProvider([cap]))
        nodes = await adapter.build_nodes()
        assert "orders_place" in nodes

    @pytest.mark.asyncio
    async def test_node_names_handle_multiple_dots(self):
        cap = make_capability("a.b.c")
        adapter = AicpLangGraphAdapter(FakeProvider([cap]))
        nodes = await adapter.build_nodes()
        assert "a_b_c" in nodes

    @pytest.mark.asyncio
    async def test_node_values_are_callable(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability()]))
        nodes = await adapter.build_nodes()
        for fn in nodes.values():
            assert callable(fn)

    @pytest.mark.asyncio
    async def test_build_nodes_is_idempotent(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability()]))
        n1 = await adapter.build_nodes()
        n2 = await adapter.build_nodes()
        assert list(n1.keys()) == list(n2.keys())


# ===========================================================================
# 3. Node function behaviour
# ===========================================================================


class TestNodeFunction:
    @pytest.mark.asyncio
    async def test_node_fn_calls_provider_execute(self):
        provider = FakeProvider([make_capability("orders.place")])
        adapter = AicpLangGraphAdapter(provider)
        nodes = await adapter.build_nodes()
        node_fn = nodes["orders_place"]
        state = {"input": {"item": "pizza"}}
        await node_fn(state)
        assert len(provider.execute_calls) == 1
        cap_name, args = provider.execute_calls[0]
        assert cap_name == "orders.place"
        assert args == {"item": "pizza"}

    @pytest.mark.asyncio
    async def test_node_fn_returns_dict_with_output(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": {"order_id": "ord_1"}},
        )
        adapter = AicpLangGraphAdapter(provider)
        nodes = await adapter.build_nodes()
        result = await nodes["orders_place"]({"input": {}})
        assert isinstance(result, dict)
        assert "output" in result

    @pytest.mark.asyncio
    async def test_node_fn_output_contains_capability_result(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": {"order_id": "ord_42"}},
        )
        adapter = AicpLangGraphAdapter(provider)
        nodes = await adapter.build_nodes()
        result = await nodes["orders_place"]({"input": {}})
        assert result["output"] == {"order_id": "ord_42"}

    @pytest.mark.asyncio
    async def test_node_fn_result_includes_capability_name(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability("orders.place")]))
        nodes = await adapter.build_nodes()
        result = await nodes["orders_place"]({"input": {}})
        assert result.get("capability") == "orders.place"

    @pytest.mark.asyncio
    async def test_node_fn_empty_state_uses_empty_args(self):
        """Node called with empty state should pass {} to execute."""
        provider = FakeProvider([make_capability("ping")])
        adapter = AicpLangGraphAdapter(provider)
        nodes = await adapter.build_nodes()
        await nodes["ping"]({})
        assert provider.execute_calls[0][1] == {}

    @pytest.mark.asyncio
    async def test_node_fn_propagates_error_from_provider(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": RuntimeError("failed")},
        )
        adapter = AicpLangGraphAdapter(provider)
        nodes = await adapter.build_nodes()
        with pytest.raises(RuntimeError, match="failed"):
            await nodes["orders_place"]({"input": {}})

    @pytest.mark.asyncio
    async def test_node_fn_forwards_context(self):
        """Context passed to adapter is forwarded to execute."""
        provider = FakeProvider([make_capability("orders.place")])
        ctx = {"session_id": "sess_1"}
        adapter = AicpLangGraphAdapter(provider, context=ctx)
        nodes = await adapter.build_nodes()
        await nodes["orders_place"]({"input": {}})
        assert len(provider.execute_calls) == 1


# ===========================================================================
# 4. build_tool_node (dispatch node)
# ===========================================================================


class TestBuildToolNode:
    @pytest.mark.asyncio
    async def test_returns_callable(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability()]))
        tool_node = await adapter.build_tool_node()
        assert callable(tool_node)

    @pytest.mark.asyncio
    async def test_tool_node_dispatches_by_capability_name(self):
        provider = FakeProvider([make_capability("orders.place"), make_capability("orders.cancel")])
        adapter = AicpLangGraphAdapter(provider)
        tool_node = await adapter.build_tool_node()
        state = {"capability_name": "orders.place", "input": {"item": "burger"}}
        await tool_node(state)
        assert provider.execute_calls[0][0] == "orders.place"

    @pytest.mark.asyncio
    async def test_tool_node_returns_dict_with_output(self):
        provider = FakeProvider(
            [make_capability("orders.place")],
            results={"orders.place": {"order_id": "ord_5"}},
        )
        adapter = AicpLangGraphAdapter(provider)
        tool_node = await adapter.build_tool_node()
        result = await tool_node({"capability_name": "orders.place", "input": {}})
        assert "output" in result
        assert result["output"] == {"order_id": "ord_5"}

    @pytest.mark.asyncio
    async def test_tool_node_raises_on_unknown_capability(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability("orders.place")]))
        tool_node = await adapter.build_tool_node()
        with pytest.raises(Exception):
            await tool_node({"capability_name": "nonexistent.cap", "input": {}})

    @pytest.mark.asyncio
    async def test_tool_node_raises_on_missing_capability_name_key(self):
        adapter = AicpLangGraphAdapter(FakeProvider([make_capability()]))
        tool_node = await adapter.build_tool_node()
        with pytest.raises((KeyError, ValueError)):
            await tool_node({"input": {}})
