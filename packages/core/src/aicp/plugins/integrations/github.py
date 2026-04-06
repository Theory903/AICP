"""GitHub integration plugin for AICP."""
from typing import Any, Optional
from dataclasses import dataclass
from aicp.core.capability import Capability, CapabilityKind
from aicp.core.errors import CapabilityError


@dataclass
class GitHubConfig:
    token: str
    owner: str
    repo: Optional[str] = None


class GitHubClient:
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/vnd.github+json",
        }

    async def list_issues(self, state: str = "open") -> list[dict]:
        url = f"{self.base_url}/repos/{self.config.owner}/issues"
        params = {"state": state, "per_page": 30}
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_issue(self, issue_number: int) -> dict:
        url = f"{self.base_url}/repos/{self.config.owner}/{self.config.repo}/issues/{issue_number}"
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def create_issue(self, title: str, body: str = "", labels: list[str] = None) -> dict:
        url = f"{self.base_url}/repos/{self.config.owner}/{self.config.repo}/issues"
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def list_pulls(self, state: str = "open") -> list[dict]:
        url = f"{self.base_url}/repos/{self.config.owner}/{self.config.repo}/pulls"
        params = {"state": state, "per_page": 30}
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def create_pull(
        self, title: str, body: str, head: str, base: str = "main"
    ) -> dict:
        url = f"{self.base_url}/repos/{self.config.owner}/{self.config.repo}/pulls"
        data = {"title": title, "body": body, "head": head, "base": base}
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def list_commits(self, path: Optional[str] = None) -> list[dict]:
        url = f"{self.base_url}/repos/{self.config.owner}/{self.config.repo}/commits"
        params = {"per_page": 30}
        if path:
            params["path"] = path
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()


def get_capabilities() -> list[Capability]:
    return [
        Capability(
            name="github.issues.list",
            description="List GitHub issues",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"}
                }
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="github.issues.get",
            description="Get a specific GitHub issue",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "issue_number": {"type": "integer"}
                },
                "required": ["issue_number"],
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="github.issues.create",
            description="Create a new GitHub issue",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title"],
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="github.pulls.list",
            description="List pull requests",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"}
                }
            },
            output_schema={"type": "object"},
        ),
        Capability(
            name="github.pulls.create",
            description="Create a pull request",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "head": {"type": "string"},
                    "base": {"type": "string", "default": "main"},
                },
                "required": ["title", "head"],
            },
            output_schema={"type": "object"},
        ),
    ]


__all__ = ["GitHubClient", "GitHubConfig", "get_capabilities"]