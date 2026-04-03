"""Payment Transfer Capabilities.

Demonstrates policy-driven execution with approval workflows, thresholds, and audit trails.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from aicp import (
    Capability,
    CapabilityKind,
    RenderSpec,
    ContinuationSpec,
)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest(BaseModel):
    id: str
    capability: str
    arguments: dict[str, Any]
    amount: float
    requester: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: str | None = None
    reason: str | None = None
    created_at: str = ""
    resolved_at: str | None = None


class AuditEntry(BaseModel):
    id: str
    timestamp: str
    action: str
    user: str
    details: dict[str, Any]


class ApprovalSimulator:
    """Manages approval requests and audit trail."""

    def __init__(self):
        self.approval_requests: dict[str, ApprovalRequest] = {}
        self.audit_trail: list[AuditEntry] = []

    def log_audit(self, action: str, user: str, details: dict[str, Any]) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            action=action,
            user=user,
            details=details,
        )
        self.audit_trail.append(entry)
        return entry

    def create_approval_request(
        self,
        capability: str,
        arguments: dict[str, Any],
        amount: float,
        requester: str,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            id=str(uuid.uuid4())[:8],
            capability=capability,
            arguments=arguments,
            amount=amount,
            requester=requester,
            created_at=datetime.now().isoformat(),
        )
        self.approval_requests[request.id] = request
        self.log_audit(
            "approval_requested",
            requester,
            {
                "request_id": request.id,
                "capability": capability,
                "amount": amount,
            },
        )
        return request

    def get_approval_request(self, request_id: str) -> ApprovalRequest | None:
        return self.approval_requests.get(request_id)

    def list_pending_requests(self) -> list[ApprovalRequest]:
        return [
            req
            for req in self.approval_requests.values()
            if req.status == ApprovalStatus.PENDING
        ]

    def approve_request(
        self,
        request_id: str,
        approver: str,
        reason: str | None = None,
    ) -> ApprovalRequest | dict[str, Any]:
        request = self.approval_requests.get(request_id)
        if not request:
            return {"error": f"Approval request not found: {request_id}"}
        if request.status != ApprovalStatus.PENDING:
            return {"error": f"Request already resolved: {request.status}"}

        request.status = ApprovalStatus.APPROVED
        request.approver = approver
        request.reason = reason
        request.resolved_at = datetime.now().isoformat()

        self.log_audit(
            "approval_approved",
            approver,
            {
                "request_id": request_id,
                "reason": reason,
            },
        )
        return request

    def reject_request(
        self,
        request_id: str,
        approver: str,
        reason: str,
    ) -> ApprovalRequest | dict[str, Any]:
        request = self.approval_requests.get(request_id)
        if not request:
            return {"error": f"Approval request not found: {request_id}"}
        if request.status != ApprovalStatus.PENDING:
            return {"error": f"Request already resolved: {request.status}"}

        request.status = ApprovalStatus.REJECTED
        request.approver = approver
        request.reason = reason
        request.resolved_at = datetime.now().isoformat()

        self.log_audit(
            "approval_rejected",
            approver,
            {
                "request_id": request_id,
                "reason": reason,
            },
        )
        return request

    def get_audit_trail(self, user: str | None = None) -> list[AuditEntry]:
        if user:
            return [e for e in self.audit_trail if e.user == user]
        return self.audit_trail


class PaymentSimulator:
    """Simulates a payment system."""

    def __init__(self):
        self.accounts = {
            "user123": {"balance": 10000.00, "currency": "USD"},
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
            description="Transfer funds between accounts (requires approval over $1000)",
            kind=CapabilityKind.ACTION,
            policy={
                "policy_name": "high_value_approval",
                "parameters": {},
            },
            input_schema={
                "type": "object",
                "properties": {
                    "from_account": {"type": "string"},
                    "to_account": {"type": "string"},
                    "amount": {"type": "number", "minimum": 0.01, "maximum": 100000},
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
                    "approval_required": {"type": "boolean"},
                    "approval_request_id": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["id", "amount", "status", "approval_required"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=[
                    "payments.get_transactions",
                    "payments.approve_request",
                ],
                next_hint="View transaction history or approve pending requests",
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
        Capability(
            name="payments.request_approval",
            description="Request approval for a high-value transfer",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "capability": {"type": "string"},
                    "arguments": {"type": "object"},
                    "amount": {"type": "number"},
                    "requester": {"type": "string"},
                },
                "required": ["capability", "arguments", "amount", "requester"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "capability": {"type": "string"},
                    "amount": {"type": "number"},
                    "status": {"type": "string"},
                    "created_at": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["id", "amount", "status"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.list_pending", "payments.approve_request"],
                next_hint="List pending approvals or approve the request",
            ),
        ),
        Capability(
            name="payments.list_pending",
            description="List all pending approval requests",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {},
            },
            output_schema={
                "type": "object",
                "properties": {
                    "requests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "capability": {"type": "string"},
                                "amount": {"type": "number"},
                                "requester": {"type": "string"},
                                "status": {"type": "string"},
                            },
                        },
                    },
                },
            },
            render=RenderSpec(
                format="table",
                table_columns=["id", "capability", "amount", "requester", "status"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=[
                    "payments.approve_request",
                    "payments.reject_request",
                ],
                next_hint="Approve or reject pending requests",
            ),
        ),
        Capability(
            name="payments.approve_request",
            description="Approve a pending transfer request",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "approver": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["request_id", "approver"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string"},
                    "approver": {"type": "string"},
                    "resolved_at": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["id", "status", "approver"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.list_pending", "payments.get_audit_trail"],
                next_hint="View more pending requests or audit trail",
            ),
        ),
        Capability(
            name="payments.reject_request",
            description="Reject a pending transfer request",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "approver": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["request_id", "approver", "reason"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string"},
                    "approver": {"type": "string"},
                    "resolved_at": {"type": "string"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["id", "status", "approver"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.list_pending", "payments.get_audit_trail"],
                next_hint="View more pending requests or audit trail",
            ),
        ),
        Capability(
            name="payments.get_audit_trail",
            description="Get audit trail for all operations (admin only)",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "user": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "timestamp": {"type": "string"},
                                "action": {"type": "string"},
                                "user": {"type": "string"},
                            },
                        },
                    },
                },
            },
            render=RenderSpec(
                format="table",
                table_columns=["timestamp", "action", "user", "id"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["payments.list_pending"],
                next_hint="View pending approval requests",
            ),
        ),
    ]
