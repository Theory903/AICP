from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChannelConfig(BaseModel):
    auth_token: str | None = None
    webhook_url: str | None = None
    allowlist: list[str] = Field(default_factory=list)
    rate_limit_rpm: int = 60
    max_message_length: int = 4096
    retry_count: int = 3
    retry_delay_ms: int = 1000
    extra: dict[str, Any] = Field(default_factory=dict)

    def is_allowed(self, sender_id: str) -> bool:
        if not self.allowlist:
            return True
        return sender_id in self.allowlist
