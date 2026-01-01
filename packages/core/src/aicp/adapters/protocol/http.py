"""HTTP execution adapter for AICP.

Provides real HTTP execution capabilities with auth support.
"""

import re
from typing import Any
from urllib.parse import quote

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

from aicp.capability import Capability
from aicp.interfaces.capability_provider import CapabilityProvider


class HttpExecutionAdapter(CapabilityProvider):
    """HTTP-based capability execution.

    Executes capabilities as HTTP requests. Each capability maps to an endpoint.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        capabilities: list[Capability],
        default_headers: dict[str, str] | None = None,
    ):
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._capabilities: dict[str, Capability] = {cap.name: cap for cap in capabilities}
        self._default_headers = default_headers or {}

    @property
    def provider_type(self) -> str:
        return "http"

    @property
    def provider_name(self) -> str:
        return self._name

    async def discover(self) -> list[Capability]:
        return list(self._capabilities.values())

    async def get_capability(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        cap = self._capabilities.get(capability_name)
        if not cap:
            raise ValueError(f"Capability not found: {capability_name}")

        url = self._build_url(cap, arguments)
        headers = {**self._default_headers}
        headers.update(context.get("headers", {}) if context else {})

        body = arguments.get("body")
        for key in list(arguments.keys()):
            if key not in url and key != "body":
                if "?" not in url:
                    url += "?"
                else:
                    url += "&"
                url += f"{key}={quote(str(arguments[key]))}"

        async with aiohttp.ClientSession() as session:
            method = context.get("method", "POST") if context else "POST"
            async with session.request(
                method,
                url,
                headers=headers,
                json=body if body else None,
            ) as response:
                response.raise_for_status()
                return await response.json()

    def _build_url(self, cap: Capability, arguments: dict[str, Any]) -> str:
        url = self._base_url

        path = getattr(cap, "path", f"/{cap.name.replace('.', '/')}")
        for param in re.findall(r"\{([^}]+)\}", path):
            if param in arguments:
                path = path.replace(f"{{{param}}}", quote(str(arguments[param])))
                del arguments[param]

        return url + path
