from __future__ import annotations

from importlib import import_module

import pytest

cost_tracking = import_module("aicp.cost_tracking")
cost_tracking_models = import_module("aicp.cost_tracking.models")

BudgetExceeded = cost_tracking.BudgetExceeded
CostTracker = cost_tracking.CostTracker
TokenBudget = cost_tracking_models.TokenBudget


class TestCostTracker:
    def test_record_and_get_total_tokens(self) -> None:
        tracker = CostTracker()

        tracker.record(
            provider_id="openai",
            model_id="gpt-4",
            tokens_in=100,
            tokens_out=50,
            latency_ms=120.0,
        )
        tracker.record(
            provider_id="openai",
            model_id="gpt-4",
            tokens_in=25,
            tokens_out=25,
            latency_ms=80.0,
        )

        assert tracker.get_total_tokens() == 200
        assert tracker.get_total_tokens(provider_id="openai") == 200

    def test_get_total_cost(self) -> None:
        tracker = CostTracker()

        tracker.record(
            provider_id="anthropic",
            model_id="claude-3-sonnet",
            tokens_in=1_000_000,
            tokens_out=1_000_000,
            latency_ms=100.0,
        )

        assert tracker.get_total_cost() == pytest.approx(0.018)
        assert tracker.get_total_cost(provider_id="anthropic") == pytest.approx(0.018)

    def test_get_average_latency(self) -> None:
        tracker = CostTracker()

        tracker.record(
            provider_id="google",
            model_id="gemini-pro",
            tokens_in=10,
            tokens_out=20,
            latency_ms=100.0,
        )
        tracker.record(
            provider_id="google",
            model_id="gemini-pro",
            tokens_in=10,
            tokens_out=20,
            latency_ms=200.0,
        )

        assert tracker.get_average_latency() == pytest.approx(150.0)
        assert tracker.get_average_latency(provider_id="google") == pytest.approx(150.0)

    def test_budget_exceeded_raised_when_over_limit(self) -> None:
        tracker = CostTracker(
            budget=TokenBudget(
                cost_daily_limit=0.000001,
                cost_monthly_limit=1.0,
                daily_limit=1_000_000,
                monthly_limit=1_000_000,
            )
        )

        with pytest.raises(BudgetExceeded):
            tracker.record(
                provider_id="openai",
                model_id="gpt-4",
                tokens_in=100_000,
                tokens_out=100_000,
                latency_ms=50.0,
            )
