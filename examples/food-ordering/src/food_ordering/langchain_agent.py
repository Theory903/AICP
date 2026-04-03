"""LangChain integration for the food-ordering example.

Wraps ``FoodOrderProvider`` with ``AicpLangChainAdapter`` to expose all
food-ordering capabilities as LangChain ``BaseTool`` instances.

Usage::

    from food_ordering.provider import FoodOrderProvider
    from food_ordering.langchain_agent import build_langchain_tools

    provider = FoodOrderProvider()
    tools = await build_langchain_tools(provider)
    # Pass tools to any LangChain agent
"""

from __future__ import annotations

from typing import Any

from aicp_connect_langchain import AicpCapabilityTool, AicpLangChainAdapter

from food_ordering.provider import FoodOrderProvider


async def build_langchain_tools(
    provider: FoodOrderProvider | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> list[AicpCapabilityTool]:
    """Return all food-ordering capabilities as LangChain tools.

    Parameters
    ----------
    provider:
        A ``FoodOrderProvider`` instance. If ``None``, a fresh one is created.
    context:
        Optional execution context forwarded to every capability call.

    Returns
    -------
    list[AicpCapabilityTool]
        One tool per food-ordering capability (5 total).
    """
    if provider is None:
        provider = FoodOrderProvider()

    adapter = AicpLangChainAdapter(provider, context=context)
    return await adapter.build_tools()
