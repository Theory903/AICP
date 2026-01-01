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
