from __future__ import annotations

from importlib import import_module

import pytest

CostEstimator = import_module("aicp.cost_tracking").CostEstimator


class TestCostEstimator:
    def test_estimate_cost(self) -> None:
        estimated = CostEstimator.estimate("gpt-4", tokens_in=1_000_000, tokens_out=500_000)

        assert estimated == pytest.approx(0.06)

    def test_register_rate(self) -> None:
        CostEstimator.register_rate("custom-model", 0.1, 0.2)

        assert CostEstimator.estimate("custom-model", tokens_in=1_000_000, tokens_out=1_000_000) == pytest.approx(0.3)

    def test_list_rates(self) -> None:
        rates = CostEstimator.list_rates()

        assert "gpt-4" in rates
        assert rates["gpt-4"] == (0.03, 0.06)
