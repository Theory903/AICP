import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenSet:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    scopes: list[str] = field(default_factory=list)


class TokenManager:
    def __init__(self):
        self._tokens: Optional[TokenSet] = None

    def store_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        self._tokens = TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=time.time() + expires_in,
            scopes=[],
        )

    def store_token_only(self, access_token: str, expires_in: Optional[int] = None):
        expires_at = (time.time() + expires_in) if expires_in else None
        self._tokens = TokenSet(
            access_token=access_token,
            expires_at=expires_at,
            scopes=[],
        )

    def should_refresh(self, buffer_seconds: int = 300) -> bool:
        if not self._tokens or not self._tokens.expires_at:
            return False
        return time.time() > (self._tokens.expires_at - buffer_seconds)

    def get_access_token(self) -> Optional[str]:
        if not self._tokens:
            return None
        return self._tokens.access_token

    def get_refresh_token(self) -> Optional[str]:
        if not self._tokens:
            return None
        return self._tokens.refresh_token

    def is_valid(self) -> bool:
        if not self._tokens or not self._tokens.access_token:
            return False
        if self._tokens.expires_at and time.time() > self._tokens.expires_at:
            return False
        return True
