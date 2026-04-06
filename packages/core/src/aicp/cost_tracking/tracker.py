from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .estimator import CostEstimator
from .models import TokenBudget, UsageRecord


class CostError(Exception):
    pass


class BudgetExceeded(CostError):
    def __init__(self, limit_type: str, current: float, limit: float) -> None:
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
        super().__init__(f"Budget exceeded: {limit_type} {current:.2f}/{limit:.2f}")


class CostTracker:
    def __init__(self, budget: TokenBudget | None = None) -> None:
        self.budget = budget or TokenBudget()
        self._records: list[UsageRecord] = []

    def record(
        self,
        provider_id: str,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        success: bool = True,
        error: str | None = None,
    ) -> UsageRecord:
        cost = self._estimate_cost(provider_id, model_id, tokens_in, tokens_out)
        record = UsageRecord(
            id=str(uuid.uuid4()),
            provider_id=provider_id,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost=cost,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            success=success,
            error=error,
        )
        self._records.append(record)
        self._check_budget()
        return record

    def get_total_tokens(self, provider_id: str | None = None) -> int:
        records = self._records if provider_id is None else [record for record in self._records if record.provider_id == provider_id]
        return sum(record.tokens_in + record.tokens_out for record in records)

    def get_total_cost(self, provider_id: str | None = None) -> float:
        records = self._records if provider_id is None else [record for record in self._records if record.provider_id == provider_id]
        return sum(record.estimated_cost for record in records)

    def get_average_latency(self, provider_id: str | None = None) -> float:
        records = self._records if provider_id is None else [record for record in self._records if record.provider_id == provider_id]
        if not records:
            return 0.0
        return sum(record.latency_ms for record in records) / len(records)

    def get_records(self, limit: int = 100) -> list[UsageRecord]:
        return self._records[-limit:]

    def _estimate_cost(self, provider_id: str, model_id: str, tokens_in: int, tokens_out: int) -> float:
        del provider_id
        return CostEstimator.estimate(model_id=model_id, tokens_in=tokens_in, tokens_out=tokens_out)

    def _check_budget(self) -> None:
        daily_cost = self.get_total_cost()
        if daily_cost > self.budget.cost_daily_limit:
            raise BudgetExceeded("daily_cost", daily_cost, self.budget.cost_daily_limit)
