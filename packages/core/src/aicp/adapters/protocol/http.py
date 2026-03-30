"""HTTP execution adapter for AICP.

Provides real HTTP execution capabilities with auth support.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover
    aiohttp = None
    AIOHTTP_AVAILABLE = False

from aicp.capability import Capability
from aicp.interfaces.capability_provider import CapabilityNotFoundError, CapabilityProvider


_PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")


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
        timeout_seconds: float = 30.0,
        auth: Any | None = None,
    ) -> None:
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._capabilities: dict[str, Capability] = {cap.name: cap for cap in capabilities}
        self._default_headers = dict(default_headers or {})
        self._timeout_seconds = timeout_seconds
        self._auth = auth
        self._session: aiohttp.ClientSession | None = None

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
        """Execute a capability as an HTTP request."""
        capability = self._capabilities.get(capability_name)
        if capability is None:
            raise CapabilityNotFoundError(f"Capability not found: {capability_name}")

        if not AIOHTTP_AVAILABLE or aiohttp is None:
            raise RuntimeError(
                "aiohttp is required for HTTP execution. Install it with: pip install aiohttp"
            )

        safe_context = context or {}
        request_args = dict(arguments)

        method = self._resolve_method(capability, safe_context)
        path = self._resolve_path(capability)
        url, remaining_args = self._build_url(path, request_args)

        body = remaining_args.pop("body", None)
        params = self._extract_query_params(remaining_args, safe_context)
        headers = self._build_headers(safe_context)

        timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
        session = await self._get_session(timeout)

        async with session.request(
            method=method,
            url=url,
            headers=headers,
            params=params or None,
            json=body if body is not None else None,
        ) as response:
            return await self._parse_response(response)

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self, timeout: "aiohttp.ClientTimeout") -> "aiohttp.ClientSession":
        """Get or create a shared aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _build_headers(self, context: dict[str, Any]) -> dict[str, str]:
        """Build request headers from defaults, auth, and runtime context."""
        headers = dict(self._default_headers)

        if self._auth is not None and hasattr(self._auth, "apply"):
            # Auth implementations mutate headers/params in place.
            self._auth.apply(headers, {})

        context_headers = context.get("headers")
        if isinstance(context_headers, dict):
            headers.update({str(k): str(v) for k, v in context_headers.items()})

        headers.setdefault("Accept", "application/json")
        return headers

    def _resolve_method(self, capability: Capability, context: dict[str, Any]) -> str:
        """Resolve the HTTP method for a capability."""
        context_method = context.get("method")
        if isinstance(context_method, str) and context_method.strip():
            return context_method.upper()

        for tag in capability.tags:
            if tag.startswith("method:"):
                return tag.split(":", 1)[1].upper()

        if capability.is_query:
            return "GET"

        return "POST"

    def _resolve_path(self, capability: Capability) -> str:
        """Resolve the HTTP path for a capability."""
        metadata_path = capability.model_dump(exclude_none=True).get("path")
        if isinstance(metadata_path, str) and metadata_path.strip():
            path = metadata_path
        else:
            path = f"/{capability.name.replace('.', '/')}"

        if not path.startswith("/"):
            path = f"/{path}"

        return path

    def _build_url(
        self,
        path: str,
        arguments: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Substitute path params and return final URL plus remaining arguments."""
        remaining_args = dict(arguments)
        resolved_path = path

        for param in _PATH_PARAM_RE.findall(path):
            if param not in remaining_args:
                raise ValueError(f"Missing required path parameter: {param}")

            value = quote(str(remaining_args.pop(param)))
            resolved_path = resolved_path.replace(f"{{{param}}}", value)

        return f"{self._base_url}{resolved_path}", remaining_args

    def _extract_query_params(
        self,
        remaining_args: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, str]:
        """Build query parameters from remaining args and explicit context params."""
        params: dict[str, str] = {}

        context_params = context.get("params")
        if isinstance(context_params, dict):
            params.update({str(k): str(v) for k, v in context_params.items()})

        for key, value in remaining_args.items():
            if value is None:
                continue
            params[str(key)] = str(value)

        return params

    async def _parse_response(self, response: "aiohttp.ClientResponse") -> Any:
        """Parse an HTTP response safely."""
        content_type = response.headers.get("Content-Type", "").lower()

        if response.status >= 400:
            error_body: Any
            try:
                if "application/json" in content_type:
                    error_body = await response.json()
                else:
                    error_body = await response.text()
            except Exception:
                error_body = None

            raise RuntimeError(
                f"HTTP request failed with status {response.status}: {error_body}"
            )

        if "application/json" in content_type:
            return await response.json()

        if content_type.startswith("text/") or not content_type:
            return await response.text()

        return await response.read()