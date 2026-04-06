from __future__ import annotations

from datetime import datetime, timezone

from aicp.providers.usage import UsageRecord, UsageTracker


class TestUsageTracker:
    def test_record_and_get_total(self) -> None:
        tracker = UsageTracker()
        tracker.record(
            UsageRecord(
                provider_id="openai-primary",
                tokens_in=100,
                tokens_out=50,
                estimated_cost=0.02,
                latency_ms=100.0,
                timestamp=datetime.now(timezone.utc),
                error=False,
            )
        )
        tracker.record(
            UsageRecord(
                provider_id="openai-primary",
                tokens_in=30,
                tokens_out=20,
                estimated_cost=0.01,
                latency_ms=150.0,
                timestamp=datetime.now(timezone.utc),
                error=True,
            )
        )

        total = tracker.get_total("openai-primary")

        assert total.tokens_in == 130
        assert total.tokens_out == 70
        assert total.estimated_cost == 0.03
        assert total.error is True

    def test_cost_estimate(self) -> None:
        tracker = UsageTracker()
        tracker.record(
            UsageRecord(
                provider_id="anthropic-backup",
                tokens_in=10,
                tokens_out=20,
                estimated_cost=0.015,
                latency_ms=80.0,
                timestamp=datetime.now(timezone.utc),
                error=False,
            )
        )
        tracker.record(
            UsageRecord(
                provider_id="anthropic-backup",
                tokens_in=20,
                tokens_out=10,
                estimated_cost=0.025,
                latency_ms=120.0,
                timestamp=datetime.now(timezone.utc),
                error=False,
            )
        )

        assert tracker.get_cost_estimate("anthropic-backup") == 0.04

    def test_latency_average(self) -> None:
        tracker = UsageTracker()
        for latency_ms in [100.0, 200.0, 300.0]:
            tracker.record(
                UsageRecord(
                    provider_id="google-primary",
                    tokens_in=1,
                    tokens_out=1,
                    estimated_cost=0.001,
                    latency_ms=latency_ms,
                    timestamp=datetime.now(timezone.utc),
                    error=False,
                )
            )

        assert tracker.get_latency_avg("google-primary") == 200.0
