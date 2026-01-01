"""Payment Transfer Demo.

Demonstrates policy-driven payment execution.
"""

import asyncio
import json

from aicp import AicpRegistry, Policy, PolicyEffect, PolicySubject, PolicyCondition
from payment_transfer.capabilities import create_payment_capabilities, PaymentSimulator


async def main():
    print("=" * 60)
    print("AICP Payment Transfer Demo")
    print("=" * 60)

    # Set up
    simulator = PaymentSimulator()
    registry = AicpRegistry()

    # Register capabilities
    for cap in create_payment_capabilities():
        registry.register_capability(cap)

    # Register policies
    registry.register_policy(
        Policy(
            name="transfer_confirmation",
            description="Transfers over $100 require confirmation",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
    )

    registry.register_policy(
        Policy(
            name="daily_limit",
            description="Maximum $1000 per day",
            effect=PolicyEffect.LIMIT,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(max_amount=1000),
        )
    )

    # Show capabilities and policies
    print("\n1. AVAILABLE CAPABILITIES")
    print("-" * 40)
    for cap in registry.list_capabilities():
        print(f"  - {cap.name}: {cap.description}")

    print("\n2. POLICIES")
    print("-" * 40)
    for pol in registry.list_policies():
        print(f"  - {pol.name}: {pol.description}")
        print(f"    Effect: {pol.effect}")

    # Execute workflow
    print("\n3. PAYMENT WORKFLOW")
    print("-" * 40)

    # Check balance
    print("\n  Step 1: Check balance (user123)")
    result = await simulator.get_balance("user123")
    print(f"    Balance: ${result['balance']} {result['currency']}")
    print("    Hint: Transfer funds using payments.transfer")

    # Small transfer (no confirmation needed)
    print("\n  Step 2: Transfer $50 (under $100 - no confirmation)")
    result = await simulator.transfer("user123", "merchant456", 50.00)
    print(f"    Result: {json.dumps(result, indent=4)}")
    print("    Hint: View transaction history")

    # Large transfer (requires confirmation)
    print("\n  Step 3: Transfer $200 (over $100 - requires confirmation)")
    print("    Policy check: 'transfer_confirmation' triggers ASK effect")
    print("    (Simulated user confirmation)")
    result = await simulator.transfer("user123", "merchant456", 200.00)
    print(f"    Result: {json.dumps(result, indent=4)}")

    # Get transactions
    print("\n  Step 4: View transaction history")
    result = await simulator.get_transactions("user123")
    print("    Transactions:")
    for tx in result["transactions"]:
        print(f"      - {tx['id']}: ${tx['amount']} to {tx['to']}")

    print("\n4. FINAL BALANCES")
    print("-" * 40)
    for acc_id in ["user123", "merchant456"]:
        result = await simulator.get_balance(acc_id)
        print(f"  {acc_id}: ${result['balance']} {result['currency']}")

    print("\n5. CAPABILITY WITH CONTINUATION")
    print("-" * 40)
    cap = registry.get_capability("payments.transfer")
    print(f"  {cap.name}:")
    print(f"    can_continue: {cap.continuation.can_continue}")
    print(f"    next_capabilities: {cap.continuation.next_capabilities}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
