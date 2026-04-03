"""AICP LangGraph adapter.

Wraps an AICP ``CapabilityProvider`` so each capability can be added as an
async node in a LangGraph ``StateGraph``.

Usage
-----
::

    from aicp_connect_langgraph import AicpLangGraphAdapter
    from langgraph.graph import StateGraph, END
    from typing import TypedDict

    class AgentState(TypedDict):
        input: dict
        output: dict
        capability_name: str

    adapter = AicpLangGraphAdapter(provider)
    nodes = await adapter.build_nodes()
    tool_node = await adapter.build_tool_node()

    graph = StateGraph(AgentState)
    for name, fn in nodes.items():
        graph.add_node(name, fn)
    graph.add_node("tool_node", tool_node)

Design notes
------------
* Each per-capability node function accepts a ``state`` dict and reads
  ``state.get("input", {})`` as the capability arguments.
* The dispatch tool node reads ``state["capability_name"]`` and
  ``state.get("input", {})`` to route to the correct capability.
* Node names use underscores instead of dots for LangGraph compat.
* Errors from the capability provider propagate directly so the graph can
  handle them via retry edges or error nodes.
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from aicp.interfaces.capability_provider import CapabilityProvider

__all__ = [
    "AdapterConfigError",
    "AicpLangGraphAdapter",
]

# Type alias for a LangGraph node function
NodeFn = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class AdapterConfigError(Exception):
    """Raised for invalid adapter configuration."""


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AicpLangGraphAdapter:
    """Converts an AICP ``CapabilityProvider`` into LangGraph node functions.

    Parameters
    ----------
    provider:
        Any AICP ``CapabilityProvider`` implementation.
    context:
        Optional execution context forwarded to every capability call.
    """

    def __init__(
        self,
        provider: CapabilityProvider,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        if provider is None:
            raise AdapterConfigError("provider must not be None")
        self._provider = provider
        self._context: dict[str, Any] = context or {}

    @property
    def provider(self) -> CapabilityProvider:
        return self._provider

    @property
    def context(self) -> dict[str, Any]:
        return self._context

    async def build_nodes(self) -> dict[str, NodeFn]:
        """Discover capabilities and return one async node function per capability.

        Node names use underscores instead of dots.

        Returns
        -------
        dict[str, NodeFn]
            ``{node_name: async_fn}``
        """
        capabilities = await self._provider.discover()
        nodes: dict[str, NodeFn] = {}
        for cap in capabilities:
            node_name = cap.name.replace(".", "_")
            # Capture cap and provider in closure
            nodes[node_name] = _make_node_fn(
                capability_name=cap.name,
                provider=self._provider,
                context=self._context,
            )
        return nodes

    async def build_tool_node(self) -> NodeFn:
        """Return a single dispatch node that routes by state["capability_name"].

        The returned function reads ``state["capability_name"]`` and
        ``state.get("input", {})`` and invokes the matching capability.

        Raises
        ------
        KeyError
            If ``state`` does not contain ``"capability_name"``.
        ValueError
            If the capability name is unknown.
        """
        # Pre-discover all capability names so we can validate at dispatch time
        capabilities = await self._provider.discover()
        known_names = {cap.name for cap in capabilities}

        provider = self._provider
        context = self._context

        async def _tool_node(state: dict[str, Any]) -> dict[str, Any]:
            capability_name: str = state["capability_name"]  # raises KeyError if missing
            if capability_name not in known_names:
                raise ValueError(
                    f"Unknown capability '{capability_name}'. "
                    f"Known: {sorted(known_names)}"
                )
            arguments: dict[str, Any] = state.get("input") or {}
            result = await provider.execute(capability_name, arguments, context=context)
            return {"output": result, "capability": capability_name}

        return _tool_node


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_node_fn(
    *,
    capability_name: str,
    provider: CapabilityProvider,
    context: dict[str, Any],
) -> NodeFn:
    """Build a node function for a single capability."""

    async def _node(state: dict[str, Any]) -> dict[str, Any]:
        arguments: dict[str, Any] = state.get("input") or {}
        result = await provider.execute(capability_name, arguments, context=context)
        return {"output": result, "capability": capability_name}

    _node.__name__ = capability_name.replace(".", "_")
    return _node
