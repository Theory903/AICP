"""Tests for the Connect OpenAPI mapper package."""

import pytest

from aicp_connect_openapi import OpenAPIDiscoverySource


@pytest.mark.asyncio
async def test_openapi_discovery_source_maps_provider_and_required_fields() -> None:
    source = OpenAPIDiscoverySource(
        name="payments-api",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Payments API", "version": "1.0.0"},
            "paths": {
                "/payments/{payment_id}": {
                    "post": {
                        "operationId": "payments.transfer",
                        "summary": "Transfer funds",
                        "parameters": [
                            {
                                "name": "payment_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"amount": {"type": "number"}},
                                        "required": ["amount"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "transaction_id": {"type": "string"}
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
        },
    )

    capabilities = await source.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.provider is not None
    assert capability.provider.name == "payments-api"
    assert capability.provider.type == "openapi"
    assert capability.input_schema.required == ["payment_id", "body"]
    assert capability.output_schema.properties["transaction_id"]["type"] == "string"


@pytest.mark.asyncio
async def test_openapi_discovery_source_handles_optional_inputs_without_none_required() -> None:
    source = OpenAPIDiscoverySource(
        name="users-api",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Users API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "users.list",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        },
    )

    capabilities = await source.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.input_schema.required == []
    dumped = capability.model_dump(exclude_none=True, mode="json")
    assert dumped["input_schema"]["required"] == []


@pytest.mark.asyncio
async def test_core_openapi_import_is_backed_by_connect_package() -> None:
    from aicp.adapters.protocol.openapi import OpenAPIDiscoverySource as CoreOpenAPISource

    source = CoreOpenAPISource(
        name="orders-api",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Orders API", "version": "1.0.0"},
            "paths": {"/orders": {"get": {"operationId": "orders.list", "responses": {"200": {}}}}},
        },
    )

    capabilities = await source.discover()

    assert len(capabilities) == 1
    assert capabilities[0].name == "orders.list"


@pytest.mark.asyncio
async def test_openapi_discovery_source_preserves_security_and_header_tags() -> None:
    source = OpenAPIDiscoverySource(
        name="secure-api",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Secure API", "version": "1.0.0"},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {"type": "http", "scheme": "bearer"},
                    "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                }
            },
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "users.list",
                        "parameters": [{"name": "X-Trace-Id", "in": "header", "schema": {"type": "string"}}],
                        "security": [{"bearerAuth": []}, {"apiKeyAuth": []}],
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        },
    )

    capability = (await source.discover())[0]

    assert "auth:bearer" in capability.tags
    assert "auth:api_key" in capability.tags
    assert "header:x-trace-id" in capability.tags
