"""Food Ordering Capabilities.

Demonstrates multi-step workflow with policy and continuation hints.
"""

import uuid
from typing import Any

from aicp import Capability, CapabilityKind
from aicp.capability import ContinuationSpec, RenderSpec


MENU = [
    {"id": "burger", "name": "Classic Burger", "price": 9.99},
    {"id": "pizza", "name": "Margherita Pizza", "price": 12.99},
    {"id": "salad", "name": "Caesar Salad", "price": 7.99},
    {"id": "fries", "name": "French Fries", "price": 3.99},
    {"id": "drink", "name": "Soft Drink", "price": 1.99},
]

CART: dict[str, list] = {}


def create_menu_capabilities() -> list[Capability]:
    return [
        Capability(
            name="food.list_menu",
            description="List available menu items",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {},
            },
            output_schema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                            },
                        },
                    },
                },
            },
            render=RenderSpec(
                format="table",
                fields=["id", "name", "price"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["food.add_to_cart"],
                next_hint="Use food.add_to_cart to order items",
            ),
        ),
        Capability(
            name="food.add_to_cart",
            description="Add an item to the cart",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "Menu item ID"},
                    "quantity": {"type": "integer", "minimum": 1, "default": 1},
                },
                "required": ["item_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "cart_item": {"type": "object"},
                    "cart_total": {"type": "number"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["cart_item", "cart_total"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["food.view_cart", "food.checkout"],
                next_hint="View cart or proceed to checkout",
            ),
        ),
        Capability(
            name="food.view_cart",
            description="View current cart contents",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {},
            },
            output_schema={
                "type": "object",
                "properties": {
                    "items": {"type": "array"},
                    "subtotal": {"type": "number"},
                    "tax": {"type": "number"},
                    "total": {"type": "number"},
                },
            },
            render=RenderSpec(
                format="table",
                fields=["item", "quantity", "price", "total"],
            ),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["food.checkout"],
                next_hint="Proceed to checkout when ready",
            ),
        ),
        Capability(
            name="food.checkout",
            description="Process the order (requires confirmation for orders over $20)",
            kind=CapabilityKind.ACTION,
            policy={
                "policy_name": "high_value_order_confirmation",
                "parameters": {},
            },
            input_schema={
                "type": "object",
                "properties": {
                    "delivery_address": {"type": "string"},
                    "payment_method": {"type": "string", "enum": ["card", "cash"]},
                },
                "required": ["delivery_address", "payment_method"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "status": {"type": "string"},
                    "estimated_delivery": {"type": "string"},
                    "total": {"type": "number"},
                },
            },
            render=RenderSpec(
                format="text",
                fields=["order_id", "status", "estimated_delivery", "total"],
            ),
            continuation=ContinuationSpec(
                can_continue=False,
                next_hint="Order complete! Thank you for your purchase.",
            ),
        ),
        Capability(
            name="food.clear_cart",
            description="Clear all items from cart",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {},
            },
            output_schema={
                "type": "object",
                "properties": {
                    "cleared": {"type": "boolean"},
                },
            },
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["food.list_menu"],
                next_hint="Browse the menu to order again",
            ),
        ),
    ]


class FoodOrderSimulator:
    """Simulates a food ordering backend."""

    def __init__(self):
        self.orders: dict[str, dict] = {}

    async def list_menu(self) -> dict[str, Any]:
        return {"items": MENU}

    async def add_to_cart(self, item_id: str, quantity: int = 1) -> dict[str, Any]:
        item = next((i for i in MENU if i["id"] == item_id), None)
        if not item:
            return {"error": f"Item not found: {item_id}"}

        cart = CART.setdefault("default", [])
        cart.append({"item": item, "quantity": quantity})

        subtotal = sum(c["item"]["price"] * c["quantity"] for c in cart)

        return {
            "cart_item": {"item": item["name"], "quantity": quantity},
            "cart_total": subtotal,
        }

    async def view_cart(self) -> dict[str, Any]:
        cart = CART.get("default", [])
        subtotal = sum(c["item"]["price"] * c["quantity"] for c in cart)
        tax = subtotal * 0.08
        return {
            "items": cart,
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(subtotal + tax, 2),
        }

    async def checkout(
        self, delivery_address: str, payment_method: str
    ) -> dict[str, Any]:
        cart = CART.get("default", [])
        if not cart:
            return {"error": "Cart is empty"}

        subtotal = sum(c["item"]["price"] * c["quantity"] for c in cart)
        total = round(subtotal * 1.08, 2)

        order_id = str(uuid.uuid4())[:8]
        self.orders[order_id] = {
            "items": cart,
            "total": total,
            "delivery_address": delivery_address,
            "payment_method": payment_method,
            "status": "confirmed",
        }

        CART["default"] = []

        return {
            "order_id": order_id,
            "status": "confirmed",
            "estimated_delivery": "30-40 minutes",
            "total": total,
        }

    async def clear_cart(self) -> dict[str, Any]:
        CART["default"] = []
        return {"cleared": True}
