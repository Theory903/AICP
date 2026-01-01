"""Payment Transfer Capabilities.

Demonstrates policy-driven execution with amount limits and confirmations.
"""

import uuid
from datetime import datetime
from typing import Any

from aicp import (
    Capability,
    CapabilityKind,
    RenderSpec,
    ContinuationSpec,
)


class PaymentSimulator:
    """Simulates a payment system."""

    def __init__(self):
        self.accounts = {
            "user123": {"balance": 1000.00, "currency": "USD"},
            "merchant456": {"balance": 5000.00, "currency": "USD"},
        }
        self.transactions = []

    async def get_balance(self, account_id: str) -> dict[str, Any]:
        account = self.accounts.get(account_id)
        if not account:
            return {"error": f"Account not found: {account_id}"}
        return account

    async def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
    ) -> dict[str, Any]:
        if from_account not in self.accounts:
            return {"error": f"Source account not found: {from_account}"}
        if to_account not in self.accounts:
            return {"error": f"Destination account not found: {to_account}"}

        from_acc = self.accounts[from_account]
        if from_acc["balance"] < amount:
            return {"error": f"Insufficient funds. Available: {from_acc['balance']}"}

        from_acc["balance"] -= amount
        self.accounts[to_account]["balance"] += amount

        tx_id = str(uuid.uuid4())[:8]
        tx = {
            "id": tx_id,
            "from": from_account,
            "to": to_account,
            "amount": amount,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        }
        self.transactions.append(tx)

        return tx

    async def get_transactions(self, account_id: str) -> dict[str, Any]:
        txs = [
            t
            for t in self.transactions
            if t["from"] == account_id or t["to"] == account_id
        ]
        return {"transactions": txs}


def create_payment_capabilities() -> list[Capability]:
    return [
        Capability(
            name="payments.get_balance",
            description="Check account balance",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Account identifier",
                    },
                },
                "required": ["account_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "balance": {"type": "number"},
                    "currency": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["balance", "currency"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.transfer"],
                next_hint="Use payments.transfer to send money",
            ),
        ),
        Capability(
            name="payments.transfer",
            description="Transfer funds between accounts (requires confirmation over $100)",
            kind=CapabilityKind.ACTION,
            policy={
                "policy_name": "transfer_confirmation",
                "parameters": {},
            },
            input_schema={
                "type": "object",
                "properties": {
                    "from_account": {"type": "string"},
                    "to_account": {"type": "string"},
                    "amount": {"type": "number", "minimum": 0.01, "maximum": 10000},
                },
                "required": ["from_account", "to_account", "amount"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["id", "amount", "status"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.get_transactions"],
                next_hint="View transaction history with payments.get_transactions",
            ),
        ),
        Capability(
            name="payments.get_transactions",
            description="Get transaction history for an account",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                },
                "required": ["account_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "amount": {"type": "number"},
                                "timestamp": {"type": "string"},
                            },
                        },
                    },
                },
            },
            render=RenderSpec(
                format="table",
                table_columns=["id", "from", "to", "amount", "timestamp"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.transfer", "payments.get_balance"],
                next_hint="Make another transfer or check balance",
            ),
        ),
    ]
