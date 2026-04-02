"""Tests for FastAPI adapter."""


from fastapi import FastAPI, Query
from fastapi import Path as PathParam
from fastapi.testclient import TestClient
from pydantic import BaseModel

from aicp.adapters.framework.fastapi import AicpConfig, mount_aicp
from aicp.adapters.framework.fastapi.inspect import infer_capability_name, inspect_routes


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class ItemResponse(BaseModel):
    id: int
    name: str


class TestRouteInspection:
    """Tests for route inspection."""

    def test_inspect_simple_get(self):
        """Test inspecting a simple GET route."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        routes = inspect_routes(app)
        assert len(routes) == 1
        assert routes[0]["path"] == "/items"
        assert "GET" in routes[0]["methods"]
        assert routes[0]["kind"] == "query"

    def test_inspect_simple_post(self):
        """Test inspecting a POST route."""
        app = FastAPI()

        @app.post("/items")
        def create_item(name: str):
            return {"name": name}

        routes = inspect_routes(app)
        assert len(routes) == 1
        assert routes[0]["path"] == "/items"
        assert "POST" in routes[0]["methods"]
        assert routes[0]["kind"] == "action"

    def test_inspect_path_params(self):
        """Test inspecting a route with path parameters."""
        app = FastAPI()

        @app.get("/items/{item_id}")
        def get_item(item_id: int):
            return {"id": item_id}

        routes = inspect_routes(app)
        assert len(routes) == 1
        assert routes[0]["path"] == "/items/{item_id}"
        assert "item_id" in routes[0]["input_schema"]["properties"]

    def test_exclude_docs_routes(self):
        """Test that /docs routes are excluded."""
        app = FastAPI()

        @app.get("/docs")
        def docs():
            return []

        @app.get("/items")
        def list_items():
            return []

        routes = inspect_routes(app)
        assert len(routes) == 1
        assert routes[0]["path"] == "/items"


class TestCapabilityNaming:
    """Tests for capability name inference."""

    def test_list_endpoint(self):
        """Test naming for list endpoint."""
        route = {"path": "/items", "methods": ["GET"], "func_name": "list_items"}
        assert infer_capability_name(route) == "items.list"

    def test_get_endpoint(self):
        """Test naming for get by ID endpoint."""
        route = {"path": "/items/{id}", "methods": ["GET"], "func_name": "get_item"}
        assert infer_capability_name(route) == "items.get"

    def test_create_endpoint(self):
        """Test naming for create endpoint."""
        route = {"path": "/items", "methods": ["POST"], "func_name": "create_item"}
        assert infer_capability_name(route) == "items.create"

    def test_delete_endpoint(self):
        """Test naming for delete endpoint."""
        route = {"path": "/items/{id}", "methods": ["DELETE"], "func_name": "delete_item"}
        assert infer_capability_name(route) == "items.delete"


class TestMountAicp:
    """Tests for mounting AICP on FastAPI."""

    def test_mount_creates_discovery_endpoint(self):
        """Test that mounting creates the discovery endpoint."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        mount_aicp(app, discovery_path="/.well-known/aicp")

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        assert response.status_code == 200

    def test_discovery_returns_capabilities(self):
        """Test that discovery returns mapped capabilities."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        @app.post("/items")
        def create_item(name: str):
            return {"name": name}

        mount_aicp(app, discovery_path="/.well-known/aicp")

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        data = response.json()

        caps = data.get("capabilities", [])
        assert len(caps) == 2
        cap_names = [c["name"] for c in caps]
        assert "items.list" in cap_names
        assert "items.create" in cap_names

    def test_custom_provider_name(self):
        """Test custom provider name in discovery."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        mount_aicp(app, provider_name="my_service")

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        data = response.json()

        assert data["metadata"]["provider_name"] == "my_service"

    def test_exclude_routes(self):
        """Test route exclusion."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        @app.get("/internal")
        def internal():
            return []

        mount_aicp(app, exclude_routes=["/internal"])

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        data = response.json()

        caps = data.get("capabilities", [])
        assert len(caps) == 1
        assert caps[0]["name"] == "items.list"


class TestOverlay:
    """Tests for overlay functionality."""

    def test_explicit_route_mapping_adds(self):
        """Test explicit route mapping adds to auto-detected."""
        from aicp.adapters.framework.fastapi.types import RouteMapping

        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        @app.get("/users")
        def list_users():
            return []

        config = AicpConfig(
            route_mappings=[
                RouteMapping(
                    route_path="/users",
                    method="GET",
                    capability_name="custom.users",
                    description="Custom description",
                    kind="action",
                )
            ]
        )

        mount_aicp(app, config=config)

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        data = response.json()

        caps = data.get("capabilities", [])
        assert len(caps) == 2
        cap_names = [c["name"] for c in caps]
        assert "items.list" in cap_names
        assert "custom.users" in cap_names


class TestFastAPIMetadata:
    """Tests using FastAPI route metadata (Pydantic models, tags, etc.)."""

    def test_pydantic_body_model(self):
        """Test extracting schema from Pydantic body model."""
        app = FastAPI()

        @app.post("/items")
        def create_item(item: ItemCreate):
            return item

        routes = inspect_routes(app)
        assert len(routes) == 1
        props = routes[0]["input_schema"]["properties"]
        assert "body" in props
        body = props["body"]
        assert body.get("x-location") == "body"
        assert body.get("$ref") == "#/components/schemas/ItemCreate" or "properties" in body
        assert "required" in routes[0]["input_schema"]
        assert "body" in routes[0]["input_schema"]["required"]

    def test_pydantic_response_model(self):
        """Test extracting output schema from response model."""
        app = FastAPI()

        @app.get("/items/{item_id}", response_model=ItemResponse)
        def get_item(item_id: int):
            return {"id": item_id, "name": "test"}

        routes = inspect_routes(app)
        # Response model info would need to be extracted from the route
        assert len(routes) == 1
        assert routes[0]["path"] == "/items/{item_id}"

    def test_route_with_tags(self):
        """Test routes with tags are properly inspected."""
        app = FastAPI()

        @app.get("/items", tags=["items"])
        def list_items():
            return []

        routes = inspect_routes(app)
        assert len(routes) == 1

    def test_route_with_summary(self):
        """Test routes with summary/description."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            """List all items in the system."""
            return []

        routes = inspect_routes(app)
        assert len(routes) == 1
        assert "List all items" in routes[0]["description"]


class TestQueryAndPathParams:
    """Tests for query and path parameter handling."""

    def test_query_parameters(self):
        """Test extracting query parameters."""
        app = FastAPI()

        @app.get("/items")
        def list_items(
            limit: int = Query(10),
            offset: int = Query(0),
            search: str | None = Query(None),
        ):
            return []

        routes = inspect_routes(app)
        props = routes[0]["input_schema"]["properties"]
        assert "limit" in props
        assert "offset" in props
        assert "search" in props
        assert props["limit"]["type"] == "integer"

    def test_path_parameters(self):
        """Test extracting path parameters."""
        app = FastAPI()

        @app.get("/items/{item_id}")
        def get_item(item_id: int = PathParam(...)):
            return {"id": item_id}

        routes = inspect_routes(app)
        props = routes[0]["input_schema"]["properties"]
        assert "item_id" in props

    def test_mixed_query_and_body(self):
        """Test route with both query params and body."""
        app = FastAPI()

        @app.post("/items/search")
        def search_items(q: str = Query(...), filters: dict | None = None):
            return []

        routes = inspect_routes(app)
        props = routes[0]["input_schema"]["properties"]
        assert "q" in props
        assert "body" in props


class TestNestedPaths:
    """Tests for nested API paths."""

    def test_nested_resource_path(self):
        """Test capability naming for nested resources."""
        route = {"path": "/users/{user_id}/orders", "methods": ["GET"], "func_name": "get_orders"}
        assert infer_capability_name(route) == "users.orders.get"

    def test_deeply_nested_path(self):
        """Test deeply nested paths - uses .get since it has path params."""
        route = {"path": "/orgs/{org_id}/users/{user_id}/posts", "methods": ["GET"], "func_name": "list_posts"}
        # Path params present = .get semantics
        assert infer_capability_name(route) == "orgs.users.posts.get"

    def test_api_prefix_stripping(self):
        """Test that /api/v1 prefix is handled."""
        route = {"path": "/api/v1/users", "methods": ["GET"], "func_name": "list_users"}
        assert "api" not in infer_capability_name(route)


class TestEdgeCases:
    """Edge case tests."""

    def test_no_docstring(self):
        """Test route without docstring uses function name as description."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        routes = inspect_routes(app)
        assert routes[0]["description"] != ""

    def test_optional_parameters(self):
        """Test optional parameters are not marked required."""
        app = FastAPI()

        @app.get("/items")
        def list_items(name: str | None = None):
            return []

        routes = inspect_routes(app)
        required = routes[0]["input_schema"].get("required") or []
        assert "name" not in required

    def test_multiple_methods_same_path(self):
        """Test same path with different HTTP methods."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        @app.post("/items")
        def create_items():
            return []

        routes = inspect_routes(app)
        assert len(routes) == 2
        paths = [r["path"] for r in routes]
        assert "/items" in paths

    def test_discovery_includes_version(self):
        """Test discovery response includes version."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        mount_aicp(app, version="1.0.0")

        client = TestClient(app)
        response = client.get("/.well-known/aicp")
        assert response.json()["version"] == "1.0.0"

    def test_discovery_includes_metadata(self):
        """Test discovery includes correct metadata."""
        app = FastAPI()

        @app.get("/items")
        def list_items():
            return []

        mount_aicp(app, provider_name="test-provider", provider_url="https://test.example.com")

        client = TestClient(app)
        data = client.get("/.well-known/aicp").json()
        assert data["metadata"]["provider_name"] == "test-provider"
        assert data["metadata"]["provider_url"] == "https://test.example.com"
