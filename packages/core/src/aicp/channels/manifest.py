from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChannelType(str, Enum):
    WEBHOOK = "webhook"
    API = "api"
    CONSOLE = "console"
    CUSTOM = "custom"


class ChannelManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    channel_type: ChannelType
    description: str = ""
    config_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    enabled: bool = True
    priority: int = 100
    allowlist: list[str] = Field(default_factory=list)

    @field_validator("id", "name", mode="before")
    @classmethod
    def _normalize(cls, value: Any) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value cannot be empty")
        return normalized
