import json
from typing import Any, Callable, Optional

from pydantic import BaseModel


class NestJSConfig(BaseModel):
    base_url: str = "/aicp"
    enable_console: bool = True
    enable_discovery: bool = True


class AicpNestJS:
    def __init__(self, config: Optional[NestJSConfig] = None):
        self.config = config or NestJSConfig()
        self._capabilities: dict[str, Any] = {}

    def register_capability(self, name: str, handler: Callable) -> None:
        self._capabilities[name] = handler

    def get_controller(self) -> Callable:
        from aicp import AicpClient, CapabilityRegistry, InMemoryStore

        registry = CapabilityRegistry(InMemoryStore())
        client = AicpClient(registry)

        class AicpController:
            @staticmethod
            async def health() -> dict:
                return {"status": "ok"}

            @staticmethod
            async def list_capabilities() -> dict:
                caps = registry.list()
                return {"capabilities": caps}

            @staticmethod
            async def execute(body: dict) -> Any:
                name = body.get("capability")
                args = body.get("arguments", {})
                return client.execute(name, args)

            @staticmethod
            async def create_session(body: dict) -> dict:
                return client.create_session(body or {})

        return AicpController


def mount_aicp(module: Any, config: Optional[NestJSConfig] = None) -> AicpNestJS:
    aicp_nestjs = AicpNestJS(config)
    controller = aicp_nestjs.get_controller()
    return aicp_nestjs