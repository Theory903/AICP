"""Payment Transfer Demo.

Demonstrates full approval workflow with policy thresholds, approval requests, and audit trails.
"""

import asyncio

from aicp import AicpRegistry, Policy, PolicyEffect, PolicySubject, PolicyCondition
from payment_transfer.capabilities import (
    create_payment_capabilities,
    PaymentSimulator,
    ApprovalSimulator,
)

APPROVAL_THRESHOLD = 1000.0


async def main():
    print("=" * 70)
    print("AICP Payment Transfer - Full Approval Flow Demo")
    print("=" * 70)

    simulator = PaymentSimulator()
    approval_sim = ApprovalSimulator()
    registry = AicpRegistry()

    for cap in create_payment_capabilities():
        registry.register_capability(cap)

    registry.register_policy(
        Policy(
            name="high_value_approval",
            description=f"Transfers over ${APPROVAL_THRESHOLD} require approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
    )

    registry.register_policy(
        Policy(
            name="daily_limit",
            description="Maximum $5000 per day",
            effect=PolicyEffect.LIMIT,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(max_amount=5000),
        )
    )

    print("\n1. AVAILABLE CAPABILITIES")
    print("-" * 50)
    for cap in registry.list_capabilities():
        print(f"  - {cap.name}")

    print("\n2. POLICIES")
    print("-" * 50)
    for pol in registry.list_policies():
        print(f"  - {pol.name}: {pol.description}")
        print(f"    Effect: {pol.effect}")

    print("\n3. INITIAL STATE")
    print("-" * 50)
    result = await simulator.get_balance("user123")
    print(f"  user123 balance: ${result['balance']} {result['currency']}")
    result = await simulator.get_balance("merchant456")
    print(f"  merchant456 balance: ${result['balance']} {result['currency']}")

    print("\n4. TRANSFER WORKFLOW")
    print("-" * 50)

    print(
        "\n  [4.1] Transfer $500 (under ${} - no approval needed)".format(
            APPROVAL_THRESHOLD
        )
    )
    result = await simulator.transfer("user123", "merchant456", 500.00)
    print(f"      Status: {result.get('status', 'completed')}")
    print(f"      Transaction ID: {result.get('id')}")

    print(
        "\n  [4.2] Transfer $2,000 (OVER ${} - requires approval!)".format(
            APPROVAL_THRESHOLD
        )
    )
    print("      Policy: high_value_approval triggers ASK effect")

    transfer_args = {
        "from_account": "user123",
        "to_account": "merchant456",
        "amount": 2000.00,
    }

    approval_req = approval_sim.create_approval_request(
        capability="payments.transfer",
        arguments=transfer_args,
        amount=2000.00,
        requester="user123",
    )
    print(f"      Approval Request Created: {approval_req.id}")
    print(f"      Status: {approval_req.status}")

    print("\n  [4.3] Check pending approvals")
    pending = approval_sim.list_pending_requests()
    print(f"      Pending requests: {len(pending)}")
    for p in pending:
        print(f"        - {p.id}: ${p.amount} ({p.status})")

    print("\n  [4.4] Approve the request (as manager)")
    approved = approval_sim.approve_request(
        approval_req.id,
        approver="manager1",
        reason="Verified with customer via phone",
    )
    print(f"      Approved: {approved.id}")
    print(f"      Status: {approved.status}")
    print(f"      Approver: {approved.approver}")

    result = await simulator.transfer("user123", "merchant456", 2000.00)
    print(f"      Transfer completed: {result.get('id')}")

    print("\n  [4.5] Reject workflow demo (another high-value transfer)")
    transfer_args2 = {
        "from_account": "user123",
        "to_account": "merchant456",
        "amount": 5000.00,
    }
    approval_req2 = approval_sim.create_approval_request(
        capability="payments.transfer",
        arguments=transfer_args2,
        amount=5000.00,
        requester="user123",
    )
    print(f"      Approval Request: {approval_req2.id}")

    rejected = approval_sim.reject_request(
        approval_req2.id,
        approver="manager1",
        reason="Suspicious activity - requires additional verification",
    )
    print(f"      Rejected: {rejected.id}")
    print(f"      Status: {rejected.status}")
    print(f"      Reason: {rejected.reason}")

    print("\n5. AUDIT TRAIL")
    print("-" * 50)
    audit_entries = approval_sim.get_audit_trail()
    print(f"  Total audit entries: {len(audit_entries)}")
    for entry in audit_entries:
        print(f"    [{entry.timestamp[:19]}] {entry.action} by {entry.user}")

    print("\n6. FINAL STATE")
    print("-" * 50)
    result = await simulator.get_balance("user123")
    print(f"  user123 balance: ${result['balance']} {result['currency']}")
    result = await simulator.get_balance("merchant456")
    print(f"  merchant456 balance: ${result['balance']} {result['currency']}")

    result = await simulator.get_transactions("user123")
    print(f"\n  Transactions: {len(result['transactions'])}")
    for tx in result["transactions"]:
        print(f"    - {tx['id']}: ${tx['amount']} -> {tx['to']} ({tx['status']})")

    print("\n7. CAPABILITY CONTINUATION CHAINS")
    print("-" * 50)
    cap = registry.get_capability("payments.transfer")
    print(f"  {cap.name}:")
    print(f"    can_continue: {cap.continuation.can_continue}")
    print(f"    next_capabilities: {cap.continuation.next_capabilities}")

    cap = registry.get_capability("payments.approve_request")
    print(f"\n  {cap.name}:")
    print(f"    can_continue: {cap.continuation.can_continue}")
    print(f"    next_capabilities: {cap.continuation.next_capabilities}")

    print("\n" + "=" * 70)
    print("Demo Complete! Full approval flow demonstrated:")
    print("  - Threshold policy (${})".format(APPROVAL_THRESHOLD))
    print("  - Approval request creation")
    print("  - Approve/Reject workflow")
    print("  - Audit trail logging")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
