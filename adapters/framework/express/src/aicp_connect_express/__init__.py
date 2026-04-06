import json
from typing import Any, Callable, Optional

from aicp import AicpClient, CapabilityRegistry, InMemoryStore
from pydantic import BaseModel


class ExpressConfig(BaseModel):
    base_url: str = "/aicp"
    enable_console: bool = True
    enable_discovery: bool = True


class AicpExpress:
    def __init__(self, config: Optional[ExpressConfig] = None):
        self.config = config or ExpressConfig()
        self._registry = CapabilityRegistry(InMemoryStore())
        self._client = AicpClient(self._registry)

    def get_router(self) -> Callable:
        def router(req: Any, res: Any) -> None:
            path = req.path
            method = req.method

            if path == f"{self.config.base_url}/health":
                res.status(200).json({"status": "ok"})
            elif path.startswith(f"{self.config.base_url}/capabilities"):
                if method == "GET":
                    caps = self._registry.list()
                    res.status(200).json({"capabilities": caps})
                else:
                    res.status(405).json({"error": "Method not allowed"})
            elif path.startswith(f"{self.config.base_url}/execute"):
                if method == "POST":
                    body = json.loads(req.body or "{}")
                    name = body.get("capability")
                    args = body.get("arguments", {})
                    result = self._client.execute(name, args)
                    res.status(200).json(result)
                else:
                    res.status(405).json({"error": "Method not allowed"})
            elif path.startswith(f"{self.config.base_url}/sessions"):
                if method == "POST":
                    result = self._client.create_session({})
                    res.status(201).json(result)
                else:
                    res.status(405).json({"error": "Method not allowed"})
            elif self.config.enable_discovery and path == "/.well-known/aicp":
                caps = self._registry.list()
                res.status(200).json({"capabilities": caps, "version": "1.0"})
            else:
                res.status(404).json({"error": "Not found"})

        return router


def mount_aicp(app: Any, config: Optional[ExpressConfig] = None) -> AicpExpress:
    aicp_express = AicpExpress(config)
    aicp_router = aicp_express.get_router()
    app.use(f"{config.base_url if config else '/aicp'}", aicp_router)
    return aicp_express