"""Event-driven order confirmation flow.

Demonstrates ``EventWaiter`` for the food-ordering example:

1. A checkout is performed (via ``FoodOrderProvider``).
2. The flow waits for an ``"order.confirmed"`` event.
3. A background task publishes the event (simulating an external system).
4. The flow receives the event payload and returns it.

This is a reference demonstration — not production code.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aicp_runtime.workflow.events import EventWaiter

from food_ordering.provider import FoodOrderProvider


async def run_event_flow(
    *,
    item_id: str = "burger",
    quantity: int = 1,
    delivery_address: str = "1 Test Lane",
    payment_method: str = "card",
    timeout_ms: int = 5_000,
) -> dict[str, Any]:
    """Run the event-driven food order confirmation flow.

    Steps
    -----
    1. Set up a ``FoodOrderProvider`` and add an item to the cart.
    2. Checkout to get an ``order_id``.
    3. Create an ``EventWaiter`` for this workflow run.
    4. Concurrently:
       - Wait for the ``"order.confirmed"`` event.
       - Publish that event (simulating an external confirmation system).
    5. Return the received event name + payload.

    Parameters
    ----------
    item_id:
        Menu item to add before checkout.
    quantity:
        Quantity of the item.
    delivery_address:
        Delivery address passed to checkout.
    payment_method:
        Payment method passed to checkout.
    timeout_ms:
        How long to wait for the event before raising ``EventTimeoutError``.

    Returns
    -------
    dict with keys ``event_name`` and ``payload``.
    """
    provider = FoodOrderProvider()

    # --- Step 1: Build cart ---
    await provider.execute(
        "food.add_to_cart", {"item_id": item_id, "quantity": quantity}
    )

    # --- Step 2: Checkout ---
    checkout_result = await provider.execute(
        "food.checkout",
        {"delivery_address": delivery_address, "payment_method": payment_method},
    )
    order_id: str = checkout_result["order_id"]

    # --- Step 3: Set up EventWaiter ---
    waiter = EventWaiter(workflow_id=f"wf_{order_id}")

    # --- Step 4: Concurrently wait + publish ---
    async def _publish_confirmation() -> None:
        """Simulate an external system confirming the order after a short delay."""
        await asyncio.sleep(0.05)  # 50 ms simulated latency
        await waiter.publish_event(
            "order.confirmed",
            {"order_id": order_id, "status": "confirmed"},
        )

    received_payload, _ = await asyncio.gather(
        waiter.wait_for_event("order.confirmed", timeout_ms=timeout_ms),
        _publish_confirmation(),
    )

    return {
        "event_name": "order.confirmed",
        "payload": received_payload,
    }
