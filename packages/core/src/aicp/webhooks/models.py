from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class WebhookEvent:
    id: str
    source: str
    event_type: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WebhookRoute:
    path: str
    event_type: str
    handler_path: str
    enabled: bool = True
    rate_limit_per_minute: int = 60


class WebhookSignatureError(Exception):
    pass


class WebhookValidationError(Exception):
    pass
