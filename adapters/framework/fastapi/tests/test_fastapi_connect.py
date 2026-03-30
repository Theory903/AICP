"""Tests for the Connect FastAPI adapter package."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aicp_connect_fastapi import AicpConfig, mount_aicp
from aicp_connect_fastapi.inspect import inspect_routes


def test_connect_fastapi_inspects_routes() -> None:
    app = FastAPI()

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"id": item_id}

    routes = inspect_routes(app)

    assert len(routes) == 1
    assert routes[0]["path"] == "/items/{item_id}"
    assert "item_id" in routes[0]["input_schema"]["properties"]


def test_connect_fastapi_mounts_discovery_with_provider_metadata() -> None:
    app = FastAPI()

    @app.get("/items")
    def list_items():
        return []

    mount_aicp(app, config=AicpConfig(provider_name="connect-fastapi"))
    client = TestClient(app)
    response = client.get("/.well-known/aicp")
    data = response.json()

    assert response.status_code == 200
    assert data["metadata"]["provider_name"] == "connect-fastapi"
    assert data["capabilities"][0]["provider"]["type"] == "fastapi"


def test_core_fastapi_import_is_backed_by_connect_package() -> None:
    from aicp.adapters.framework.fastapi import mount_aicp as core_mount_aicp
    from aicp.adapters.framework.fastapi.inspect import infer_capability_name as core_infer

    app = FastAPI()

    @app.get("/users")
    def list_users():
        return []

    core_mount_aicp(app)
    client = TestClient(app)
    response = client.get("/.well-known/aicp")

    assert response.status_code == 200
    assert core_infer({"path": "/users", "methods": ["GET"], "func_name": "list_users"}) == "users.list"
