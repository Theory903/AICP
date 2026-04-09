import base64
import hashlib
import secrets
from dataclasses import dataclass

import httpx


@dataclass
class PKCEPair:
    verifier: str
    challenge: str

    @staticmethod
    def generate() -> "PKCEPair":
        verifier = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return PKCEPair(verifier=verifier, challenge=challenge)


class OAuth2Service:
    def __init__(
        self,
        client_id: str,
        auth_url: str,
        token_url: str,
        redirect_uri: str = "http://localhost:8765/callback",
    ):
        self.client_id = client_id
        self.auth_url = auth_url
        self.token_url = token_url
        self.redirect_uri = redirect_uri
        self._pkce: PKCEPair | None = None

    def get_authorization_url(self, state: str, scope: str = "user:inference offline_access") -> str:
        self._pkce = PKCEPair.generate()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "code_challenge": self._pkce.challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": scope,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.auth_url}?{query}"

    async def exchange_code(self, code: str) -> dict:
        if not self._pkce:
            raise ValueError("No PKCE pair available. Call get_authorization_url first.")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "code": code,
                    "code_verifier": self._pkce.verifier,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()
