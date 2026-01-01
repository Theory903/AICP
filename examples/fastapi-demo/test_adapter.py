"""Test FastAPI adapter with simple app."""

from fastapi import FastAPI
from aicp.adapters.framework.fastapi import mount_aicp

app = FastAPI(title="Test AICP")


@app.get("/items")
def list_items():
    """List all items."""
    return [{"id": 1, "name": "Item 1"}]


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Get an item by ID."""
    return {"id": item_id, "name": f"Item {item_id}"}


@app.post("/items")
def create_item(name: str, price: float):
    """Create a new item."""
    return {"id": 99, "name": name, "price": price}


# Mount AICP with configuration
config = mount_aicp(
    app,
    provider_name="test_app",
    discovery_path="/.well-known/aicp",
)


# Test the adapter
if __name__ == "__main__":
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Test discovery
    response = client.get("/.well-known/aicp")
    print("Discovery status:", response.status_code)

    data = response.json()
    print(f"Version: {data.get('version')}")
    print(f"Provider: {data.get('metadata', {}).get('provider_name')}")
    print(f"Capabilities: {data.get('metadata', {}).get('capability_count')}")

    print("\nCapabilities:")
    for cap in data.get("capabilities", []):
        print(f"  - {cap.get('name')}: {cap.get('kind')}")
