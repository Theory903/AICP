from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class UsageRecord:
    provider_id: str
    tokens_in: int
    tokens_out: int
    estimated_cost: float
    latency_ms: float
    timestamp: datetime
    error: bool = False


class UsageTracker:
    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def record(self, record: UsageRecord) -> None:
        self._records.append(record)

    def get_total(self, provider_id: str) -> UsageRecord:
        matching = [record for record in self._records if record.provider_id == provider_id]
        return UsageRecord(
            provider_id=provider_id,
            tokens_in=sum(record.tokens_in for record in matching),
            tokens_out=sum(record.tokens_out for record in matching),
            estimated_cost=round(sum(record.estimated_cost for record in matching), 10),
            latency_ms=sum(record.latency_ms for record in matching),
            timestamp=max((record.timestamp for record in matching), default=datetime.now(timezone.utc)),
            error=any(record.error for record in matching),
        )

    def get_all(self) -> list[UsageRecord]:
        return list(self._records)

    def get_cost_estimate(self, provider_id: str) -> float:
        return round(sum(record.estimated_cost for record in self._records if record.provider_id == provider_id), 10)

    def get_latency_avg(self, provider_id: str) -> float:
        matching = [record.latency_ms for record in self._records if record.provider_id == provider_id]
        if not matching:
            return 0.0
        return sum(matching) / len(matching)
