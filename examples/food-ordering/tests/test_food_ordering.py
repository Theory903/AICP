"""TDD tests for the food-ordering reference example.

Tests cover:
1. FoodOrderProvider — CapabilityProvider implementation
2. YAML DSL workflow parsing (food_order.yaml)
3. EventWaiter integration (order.confirmed event)
4. LangChain adapter integration
5. LangGraph adapter integration
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — allow imports from src/ without installing
# ---------------------------------------------------------------------------

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YAML_DIR = Path(__file__).parent.parent / "aicp" / "workflows"


# ===========================================================================
# 1. FoodOrderProvider — CapabilityProvider
# ===========================================================================


class TestFoodOrderProvider:
    """Tests for the FoodOrderProvider CapabilityProvider implementation."""

    @pytest.fixture
    def provider(self):
        from food_ordering.provider import FoodOrderProvider
        return FoodOrderProvider()

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == "food_order"

    @pytest.mark.asyncio
    async def test_provider_name(self, provider):
        assert provider.provider_name == "food-ordering"

    @pytest.mark.asyncio
    async def test_discover_returns_five_capabilities(self, provider):
        caps = await provider.discover()
        assert len(caps) == 5
        names = {c.name for c in caps}
        assert names == {
            "food.list_menu",
            "food.add_to_cart",
            "food.view_cart",
            "food.checkout",
            "food.clear_cart",
        }

    @pytest.mark.asyncio
    async def test_get_capability_found(self, provider):
        cap = await provider.get_capability("food.list_menu")
        assert cap is not None
        assert cap.name == "food.list_menu"

    @pytest.mark.asyncio
    async def test_get_capability_not_found(self, provider):
        cap = await provider.get_capability("food.nonexistent")
        assert cap is None

    @pytest.mark.asyncio
    async def test_execute_list_menu(self, provider):
        result = await provider.execute("food.list_menu", {})
        assert "items" in result
        assert len(result["items"]) == 5

    @pytest.mark.asyncio
    async def test_execute_add_to_cart(self, provider):
        # Clear state first
        await provider.execute("food.clear_cart", {})
        result = await provider.execute("food.add_to_cart", {"item_id": "burger", "quantity": 1})
        assert "cart_item" in result
        assert "cart_total" in result
        assert result["cart_total"] > 0

    @pytest.mark.asyncio
    async def test_execute_view_cart(self, provider):
        await provider.execute("food.clear_cart", {})
        await provider.execute("food.add_to_cart", {"item_id": "fries", "quantity": 2})
        result = await provider.execute("food.view_cart", {})
        assert "items" in result
        assert "total" in result
        assert result["total"] > 0

    @pytest.mark.asyncio
    async def test_execute_checkout(self, provider):
        await provider.execute("food.clear_cart", {})
        await provider.execute("food.add_to_cart", {"item_id": "pizza", "quantity": 1})
        result = await provider.execute(
            "food.checkout",
            {"delivery_address": "42 Test St", "payment_method": "card"},
        )
        assert result["status"] == "confirmed"
        assert "order_id" in result

    @pytest.mark.asyncio
    async def test_execute_clear_cart(self, provider):
        await provider.execute("food.add_to_cart", {"item_id": "drink", "quantity": 1})
        result = await provider.execute("food.clear_cart", {})
        assert result["cleared"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_capability_raises(self, provider):
        from aicp.interfaces.capability_provider import CapabilityNotFoundError
        with pytest.raises(CapabilityNotFoundError):
            await provider.execute("food.unknown", {})

    @pytest.mark.asyncio
    async def test_each_provider_instance_has_isolated_cart(self):
        """Two FoodOrderProvider instances must not share cart state."""
        from food_ordering.provider import FoodOrderProvider
        p1 = FoodOrderProvider()
        p2 = FoodOrderProvider()
        await p1.execute("food.clear_cart", {})
        await p2.execute("food.clear_cart", {})
        await p1.execute("food.add_to_cart", {"item_id": "burger", "quantity": 1})
        cart2 = await p2.execute("food.view_cart", {})
        assert cart2["items"] == []


# ===========================================================================
# 2. YAML DSL workflow parsing
# ===========================================================================


class TestYAMLWorkflow:
    """Tests for food_order.yaml parsed by WorkflowDSLParser."""

    @pytest.fixture
    def parser(self):
        from aicp_runtime.workflow.dsl import WorkflowDSLParser
        return WorkflowDSLParser()

    @pytest.fixture
    def workflow(self, parser):
        yaml_path = YAML_DIR / "food_order.yaml"
        return parser.parse_file(yaml_path)

    def test_workflow_name(self, workflow):
        assert workflow.name == "food_order"

    def test_workflow_has_four_steps(self, workflow):
        assert len(workflow.steps) == 4

    def test_step_ids(self, workflow):
        ids = [s.id for s in workflow.steps]
        assert ids == ["list_menu", "add_to_cart", "view_cart", "checkout"]

    def test_capability_names(self, workflow):
        caps = [s.capability_name for s in workflow.steps]
        assert caps == [
            "food.list_menu",
            "food.add_to_cart",
            "food.view_cart",
            "food.checkout",
        ]

    def test_step_types(self, workflow):
        for step in workflow.steps:
            assert step.metadata.get("type") == "capability"

    def test_checkout_has_arguments(self, workflow):
        checkout = next(s for s in workflow.steps if s.id == "checkout")
        assert "delivery_address" in (checkout.arguments or {})
        assert "payment_method" in (checkout.arguments or {})

    def test_yaml_round_trip(self, parser, workflow):
        """to_yaml → parse should produce the same step IDs."""
        yaml_text = parser.to_yaml(workflow)
        restored = parser.parse(yaml_text)
        assert [s.id for s in restored.steps] == [s.id for s in workflow.steps]


# ===========================================================================
# 3. EventWaiter integration
# ===========================================================================


class TestEventFlow:
    """Tests for the event-driven order confirmation flow."""

    @pytest.mark.asyncio
    async def test_order_confirmed_event_received(self):
        from food_ordering.event_flow import run_event_flow
        result = await run_event_flow(timeout_ms=500)
        assert result["event_name"] == "order.confirmed"
        assert "order_id" in result["payload"]

    @pytest.mark.asyncio
    async def test_event_flow_returns_order_id(self):
        from food_ordering.event_flow import run_event_flow
        result = await run_event_flow(timeout_ms=500)
        assert result["payload"]["order_id"] is not None

    @pytest.mark.asyncio
    async def test_event_flow_timeout(self):
        """If no event is published, EventTimeoutError should propagate."""
        from aicp_runtime.workflow.events import EventWaiter, EventTimeoutError
        waiter = EventWaiter(workflow_id="wf_test_timeout")
        with pytest.raises(EventTimeoutError):
            await waiter.wait_for_event("order.never", timeout_ms=50)


# ===========================================================================
# 4. LangChain adapter integration
# ===========================================================================


class TestLangChainIntegration:
    """Tests for the LangChain agent wrapper."""

    @pytest.fixture
    def provider(self):
        from food_ordering.provider import FoodOrderProvider
        return FoodOrderProvider()

    @pytest.mark.asyncio
    async def test_build_tools_returns_five_tools(self, provider):
        from food_ordering.langchain_agent import build_langchain_tools
        tools = await build_langchain_tools(provider)
        assert len(tools) == 5

    @pytest.mark.asyncio
    async def test_tool_names_use_underscores(self, provider):
        from food_ordering.langchain_agent import build_langchain_tools
        tools = await build_langchain_tools(provider)
        for tool in tools:
            assert "." not in tool.name

    @pytest.mark.asyncio
    async def test_tool_has_description(self, provider):
        from food_ordering.langchain_agent import build_langchain_tools
        tools = await build_langchain_tools(provider)
        for tool in tools:
            assert tool.description

    @pytest.mark.asyncio
    async def test_tool_execute_list_menu(self, provider):
        from food_ordering.langchain_agent import build_langchain_tools
        tools = await build_langchain_tools(provider)
        list_menu_tool = next(t for t in tools if t.name == "food_list_menu")
        result = await list_menu_tool._arun({})
        import json
        data = json.loads(result)
        assert "items" in data

    @pytest.mark.asyncio
    async def test_adapter_context_forwarded(self, provider):
        from food_ordering.langchain_agent import build_langchain_tools
        ctx = {"session_id": "test_sess"}
        tools = await build_langchain_tools(provider, context=ctx)
        assert len(tools) == 5


# ===========================================================================
# 5. LangGraph adapter integration
# ===========================================================================


class TestLangGraphIntegration:
    """Tests for the LangGraph flow wrapper."""

    @pytest.fixture
    def provider(self):
        from food_ordering.provider import FoodOrderProvider
        return FoodOrderProvider()

    @pytest.mark.asyncio
    async def test_build_nodes_returns_dict(self, provider):
        from food_ordering.langgraph_flow import build_langgraph_nodes
        nodes = await build_langgraph_nodes(provider)
        assert isinstance(nodes, dict)
        assert len(nodes) == 5

    @pytest.mark.asyncio
    async def test_node_names_use_underscores(self, provider):
        from food_ordering.langgraph_flow import build_langgraph_nodes
        nodes = await build_langgraph_nodes(provider)
        for name in nodes:
            assert "." not in name

    @pytest.mark.asyncio
    async def test_tool_node_dispatches_list_menu(self, provider):
        from food_ordering.langgraph_flow import build_tool_node
        tool_node = await build_tool_node(provider)
        state = {"capability_name": "food.list_menu", "input": {}}
        result = await tool_node(state)
        assert "output" in result
        assert "items" in result["output"]

    @pytest.mark.asyncio
    async def test_tool_node_raises_for_unknown_capability(self, provider):
        from food_ordering.langgraph_flow import build_tool_node
        tool_node = await build_tool_node(provider)
        with pytest.raises(ValueError, match="Unknown capability"):
            await tool_node({"capability_name": "food.unknown", "input": {}})

    @pytest.mark.asyncio
    async def test_individual_node_executes(self, provider):
        from food_ordering.langgraph_flow import build_langgraph_nodes
        await provider.execute("food.clear_cart", {})
        nodes = await build_langgraph_nodes(provider)
        node_fn = nodes["food_list_menu"]
        result = await node_fn({"input": {}})
        assert "output" in result
