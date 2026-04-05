"""FastAPI server with AICP capabilities.

A real-world example of exposing AICP capabilities via HTTP.
"""

import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from aicp.adapters.framework.fastapi import mount_aicp

app = FastAPI(title="AICP FastAPI Demo")

# Mount AICP on the FastAPI app
mount_aicp(app)

# In-memory storage
orders: dict[str, dict] = {}
menu_items = [
    {"id": "burger", "name": "Classic Burger", "price": 9.99},
    {"id": "pizza", "name": "Margherita Pizza", "price": 12.99},
    {"id": "salad", "name": "Caesar Salad", "price": 7.99},
]


class OrderRequest(BaseModel):
    item_id: str
    quantity: int = 1
    delivery_address: str


class OrderResponse(BaseModel):
    order_id: str
    item: dict
    quantity: int
    total: float
    delivery_address: str
    status: str


@app.get("/")
async def root():
    return {"message": "AICP FastAPI Demo Server"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# AICP-style discovery endpoint
@app.get("/.well-known/aicp")
async def aicp_discovery():
    """AICP Discovery endpoint - lists all available capabilities."""
    return {
        "version": "0.3.0",
        "capabilities": [
            {
                "name": "food.list_menu",
                "description": "List available menu items",
                "kind": "query",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                    },
                },
                "continuation": {
                    "can_continue": True,
                    "next_capabilities": ["food.create_order"],
                    "next_hint": "Use food.create_order to place an order",
                },
            },
            {
                "name": "food.create_order",
                "description": "Create a food order",
                "kind": "action",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1},
                        "delivery_address": {"type": "string"},
                    },
                    "required": ["item_id", "delivery_address"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "item": {"type": "object"},
                        "quantity": {"type": "integer"},
                        "total": {"type": "number"},
                        "delivery_address": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
                "continuation": {
                    "can_continue": False,
                },
            },
            {
                "name": "food.get_order",
                "description": "Get order by ID",
                "kind": "query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                    },
                    "required": ["order_id"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "item": {"type": "object"},
                        "quantity": {"type": "integer"},
                        "total": {"type": "number"},
                        "delivery_address": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
        ],
    }


# AICP-style capability endpoints
@app.get("/capabilities/food.list_menu")
async def list_menu():
    """List available menu items."""
    return {
        "items": menu_items,
    }


@app.post("/capabilities/food.create_order")
async def create_order(request: OrderRequest) -> OrderResponse:
    """Create a food order."""
    item = next((i for i in menu_items if i["id"] == request.item_id), None)
    if not item:
        raise HTTPException(
            status_code=404, detail=f"Item not found: {request.item_id}"
        )

    total = item["price"] * request.quantity
    order_id = str(uuid.uuid4())[:8]

    order = {
        "order_id": order_id,
        "item": item,
        "quantity": request.quantity,
        "total": total,
        "delivery_address": request.delivery_address,
        "status": "confirmed",
    }
    orders[order_id] = order

    return OrderResponse(**order)


@app.get("/capabilities/food.get_order")
async def get_order(order_id: str):
    """Get order by ID."""
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    return order


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
