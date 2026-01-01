"""Food Ordering Demo.

Demonstrates AICP capabilities with the food ordering workflow.
"""

import asyncio
import json

from aicp import AicpRegistry
from aicp.interfaces.policy_engine import (
    Policy,
    PolicyEffect,
    PolicySubject,
    PolicyCondition,
)

from food_ordering.capabilities import (
    create_menu_capabilities,
    FoodOrderSimulator,
)


async def main():
    print("=" * 60)
    print("AICP Food Ordering Demo")
    print("=" * 60)

    # Set up the system
    simulator = FoodOrderSimulator()

    # Create registry
    registry = AicpRegistry()

    # Register capabilities
    for cap in create_menu_capabilities():
        registry.register_capability(cap)

    # Register policy for high-value orders
    policy = Policy(
        name="high_value_order_confirmation",
        description="Orders over $20 require confirmation",
        effect=PolicyEffect.ASK,
        subject=PolicySubject(capability_name="food.checkout"),
        condition=PolicyCondition(require_confirmation=True),
    )
    registry.register_policy(policy)

    # Show discovery
    print("\n1. DISCOVERY - Available Capabilities")
    print("-" * 40)
    discovery = registry.discovery_response()
    for cap in discovery["capabilities"]:
        print(f"  - {cap['name']}: {cap['description']}")

    # Show policy
    print("\n2. POLICIES")
    print("-" * 40)
    for pol in discovery["policies"]:
        print(f"  - {pol['name']}: {pol['description']}")
        print(f"    Effect: {pol['effect']}")
        print(f"    Subject: {pol['subject']}")

    # Execute each capability step manually
    print("\n3. EXECUTE CAPABILITIES - Step by Step")
    print("-" * 40)

    # Step 1: List menu
    print("\n  Step 1: food.list_menu")
    result = await simulator.list_menu()
    print(f"    Result: {json.dumps(result, indent=4)}")
    print("    Hint: Use food.add_to_cart to order items")

    # Step 2: Add burger to cart
    print("\n  Step 2: food.add_to_cart (2x burgers)")
    result = await simulator.add_to_cart("burger", 2)
    print(f"    Result: {json.dumps(result, indent=4)}")
    print("    Hint: Continue adding items or view cart")

    # Step 3: Add fries
    print("\n  Step 3: food.add_to_cart (fries)")
    result = await simulator.add_to_cart("fries", 1)
    print(f"    Result: {json.dumps(result, indent=4)}")

    # Step 4: View cart
    print("\n  Step 4: food.view_cart")
    result = await simulator.view_cart()
    print(f"    Result: {json.dumps(result, indent=4)}")
    print("    Total: $", result.get("total", 0))
    print("    Hint: Proceed to checkout when ready")

    # Step 5: Checkout (would require policy check)
    print("\n  Step 5: food.checkout")
    print("    Policy: Would check high_value_order_confirmation")
    print("    Order total ($21.97) > $20 threshold → requires confirmation")
    print("    (Simulated confirmation)")

    result = await simulator.checkout("123 Main St", "card")
    print(f"    Result: {json.dumps(result, indent=4)}")

    # Show final discovery response
    print("\n4. DISCOVERY RESPONSE")
    print("-" * 40)
    final_discovery = registry.discovery_response()
    print(f"  Capabilities: {final_discovery['metadata']['capability_count']}")
    print(f"  Policies: {final_discovery['metadata']['policy_count']}")

    # Show capability continuation hints
    print("\n5. CAPABILITY CONTINUATION HINTS")
    print("-" * 40)
    cap = registry.get_capability("food.list_menu")
    print(f"  {cap.name}:")
    print(
        f"    can_continue: {cap.continuation.can_continue if cap.continuation else False}"
    )
    print(
        f"    next_capabilities: {cap.continuation.next_capabilities if cap.continuation else []}"
    )
    print(f"    next_hint: {cap.continuation.next_hint if cap.continuation else None}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
