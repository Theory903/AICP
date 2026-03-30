"""Tests for the HAR Connect importer."""

import pytest

from aicp_connect_har import HarImporter


@pytest.mark.asyncio
async def test_har_importer_maps_requests_to_capabilities() -> None:
    importer = HarImporter(
        name="checkout-session",
        har={
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "POST",
                            "url": "https://api.example.com/orders/123/checkout",
                            "queryString": [],
                            "postData": {
                                "mimeType": "application/json",
                                "text": '{"coupon":"SAVE10"}',
                            },
                        }
                    }
                ]
            }
        },
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.name == "orders.checkout"
    assert capability.kind == "action"
    assert capability.provider is not None
    assert capability.provider.name == "checkout-session"
    assert capability.provider.type == "har"
    assert capability.input_schema.required == ["body"]


@pytest.mark.asyncio
async def test_har_importer_merges_duplicate_requests() -> None:
    importer = HarImporter(
        name="search-session",
        har={
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/users?limit=10",
                            "queryString": [{"name": "limit", "value": "10"}],
                        }
                    },
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/users?limit=20",
                            "queryString": [{"name": "limit", "value": "20"}],
                        }
                    },
                ]
            }
        },
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    assert capabilities[0].name == "users.list"
    assert capabilities[0].input_schema.required == []
    assert "limit" in capabilities[0].input_schema.properties


@pytest.mark.asyncio
async def test_har_importer_handles_empty_inputs_without_required_none() -> None:
    importer = HarImporter(
        name="health-session",
        har={
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/health",
                            "queryString": [],
                        }
                    }
                ]
            }
        },
    )

    capabilities = await importer.discover()

    dumped = capabilities[0].model_dump(exclude_none=True, mode="json")
    assert dumped["input_schema"]["required"] == []


@pytest.mark.asyncio
async def test_har_importer_preserves_auth_and_header_tags() -> None:
    importer = HarImporter(
        name="secure-session",
        har={
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/users",
                            "queryString": [],
                            "headers": [
                                {"name": "Authorization", "value": "Bearer secret"},
                                {"name": "X-Request-Id", "value": "req-1"},
                            ],
                        }
                    }
                ]
            }
        },
    )

    capability = (await importer.discover())[0]

    assert "auth:bearer" in capability.tags
    assert "header:authorization" in capability.tags
    assert "header:x-request-id" in capability.tags
