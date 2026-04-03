"""FoodOrderProvider — CapabilityProvider implementation.

Wraps ``FoodOrderSimulator`` behind the ``CapabilityProvider`` ABC so the
food-ordering example can be plugged directly into:
- LangChain via ``AicpLangChainAdapter``
- LangGraph via ``AicpLangGraphAdapter``
- AICP Workflow Engine via the DSL runner
"""

from __future__ import annotations

from typing import Any

from aicp.capability import Capability
from aicp.interfaces.capability_provider import (
    CapabilityNotFoundError,
    CapabilityProvider,
)

from food_ordering.capabilities import FoodOrderSimulator, create_menu_capabilities


class FoodOrderProvider(CapabilityProvider):
    """AICP ``CapabilityProvider`` backed by ``FoodOrderSimulator``.

    Each instance owns its own ``FoodOrderSimulator`` and therefore its own
    isolated cart / order state — there is no shared global state.
    """

    def __init__(self) -> None:
        self._simulator = FoodOrderSimulator()
        # Per-instance cart: keyed by session key (we use "default")
        self._cart: list[dict[str, Any]] = []
        self._capabilities: list[Capability] = create_menu_capabilities()
        self._cap_map: dict[str, Capability] = {
            c.name: c for c in self._capabilities
        }

    # ------------------------------------------------------------------
    # CapabilityProvider — identity
    # ------------------------------------------------------------------

    @property
    def provider_type(self) -> str:
        return "food_order"

    @property
    def provider_name(self) -> str:
        return "food-ordering"

    # ------------------------------------------------------------------
    # CapabilityProvider — discovery
    # ------------------------------------------------------------------

    async def discover(self) -> list[Capability]:
        return list(self._capabilities)

    async def get_capability(self, name: str) -> Capability | None:
        return self._cap_map.get(name)

    # ------------------------------------------------------------------
    # CapabilityProvider — execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        if capability_name not in self._cap_map:
            raise CapabilityNotFoundError(capability_name, self.provider_name)

        sim = self._simulator

        if capability_name == "food.list_menu":
            return await sim.list_menu()

        if capability_name == "food.add_to_cart":
            return await self._add_to_cart(
                item_id=arguments.get("item_id", ""),
                quantity=int(arguments.get("quantity", 1)),
            )

        if capability_name == "food.view_cart":
            return self._view_cart()

        if capability_name == "food.checkout":
            return await self._checkout(
                delivery_address=str(arguments.get("delivery_address", "")),
                payment_method=str(arguments.get("payment_method", "card")),
            )

        if capability_name == "food.clear_cart":
            return self._clear_cart()

        # Unreachable given the cap_map check above, but satisfies type checker
        raise CapabilityNotFoundError(capability_name, self.provider_name)

    # ------------------------------------------------------------------
    # Internal — instance-scoped cart operations
    # ------------------------------------------------------------------

    _MENU = [
        {"id": "burger", "name": "Classic Burger", "price": 9.99},
        {"id": "pizza", "name": "Margherita Pizza", "price": 12.99},
        {"id": "salad", "name": "Caesar Salad", "price": 7.99},
        {"id": "fries", "name": "French Fries", "price": 3.99},
        {"id": "drink", "name": "Soft Drink", "price": 1.99},
    ]

    async def _add_to_cart(self, item_id: str, quantity: int) -> dict[str, Any]:
        item = next((i for i in self._MENU if i["id"] == item_id), None)
        if not item:
            return {"error": f"Item not found: {item_id}"}
        self._cart.append({"item": item, "quantity": quantity})
        subtotal = sum(c["item"]["price"] * c["quantity"] for c in self._cart)
        return {
            "cart_item": {"item": item["name"], "quantity": quantity},
            "cart_total": round(subtotal, 2),
        }

    def _view_cart(self) -> dict[str, Any]:
        subtotal = sum(c["item"]["price"] * c["quantity"] for c in self._cart)
        tax = subtotal * 0.08
        return {
            "items": list(self._cart),
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(subtotal + tax, 2),
        }

    async def _checkout(
        self, delivery_address: str, payment_method: str
    ) -> dict[str, Any]:
        import uuid as _uuid

        if not self._cart:
            return {"error": "Cart is empty"}
        subtotal = sum(c["item"]["price"] * c["quantity"] for c in self._cart)
        total = round(subtotal * 1.08, 2)
        order_id = str(_uuid.uuid4())[:8]
        self._simulator.orders[order_id] = {
            "items": list(self._cart),
            "total": total,
            "delivery_address": delivery_address,
            "payment_method": payment_method,
            "status": "confirmed",
        }
        self._cart.clear()
        return {
            "order_id": order_id,
            "status": "confirmed",
            "estimated_delivery": "30-40 minutes",
            "total": total,
        }

    def _clear_cart(self) -> dict[str, Any]:
        self._cart.clear()
        return {"cleared": True}
