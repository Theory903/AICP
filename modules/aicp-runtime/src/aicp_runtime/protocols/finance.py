"""Finance Cognitive Protocol for AICP.

Governs how the agent performs financial analysis and transactional operations.
Every finance action the agent initiates goes through this protocol so that:
  - Financial operations are structured and auditable.
  - Required fields are enforced per operation type.
  - Amounts are validated as positive.
  - Risk levels are classified consistently (transactional ops default HIGH).
  - The agent tracks finance actions per session.

Operations:
  QUOTE     — get a market quote for a symbol (read-only, low risk)
  BUY       — purchase an asset (high risk)
  SELL      — sell an asset (high risk)
  TRANSFER  — move funds between accounts (high risk)
  BALANCE   — check account balance (read-only, low risk)
  ANALYZE   — analyze an asset's historical performance (low risk)
  FORECAST  — generate a price forecast for an asset (medium risk)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class FinanceProtocolError(Exception):
    """Raised when a Finance protocol constraint is violated."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FinanceOperationType(str, Enum):
    QUOTE = "quote"
    BUY = "buy"
    SELL = "sell"
    TRANSFER = "transfer"
    BALANCE = "balance"
    ANALYZE = "analyze"
    FORECAST = "forecast"


class FinanceRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Default risk level per operation type.
_DEFAULT_RISK: dict[FinanceOperationType, FinanceRiskLevel] = {
    FinanceOperationType.QUOTE: FinanceRiskLevel.LOW,
    FinanceOperationType.BUY: FinanceRiskLevel.HIGH,
    FinanceOperationType.SELL: FinanceRiskLevel.HIGH,
    FinanceOperationType.TRANSFER: FinanceRiskLevel.HIGH,
    FinanceOperationType.BALANCE: FinanceRiskLevel.LOW,
    FinanceOperationType.ANALYZE: FinanceRiskLevel.LOW,
    FinanceOperationType.FORECAST: FinanceRiskLevel.MEDIUM,
}


# ---------------------------------------------------------------------------
# FinanceAction
# ---------------------------------------------------------------------------


@dataclass
class FinanceAction:
    """A structured financial operation."""

    operation: FinanceOperationType
    symbol: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    from_account: Optional[str] = None
    to_account: Optional[str] = None
    period: Optional[str] = None
    horizon: Optional[str] = None
    risk_level: FinanceRiskLevel = field(default=FinanceRiskLevel.MEDIUM)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "symbol": self.symbol,
            "amount": str(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "period": self.period,
            "horizon": self.horizon,
            "risk_level": self.risk_level.value,
        }


# ---------------------------------------------------------------------------
# FinanceProtocol
# ---------------------------------------------------------------------------


class FinanceProtocol:
    """Manages structured financial actions for a session."""

    def __init__(self) -> None:
        self._history: list[FinanceAction] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[FinanceAction]:
        return list(self._history)

    @property
    def high_risk_count(self) -> int:
        return sum(1 for a in self._history if a.risk_level == FinanceRiskLevel.HIGH)

    # ------------------------------------------------------------------
    # Action builders
    # ------------------------------------------------------------------

    def quote(self, symbol: str) -> FinanceAction:
        """Create a QUOTE action (read-only, low risk)."""
        self._validate_symbol(symbol)
        action = FinanceAction(
            operation=FinanceOperationType.QUOTE,
            symbol=symbol,
            risk_level=_DEFAULT_RISK[FinanceOperationType.QUOTE],
        )
        self._record(action)
        return action

    def buy(self, symbol: str, amount: Decimal, currency: str) -> FinanceAction:
        """Create a BUY action (requires positive amount and currency)."""
        self._validate_symbol(symbol)
        self._validate_amount(amount)
        self._validate_currency(currency)
        action = FinanceAction(
            operation=FinanceOperationType.BUY,
            symbol=symbol,
            amount=amount,
            currency=currency,
            risk_level=_DEFAULT_RISK[FinanceOperationType.BUY],
        )
        self._record(action)
        return action

    def sell(self, symbol: str, amount: Decimal, currency: str) -> FinanceAction:
        """Create a SELL action (requires positive amount and currency)."""
        self._validate_symbol(symbol)
        self._validate_amount(amount)
        self._validate_currency(currency)
        action = FinanceAction(
            operation=FinanceOperationType.SELL,
            symbol=symbol,
            amount=amount,
            currency=currency,
            risk_level=_DEFAULT_RISK[FinanceOperationType.SELL],
        )
        self._record(action)
        return action

    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: Decimal,
        currency: str,
    ) -> FinanceAction:
        """Create a TRANSFER action."""
        if not from_account or not from_account.strip():
            raise FinanceProtocolError("from_account must not be empty")
        if not to_account or not to_account.strip():
            raise FinanceProtocolError("to_account must not be empty")
        self._validate_amount(amount)
        self._validate_currency(currency)
        action = FinanceAction(
            operation=FinanceOperationType.TRANSFER,
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            currency=currency,
            risk_level=_DEFAULT_RISK[FinanceOperationType.TRANSFER],
        )
        self._record(action)
        return action

    def balance(self, account: str) -> FinanceAction:
        """Create a BALANCE action (read-only, low risk)."""
        if not account or not account.strip():
            raise FinanceProtocolError("account must not be empty")
        action = FinanceAction(
            operation=FinanceOperationType.BALANCE,
            from_account=account,
            risk_level=_DEFAULT_RISK[FinanceOperationType.BALANCE],
        )
        self._record(action)
        return action

    def analyze(self, symbol: str, period: str = "1Y") -> FinanceAction:
        """Create an ANALYZE action (read-only, low risk)."""
        self._validate_symbol(symbol)
        action = FinanceAction(
            operation=FinanceOperationType.ANALYZE,
            symbol=symbol,
            period=period,
            risk_level=_DEFAULT_RISK[FinanceOperationType.ANALYZE],
        )
        self._record(action)
        return action

    def forecast(self, symbol: str, horizon: str = "30D") -> FinanceAction:
        """Create a FORECAST action (medium risk)."""
        self._validate_symbol(symbol)
        action = FinanceAction(
            operation=FinanceOperationType.FORECAST,
            symbol=symbol,
            horizon=horizon,
            risk_level=_DEFAULT_RISK[FinanceOperationType.FORECAST],
        )
        self._record(action)
        return action

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_symbol(self, symbol: str) -> None:
        if not symbol or not symbol.strip():
            raise FinanceProtocolError("symbol must not be empty")

    def _validate_amount(self, amount: Decimal) -> None:
        if amount is None or amount <= Decimal("0"):
            raise FinanceProtocolError(
                f"amount must be a positive value, got: {amount}"
            )

    def _validate_currency(self, currency: str) -> None:
        if not currency or not currency.strip():
            raise FinanceProtocolError("currency must not be empty")

    def _record(self, action: FinanceAction) -> None:
        self._history.append(action)
