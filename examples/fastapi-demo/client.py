"""AICP Client for FastAPI Demo.

Tests the FastAPI server using AICP HTTP adapter.
"""

import asyncio

from aicp import Capability, CapabilityKind, RenderSpec, ContinuationSpec
from aicp.adapters import HttpExecutionAdapter


async def main():
    print("=" * 60)
    print("AICP FastAPI Client Demo")
    print("=" * 60)

    # Create AICP capabilities that match the FastAPI endpoints
    capabilities = [
        Capability(
            name="food.list_menu",
            description="List available menu items",
            kind=CapabilityKind.QUERY,
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {"items": {"type": "array"}},
            },
            render=RenderSpec(format="table"),
            continuation=ContinuationSpec(
                can_continue=True,
                next_capabilities=["food.create_order"],
                next_hint="Use food.create_order to place an order",
            ),
        ),
        Capability(
            name="food.create_order",
            description="Create a food order",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "delivery_address": {"type": "string"},
                },
                "required": ["item_id", "delivery_address"],
            },
            output_schema={
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
            render=RenderSpec(format="text"),
        ),
        Capability(
            name="food.get_order",
            description="Get order by ID",
            kind=CapabilityKind.QUERY,
            input_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        ),
    ]

    # Create HTTP adapter
    base_url = "http://localhost:8000"
    adapter = HttpExecutionAdapter(
        name="fastapi_demo",
        base_url=base_url,
        capabilities=capabilities,
        default_headers={"Content-Type": "application/json"},
    )

    # Override execute to use correct URL paths
    original_execute = adapter.execute

    async def custom_execute(capability_name, arguments, context=None):
        if capability_name == "food.list_menu":
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/capabilities/food.list_menu"
                ) as resp:
                    return await resp.json()
        elif capability_name == "food.create_order":
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/capabilities/food.create_order",
                    json=arguments,
                ) as resp:
                    return await resp.json()
        elif capability_name == "food.get_order":
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/capabilities/food.get_order?order_id={arguments['order_id']}"
                ) as resp:
                    return await resp.json()
        return await original_execute(capability_name, arguments, context)

    adapter.execute = custom_execute

    # Test discovery
    print("\n1. AICP DISCOVERY")
    print("-" * 40)
    response = await adapter.discover()
    for cap in response:
        print(f"  - {cap.name}: {cap.description}")
        if cap.continuation:
            print(f"    next: {cap.continuation.next_capabilities}")

    # Test list menu
    print("\n2. CALL: food.list_menu")
    print("-" * 40)
    result = await adapter.execute("food.list_menu", {})
    print("  Available items:")
    for item in result.get("items", []):
        print(f"    - {item['name']}: ${item['price']}")

    # Test create order
    print("\n3. CALL: food.create_order")
    print("-" * 40)
    order_result = await adapter.execute(
        "food.create_order",
        {
            "item_id": "burger",
            "quantity": 2,
            "delivery_address": "123 Main St",
        },
    )
    print("  Order created:")
    print(f"    Order ID: {order_result['order_id']}")
    print(f"    Item: {order_result['item']['name']}")
    print(f"    Quantity: {order_result['quantity']}")
    print(f"    Total: ${order_result['total']}")
    print(f"    Status: {order_result['status']}")

    order_id = order_result["order_id"]

    # Test get order
    print("\n4. CALL: food.get_order")
    print("-" * 40)
    get_result = await adapter.execute("food.get_order", {"order_id": order_id})
    print(f"  Order status: {get_result['status']}")

    # Test continuation hints
    print("\n5. CONTINUATION HINTS")
    print("-" * 40)
    list_cap = await adapter.get_capability("food.list_menu")
    print("  After list_menu:")
    print(f"    can_continue: {list_cap.continuation.can_continue}")
    print(f"    next_hint: {list_cap.continuation.next_hint}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
