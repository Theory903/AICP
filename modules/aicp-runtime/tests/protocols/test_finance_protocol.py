"""Tests for the Finance Cognitive Protocol (TDD).

The Finance Protocol governs how the agent performs financial analysis
and transactional operations:
  - Produces a FinanceAction (a structured financial operation)
  - Classifies operation type: QUOTE, BUY, SELL, TRANSFER, BALANCE,
    ANALYZE, FORECAST
  - Enforces required fields per operation type
  - Validates amounts (must be positive)
  - Risk classification: low / medium / high (transactional ops default high)
  - Tracks finance actions per session
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aicp_runtime.protocols.finance import (
    FinanceProtocol,
    FinanceAction,
    FinanceOperationType,
    FinanceRiskLevel,
    FinanceProtocolError,
)


# ---------------------------------------------------------------------------
# FinanceAction
# ---------------------------------------------------------------------------


class TestFinanceAction:
    def test_quote_action_fields(self):
        action = FinanceAction(
            operation=FinanceOperationType.QUOTE,
            symbol="AAPL",
        )
        assert action.operation == FinanceOperationType.QUOTE
        assert action.symbol == "AAPL"

    def test_buy_action_fields(self):
        action = FinanceAction(
            operation=FinanceOperationType.BUY,
            symbol="BTC",
            amount=Decimal("0.5"),
            currency="USD",
        )
        assert action.amount == Decimal("0.5")
        assert action.currency == "USD"

    def test_transfer_action_fields(self):
        action = FinanceAction(
            operation=FinanceOperationType.TRANSFER,
            from_account="acct_001",
            to_account="acct_002",
            amount=Decimal("1000"),
            currency="USD",
        )
        assert action.from_account == "acct_001"
        assert action.to_account == "acct_002"

    def test_analyze_action_fields(self):
        action = FinanceAction(
            operation=FinanceOperationType.ANALYZE,
            symbol="AAPL",
            period="1Y",
        )
        assert action.period == "1Y"

    def test_forecast_action_fields(self):
        action = FinanceAction(
            operation=FinanceOperationType.FORECAST,
            symbol="AAPL",
            horizon="30D",
        )
        assert action.horizon == "30D"

    def test_risk_level_defaults_to_medium(self):
        action = FinanceAction(
            operation=FinanceOperationType.QUOTE,
            symbol="AAPL",
        )
        assert action.risk_level == FinanceRiskLevel.MEDIUM

    def test_to_dict_includes_operation(self):
        action = FinanceAction(
            operation=FinanceOperationType.QUOTE,
            symbol="AAPL",
        )
        d = action.to_dict()
        assert d["operation"] == "quote"
        assert d["symbol"] == "AAPL"

    def test_to_dict_serializes_decimal_amount(self):
        action = FinanceAction(
            operation=FinanceOperationType.BUY,
            symbol="BTC",
            amount=Decimal("0.123"),
            currency="USD",
        )
        d = action.to_dict()
        assert d["amount"] == "0.123"


# ---------------------------------------------------------------------------
# FinanceProtocol
# ---------------------------------------------------------------------------


class TestFinanceProtocol:
    # ------------------------------------------------------------------
    # Action builders — happy path
    # ------------------------------------------------------------------

    def test_quote_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.quote("AAPL")
        assert isinstance(action, FinanceAction)
        assert action.operation == FinanceOperationType.QUOTE

    def test_buy_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.buy("BTC", amount=Decimal("1.0"), currency="USD")
        assert action.operation == FinanceOperationType.BUY
        assert action.amount == Decimal("1.0")

    def test_sell_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.sell("BTC", amount=Decimal("0.5"), currency="USD")
        assert action.operation == FinanceOperationType.SELL

    def test_transfer_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.transfer(
            from_account="acct_001",
            to_account="acct_002",
            amount=Decimal("500"),
            currency="EUR",
        )
        assert action.operation == FinanceOperationType.TRANSFER
        assert action.currency == "EUR"

    def test_balance_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.balance("acct_001")
        assert action.operation == FinanceOperationType.BALANCE

    def test_analyze_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.analyze("AAPL", period="6M")
        assert action.operation == FinanceOperationType.ANALYZE
        assert action.period == "6M"

    def test_forecast_returns_finance_action(self):
        fp = FinanceProtocol()
        action = fp.forecast("AAPL", horizon="90D")
        assert action.operation == FinanceOperationType.FORECAST
        assert action.horizon == "90D"

    # ------------------------------------------------------------------
    # Validation — required fields
    # ------------------------------------------------------------------

    def test_quote_requires_symbol(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="symbol"):
            fp.quote("")

    def test_buy_requires_positive_amount(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="amount"):
            fp.buy("BTC", amount=Decimal("0"), currency="USD")

    def test_buy_rejects_negative_amount(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="amount"):
            fp.buy("BTC", amount=Decimal("-1"), currency="USD")

    def test_buy_requires_currency(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="currency"):
            fp.buy("BTC", amount=Decimal("1"), currency="")

    def test_sell_requires_positive_amount(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="amount"):
            fp.sell("BTC", amount=Decimal("0"), currency="USD")

    def test_transfer_requires_from_account(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="from_account"):
            fp.transfer(
                from_account="",
                to_account="acct_002",
                amount=Decimal("100"),
                currency="USD",
            )

    def test_transfer_requires_to_account(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="to_account"):
            fp.transfer(
                from_account="acct_001",
                to_account="",
                amount=Decimal("100"),
                currency="USD",
            )

    def test_transfer_requires_positive_amount(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="amount"):
            fp.transfer(
                from_account="acct_001",
                to_account="acct_002",
                amount=Decimal("0"),
                currency="USD",
            )

    def test_balance_requires_account(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="account"):
            fp.balance("")

    def test_analyze_requires_symbol(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="symbol"):
            fp.analyze("", period="1Y")

    def test_forecast_requires_symbol(self):
        fp = FinanceProtocol()
        with pytest.raises(FinanceProtocolError, match="symbol"):
            fp.forecast("", horizon="30D")

    # ------------------------------------------------------------------
    # Risk level defaults
    # ------------------------------------------------------------------

    def test_quote_default_risk_is_low(self):
        fp = FinanceProtocol()
        action = fp.quote("AAPL")
        assert action.risk_level == FinanceRiskLevel.LOW

    def test_analyze_default_risk_is_low(self):
        fp = FinanceProtocol()
        action = fp.analyze("AAPL", period="1Y")
        assert action.risk_level == FinanceRiskLevel.LOW

    def test_balance_default_risk_is_low(self):
        fp = FinanceProtocol()
        action = fp.balance("acct_001")
        assert action.risk_level == FinanceRiskLevel.LOW

    def test_buy_default_risk_is_high(self):
        fp = FinanceProtocol()
        action = fp.buy("BTC", amount=Decimal("1"), currency="USD")
        assert action.risk_level == FinanceRiskLevel.HIGH

    def test_sell_default_risk_is_high(self):
        fp = FinanceProtocol()
        action = fp.sell("BTC", amount=Decimal("0.5"), currency="USD")
        assert action.risk_level == FinanceRiskLevel.HIGH

    def test_transfer_default_risk_is_high(self):
        fp = FinanceProtocol()
        action = fp.transfer(
            from_account="a", to_account="b", amount=Decimal("1"), currency="USD"
        )
        assert action.risk_level == FinanceRiskLevel.HIGH

    def test_forecast_default_risk_is_medium(self):
        fp = FinanceProtocol()
        action = fp.forecast("AAPL", horizon="30D")
        assert action.risk_level == FinanceRiskLevel.MEDIUM

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def test_history_tracks_all_actions(self):
        fp = FinanceProtocol()
        fp.quote("AAPL")
        fp.analyze("AAPL", period="1Y")
        fp.balance("acct_001")
        assert len(fp.history) == 3

    def test_clear_history(self):
        fp = FinanceProtocol()
        fp.quote("AAPL")
        fp.clear_history()
        assert fp.history == []

    def test_history_is_a_copy(self):
        fp = FinanceProtocol()
        fp.quote("AAPL")
        h = fp.history
        h.clear()
        assert len(fp.history) == 1

    def test_high_risk_count(self):
        fp = FinanceProtocol()
        fp.buy("BTC", amount=Decimal("1"), currency="USD")
        fp.sell("BTC", amount=Decimal("0.5"), currency="USD")
        fp.quote("AAPL")
        assert fp.high_risk_count == 2
