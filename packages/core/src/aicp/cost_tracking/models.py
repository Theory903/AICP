from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PricingTier(str, Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass(slots=True)
class UsageRecord:
    id: str
    provider_id: str
    model_id: str
    tokens_in: int
    tokens_out: int
    estimated_cost: float
    latency_ms: float
    timestamp: str
    success: bool = True
    error: str | None = None


@dataclass(slots=True)
class TokenBudget:
    daily_limit: int = 100000
    monthly_limit: int = 3000000
    cost_daily_limit: float = 10.0
    cost_monthly_limit: float = 300.0
