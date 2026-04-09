"""Gmail integration plugin for AICP."""
import base64
import json
from dataclasses import dataclass


@dataclass
class GmailConfig:
    credentials_json: str


class GmailClient:
    def __init__(self, config: GmailConfig):
        self.config = config
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
        import httpx
        self._client = httpx.AsyncClient()
        self._token = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        creds = json.loads(self.config.credentials_json)
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": creds.get("client_id"),
            "client_secret": creds.get("client_secret"),
            "refresh_token": creds.get("refresh_token"),
            "grant_type": "refresh_token",
        }
        resp = await self._client.post(token_url, data=data)
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    async def list_messages(self, max_results: int = 10, query: str = "") -> list[dict]:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        resp = await self._client.get(
            f"{self.base_url}/users/me/messages", headers=headers, params=params
        )
        resp.raise_for_status()
        return resp.json().get("messages", [])

    async def get_message(self, msg_id: str) -> dict:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._client.get(
            f"{self.base_url}/users/me/messages/{msg_id}", headers=headers
        )
        resp.raise_for_status()
        return resp.json()

    async def send_message(
        self, to: str, subject: str, body: str
    ) -> dict:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        msg = f"From: me\r\nTo: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(msg.encode("utf-8")).decode("utf-8")
        payload = {"raw": encoded}
        resp = await self._client.post(
            f"{self.base_url}/users/me/messages/send", headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.json()


def get_capabilities():
    from aicp.core.capability import Capability, CapabilityKind

    return [
        Capability(
            name="gmail.messages.list",
            description="List Gmail messages",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "default": 10},
                    "query": {"type": "string", "default": ""},
                },
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="gmail.messages.get",
            description="Get a specific Gmail message",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                },
                "required": ["message_id"],
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="gmail.messages.send",
            description="Send an email",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
            output_schema={"type": "object"},
        ),
    ]


__all__ = ["GmailClient", "GmailConfig", "get_capabilities"]
