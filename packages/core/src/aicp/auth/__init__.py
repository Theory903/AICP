"""Authentication support for AICP.

Provides authentication mechanisms:
- API Key
- Basic
- Bearer
- OAuth2 client credentials
- OAuth2 with refresh token support
"""

from __future__ import annotations

import asyncio
import base64
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx


class AuthError(Exception):
    """Base exception for authentication-related failures."""


class InvalidAuthConfigError(AuthError):
    """Raised when an auth object is configured incorrectly."""


class TokenFetchError(AuthError):
    """Raised when an OAuth token cannot be fetched or refreshed."""


class Auth(ABC):
    """Base authentication class."""

    @abstractmethod
    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        """Apply authentication material to request headers/params."""
        raise NotImplementedError

    async def ensure_ready(self) -> None:
        """Ensure the auth object is ready before apply is used.

        Sync auth types do not need preparation, but OAuth-based types do.
        """
        return None


class ApiKeyAuth(Auth):
    """API Key authentication.

    Supports sending the key via header or query parameter.
    """

    def __init__(
        self,
        api_key: str,
        header_name: str = "Authorization",
        location: str = "header",
    ) -> None:
        if not api_key:
            raise InvalidAuthConfigError("api_key cannot be empty")
        if location not in {"header", "query"}:
            raise InvalidAuthConfigError("location must be either 'header' or 'query'")
        if not header_name:
            raise InvalidAuthConfigError("header_name cannot be empty")

        self.api_key = api_key
        self.header_name = header_name
        self.location = location

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        if self.location == "header":
            headers[self.header_name] = self.api_key
        else:
            params[self.header_name] = self.api_key


class BasicAuth(Auth):
    """Basic authentication."""

    def __init__(self, username: str, password: str) -> None:
        if not username:
            raise InvalidAuthConfigError("username cannot be empty")
        if password is None:
            raise InvalidAuthConfigError("password cannot be None")

        self.username = username
        self.password = password

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"


class BearerAuth(Auth):
    """Bearer token authentication."""

    def __init__(self, token: str) -> None:
        if not token:
            raise InvalidAuthConfigError("token cannot be empty")
        self.token = token

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        headers["Authorization"] = f"Bearer {self.token}"


class OAuth2Auth(Auth):
    """OAuth2 client credentials flow authentication.

    Supports machine-to-machine authentication with token caching and expiry handling.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        scopes: list[str] | None = None,
        audience: str | None = None,
        refresh_margin_seconds: int = 30,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not client_id:
            raise InvalidAuthConfigError("client_id cannot be empty")
        if not client_secret:
            raise InvalidAuthConfigError("client_secret cannot be empty")
        if not token_url:
            raise InvalidAuthConfigError("token_url cannot be empty")
        if refresh_margin_seconds < 0:
            raise InvalidAuthConfigError("refresh_margin_seconds must be >= 0")
        if timeout_seconds <= 0:
            raise InvalidAuthConfigError("timeout_seconds must be > 0")

        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scopes = scopes or []
        self.audience = audience
        self.refresh_margin_seconds = refresh_margin_seconds
        self.timeout_seconds = timeout_seconds

        self._cached_token: str | None = None
        self._token_expires_at: float | None = None
        self._lock = asyncio.Lock()

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        if not self._cached_token:
            raise TokenFetchError("OAuth2 token is not available. Call 'await ensure_ready()' before apply().")
        headers["Authorization"] = f"Bearer {self._cached_token}"

    async def ensure_ready(self) -> None:
        """Ensure a valid access token is available."""
        if self._has_valid_token():
            return

        async with self._lock:
            if self._has_valid_token():
                return
            await self.fetch_token()

    def _has_valid_token(self) -> bool:
        if not self._cached_token:
            return False
        if self._token_expires_at is None:
            return True
        return time.time() < (self._token_expires_at - self.refresh_margin_seconds)

    async def fetch_token(self) -> str:
        """Fetch a new OAuth2 access token using client credentials."""
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        if self.scopes:
            data["scope"] = " ".join(self.scopes)
        if self.audience:
            data["audience"] = self.audience

        token_data = await self._post_token_request(data)
        return self._store_token_response(token_data)

    async def _post_token_request(self, data: dict[str, str]) -> dict[str, Any]:
        timeout = httpx.Timeout(self.timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.token_url, data=data)
                text = response.text
                if response.status_code != 200:
                    raise TokenFetchError(f"OAuth2 token request failed: status={response.status_code}, body={text}")
                try:
                    return response.json()
                except Exception as exc:
                    raise TokenFetchError(f"OAuth2 token response was not valid JSON: {text}") from exc
        except httpx.HTTPError as exc:
            raise TokenFetchError(f"OAuth2 token request failed: {exc}") from exc

    def _store_token_response(self, token_data: dict[str, Any]) -> str:
        token = token_data.get("access_token")
        if not isinstance(token, str) or not token:
            raise TokenFetchError("OAuth2 response missing valid 'access_token'")

        self._cached_token = token

        expires_in = token_data.get("expires_in")
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            self._token_expires_at = time.time() + float(expires_in)
        else:
            self._token_expires_at = None

        return token


class OAuth2WithRefresh(OAuth2Auth):
    """OAuth2 authentication with refresh token support.

    Supports refresh-token flow for long-lived user-based sessions.
    Falls back to client credentials if no refresh token is available.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        refresh_token: str | None = None,
        scopes: list[str] | None = None,
        audience: str | None = None,
        refresh_margin_seconds: int = 30,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            scopes=scopes,
            audience=audience,
            refresh_margin_seconds=refresh_margin_seconds,
            timeout_seconds=timeout_seconds,
        )
        self.refresh_token = refresh_token

    async def ensure_ready(self) -> None:
        """Ensure a valid token exists, preferring refresh flow when possible."""
        if self._has_valid_token():
            return

        async with self._lock:
            if self._has_valid_token():
                return

            if self.refresh_token:
                try:
                    await self.refresh_access_token()
                    return
                except TokenFetchError:
                    # Fall back to client credentials instead of dying dramatically.
                    pass

            await self.fetch_token()

    async def refresh_access_token(self) -> str:
        """Refresh the access token using a refresh token."""
        if not self.refresh_token:
            raise TokenFetchError("No refresh_token available for refresh flow")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        token_data = await self._post_token_request(data)
        token = self._store_token_response(token_data)

        new_refresh_token = token_data.get("refresh_token")
        if isinstance(new_refresh_token, str) and new_refresh_token:
            self.refresh_token = new_refresh_token

        return token
