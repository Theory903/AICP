"""Authentication support for AICP.

Provides authentication mechanisms: API Key, Basic, OAuth2.
"""

import base64
from abc import ABC, abstractmethod
from typing import Any


class Auth(ABC):
    """Base authentication class."""

    @abstractmethod
    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        """Apply authentication to request headers/params."""
        pass


class ApiKeyAuth(Auth):
    """API Key authentication."""

    def __init__(
        self,
        api_key: str,
        header_name: str = "Authorization",
        location: str = "header",
    ):
        self.api_key = api_key
        self.header_name = header_name
        self.location = location

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        if self.location == "header":
            headers[self.header_name] = self.api_key
        elif self.location == "query":
            params[self.header_name] = self.api_key


class BasicAuth(Auth):
    """Basic authentication."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"


class BearerAuth(Auth):
    """Bearer token authentication."""

    def __init__(self, token: str):
        self.token = token

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        headers["Authorization"] = f"Bearer {self.token}"


class OAuth2Auth(Auth):
    """OAuth2 client credentials flow authentication.

    Supports client credentials grant type for machine-to-machine authentication.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        scopes: list[str] | None = None,
        audience: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scopes = scopes or []
        self.audience = audience
        self._cached_token: str | None = None

    def apply(self, headers: dict[str, str], params: dict[str, Any]) -> None:
        if self._cached_token:
            headers["Authorization"] = f"Bearer {self._cached_token}"

    async def fetch_token(self) -> str:
        """Fetch OAuth2 token from token URL.

        Returns:
            Access token string.

        Raises:
            ValueError: If token fetch fails.
        """
        import aiohttp

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        if self.scopes:
            data["scope"] = " ".join(self.scopes)
        if self.audience:
            data["audience"] = self.audience

        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise ValueError(f"OAuth2 token fetch failed: {response.status} - {text}")

                token_data = await response.json()
                self._cached_token = token_data.get("access_token")
                return self._cached_token


class OAuth2WithRefresh(OAuth2Auth):
    """OAuth2 with refresh token support.

    Supports authorization code and refresh token flows for user-based auth.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        refresh_token: str | None = None,
        scopes: list[str] | None = None,
        audience: str | None = None,
    ):
        super().__init__(client_id, client_secret, token_url, scopes, audience)
        self.refresh_token = refresh_token

    async def refresh_access_token(self) -> str:
        """Refresh the access token using refresh token.

        Returns:
            New access token string.
        """
        import aiohttp

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    raise ValueError(f"OAuth2 refresh failed: {response.status}")

                token_data = await response.json()
                self._cached_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                return self._cached_token
