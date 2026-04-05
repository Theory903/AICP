from typing import Any, Optional

from pydantic import BaseModel


class PluginManifest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[dict[str, str]] = None
    commands: list[str] = []
    skills: list[str] = []
    hooks: Optional[str] = None
    mcp_servers: dict[str, Any] = {}

    def is_valid(self) -> tuple[bool, Optional[str]]:
        try:
            self.model_validate(self.model_dump())
            return (True, None)
        except Exception as e:
            return (False, str(e))

    @classmethod
    def from_dict(cls, data: dict) -> tuple[bool, Optional["PluginManifest"], Optional[str]]:
        try:
            manifest = cls.model_validate(data)
            return (True, manifest, None)
        except Exception as e:
            return (False, None, str(e))
