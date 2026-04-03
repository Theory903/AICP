"""AICP LangChain adapter.

Wraps an AICP ``CapabilityProvider`` so each capability becomes a LangChain
``BaseTool``. This lets any LangChain agent (ReAct, OpenAI tools, etc.) discover
and invoke AICP capabilities transparently.

Usage
-----
::

    from aicp_runtime.services.capabilities import CapabilityService
    from aicp_connect_langchain import AicpLangChainAdapter

    # provider can be any CapabilityProvider implementation
    adapter = AicpLangChainAdapter(provider, context={"session_id": "sess_1"})
    tools = await adapter.build_tools()

    # Pass tools to any LangChain agent
    agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS)

Design notes
------------
* Dots in capability names are replaced with underscores because LangChain tool
  names may not contain dots.
* Both sync ``_run`` and async ``_arun`` are implemented. The sync variant runs
  the coroutine via ``asyncio.get_event_loop().run_until_complete`` when no loop
  is running, or via ``asyncio.run`` as a fallback.
* Tool execution results are serialized to JSON strings so LangChain can
  reason over them. If the result is already a string it is returned as-is.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from aicp.capability import Capability
from aicp.interfaces.capability_provider import CapabilityProvider

__all__ = [
    "AdapterConfigError",
    "AicpCapabilityTool",
    "AicpLangChainAdapter",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AdapterConfigError(Exception):
    """Raised for invalid adapter configuration."""


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


class AicpCapabilityTool(BaseTool):
    """A LangChain ``BaseTool`` backed by an AICP capability.

    Do not instantiate directly; use :meth:`AicpLangChainAdapter.build_tools`.
    """

    # LangChain requires name/description to be str class attributes but
    # Pydantic allows them to be set at init time via Field defaults.
    name: str = ""
    description: str = ""

    # Extra fields — must declare as Pydantic fields (model_config allows this)
    capability: Capability
    _provider: CapabilityProvider
    _context: dict[str, Any]

    model_config = {"arbitrary_types_allowed": True}  # type: ignore[assignment]

    def __init__(
        self,
        *,
        capability: Capability,
        provider: CapabilityProvider,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        safe_name = capability.name.replace(".", "_")
        super().__init__(
            name=safe_name,
            description=capability.description or capability.name,
            capability=capability,
            **kwargs,
        )
        # Use object.__setattr__ to bypass Pydantic's private attribute handling
        object.__setattr__(self, "_provider", provider)
        object.__setattr__(self, "_context", context)

    # ------------------------------------------------------------------
    # LangChain protocol
    # ------------------------------------------------------------------

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Synchronous execution — delegates to the async _arun via event loop."""
        tool_input = args[0] if args else kwargs
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Inside an async context; create a new loop in a thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self._arun(tool_input))
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(tool_input))
        except RuntimeError:
            return asyncio.run(self._arun(tool_input))

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async execution — calls the AICP capability provider."""
        # LangChain may pass input as positional or keyword argument
        tool_input = args[0] if args else kwargs
        arguments = _parse_tool_input(tool_input)
        result = await object.__getattribute__(self, "_provider").execute(
            self.capability.name,
            arguments,
            context=object.__getattribute__(self, "_context"),
        )
        return _serialize_result(result)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AicpLangChainAdapter:
    """Converts an AICP ``CapabilityProvider`` into a list of LangChain tools.

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

    async def build_tools(self) -> list[AicpCapabilityTool]:
        """Discover capabilities and return them as LangChain tools.

        Returns
        -------
        list[AicpCapabilityTool]
            One tool per discovered capability.
        """
        capabilities = await self._provider.discover()
        return [
            AicpCapabilityTool(
                capability=cap,
                provider=self._provider,
                context=self._context,
            )
            for cap in capabilities
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_tool_input(tool_input: Any) -> dict[str, Any]:
    """Parse tool input into a dict of arguments."""
    if isinstance(tool_input, dict):
        return tool_input
    if isinstance(tool_input, str):
        stripped = tool_input.strip()
        if stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return {"input": tool_input}
    return {}


def _serialize_result(result: Any) -> str:
    """Serialize an execution result to a string for LangChain."""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result)
    except (TypeError, ValueError):
        return str(result)
