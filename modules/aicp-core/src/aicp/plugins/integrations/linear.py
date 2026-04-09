"""Linear integration plugin for AICP."""
from dataclasses import dataclass


@dataclass
class LinearConfig:
    api_key: str
    org_id: str | None = None


class LinearClient:
    def __init__(self, config: LinearConfig):
        self.config = config
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": config.api_key,
            "Content-Type": "application/json",
        }

    async def issues(self, first: int = 50) -> list[dict]:
        query = f"""
        query {{ issues(first: {first}) {{ nodes {{ id title description state {{ name }} }} }} }}
        """
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url, headers=self.headers, json={"query": query}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("issues", {}).get("nodes", [])

    async def create_issue(
        self,
        title: str,
        description: str = "",
        team_id: str | None = None,
    ) -> dict:
        mutation = """
        mutation {{ issueCreate(input: {{ title: "{}", description: "{}" {} }}) {{
            success issue {{ id title }} }} }}
        """.format(
            title.replace('"', '\\"'),
            description.replace('"', '\\"'),
            f', teamId: "{team_id}"' if team_id else "",
        )
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url, headers=self.headers, json={"query": mutation}
            )
            resp.raise_for_status()
            return resp.json()

    async def list_teams(self) -> list[dict]:
        query = """query { teams { nodes { id key name } } }"""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.base_url, headers=self.headers, json={"query": query}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("teams", {}).get("nodes", [])


def get_capabilities():
    from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema

    return [
        Capability(
            name="linear.issues.list",
            description="List Linear issues",
            kind=CapabilityKind.QUERY,
            input_schema=InputSchema(
                type="object",
                properties={"first": {"type": "integer", "default": 50}},
            ),
            output_schema=OutputSchema(type="object"),
        ),
        Capability(
            name="linear.issues.create",
            description="Create a Linear issue",
            kind=CapabilityKind.ACTION,
            input_schema=InputSchema(
                type="object",
                properties={
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "team_id": {"type": "string"},
                },
                required=["title"],
            ),
            output_schema=OutputSchema(type="object"),
        ),
        Capability(
            name="linear.teams.list",
            description="List Linear teams",
            kind=CapabilityKind.QUERY,
            input_schema=InputSchema(type="object"),
            output_schema=OutputSchema(type="object"),
        ),
    ]


__all__ = ["LinearClient", "LinearConfig", "get_capabilities"]
