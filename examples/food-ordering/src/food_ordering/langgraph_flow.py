"""LangGraph integration for the food-ordering example.

Wraps ``FoodOrderProvider`` with ``AicpLangGraphAdapter`` to expose all
food-ordering capabilities as async LangGraph node functions.

Usage::

    from food_ordering.provider import FoodOrderProvider
    from food_ordering.langgraph_flow import build_langgraph_nodes, build_tool_node

    provider = FoodOrderProvider()
    nodes = await build_langgraph_nodes(provider)
    tool_node = await build_tool_node(provider)

    # Use nodes in a StateGraph:
    #   for name, fn in nodes.items():
    #       graph.add_node(name, fn)
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from aicp_connect_langgraph import AicpLangGraphAdapter

from food_ordering.provider import FoodOrderProvider

# Type alias
NodeFn = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


async def build_langgraph_nodes(
    provider: FoodOrderProvider | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, NodeFn]:
    """Return all food-ordering capabilities as LangGraph node functions.

    Parameters
    ----------
    provider:
        A ``FoodOrderProvider`` instance. If ``None``, a fresh one is created.
    context:
        Optional execution context forwarded to every capability call.

    Returns
    -------
    dict[str, NodeFn]
        ``{node_name: async_fn}`` — one entry per capability (5 total).
        Node names use underscores instead of dots.
    """
    if provider is None:
        provider = FoodOrderProvider()

    adapter = AicpLangGraphAdapter(provider, context=context)
    return await adapter.build_nodes()


async def build_tool_node(
    provider: FoodOrderProvider | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> NodeFn:
    """Return a single dispatch node that routes by ``state["capability_name"]``.

    Parameters
    ----------
    provider:
        A ``FoodOrderProvider`` instance. If ``None``, a fresh one is created.
    context:
        Optional execution context.

    Returns
    -------
    NodeFn
        An async function that reads ``state["capability_name"]`` and
        ``state.get("input", {})`` to execute the matching capability.
    """
    if provider is None:
        provider = FoodOrderProvider()

    adapter = AicpLangGraphAdapter(provider, context=context)
    return await adapter.build_tool_node()
