"""Tests for the Postman Connect importer."""

import pytest

from aicp_connect_postman import PostmanCollectionImporter


@pytest.mark.asyncio
async def test_postman_importer_maps_collection_items_to_capabilities() -> None:
    importer = PostmanCollectionImporter(
        name="payments-collection",
        collection={
            "info": {"name": "Payments Collection"},
            "item": [
                {
                    "name": "Transfer Funds",
                    "request": {
                        "method": "POST",
                        "url": {
                            "raw": "https://api.example.com/payments/{{payment_id}}",
                            "path": ["payments", ":payment_id"],
                            "variable": [{"key": "payment_id"}],
                        },
                        "body": {
                            "mode": "raw",
                            "raw": '{"amount": 100}',
                        },
                    },
                }
            ],
        },
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.name == "payments.payment_id.transfer_funds"
    assert capability.kind == "action"
    assert capability.provider is not None
    assert capability.provider.name == "payments-collection"
    assert capability.provider.type == "postman"
    assert capability.input_schema.required == ["body", "payment_id"]


@pytest.mark.asyncio
async def test_postman_importer_flattens_nested_folders() -> None:
    importer = PostmanCollectionImporter(
        name="ops-collection",
        collection={
            "info": {"name": "Ops Collection"},
            "item": [
                {
                    "name": "Users",
                    "item": [
                        {
                            "name": "List Users",
                            "request": {
                                "method": "GET",
                                "url": {"raw": "https://api.example.com/users", "path": ["users"]},
                            },
                        }
                    ],
                }
            ],
        },
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    assert capabilities[0].name == "users.list_users"
    assert capabilities[0].kind == "query"


@pytest.mark.asyncio
async def test_postman_importer_handles_missing_body_without_required_none() -> None:
    importer = PostmanCollectionImporter(
        name="users-collection",
        collection={
            "info": {"name": "Users Collection"},
            "item": [
                {
                    "name": "Get Users",
                    "request": {
                        "method": "GET",
                        "url": {"raw": "https://api.example.com/users", "path": ["users"]},
                    },
                }
            ],
        },
    )

    capabilities = await importer.discover()

    assert capabilities[0].input_schema.required == []
    dumped = capabilities[0].model_dump(exclude_none=True, mode="json")
    assert dumped["input_schema"]["required"] == []


@pytest.mark.asyncio
async def test_postman_importer_preserves_auth_and_header_tags() -> None:
    importer = PostmanCollectionImporter(
        name="secure-collection",
        collection={
            "info": {"name": "Secure Collection"},
            "item": [
                {
                    "name": "Create Payment",
                    "request": {
                        "method": "POST",
                        "url": {
                            "raw": "https://api.example.com/payments",
                            "path": ["payments"],
                        },
                        "header": [
                            {"key": "Content-Type", "value": "application/json"},
                            {"key": "X-Trace-Id", "value": "abc"},
                        ],
                        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "secret"}]},
                    },
                }
            ],
        },
    )

    capability = (await importer.discover())[0]

    assert capability.provider is not None
    assert "auth:bearer" in capability.tags
    assert "header:content-type" in capability.tags
    assert "header:x-trace-id" in capability.tags


@pytest.mark.asyncio
async def test_postman_importer_makes_duplicate_capability_names_unique() -> None:
    importer = PostmanCollectionImporter(
        name="realworld-collection",
        collection={
            "info": {"name": "RealWorld Collection"},
            "item": [
                {
                    "name": "Articles",
                    "item": [
                        {
                            "name": "All Articles",
                            "request": {
                                "method": "GET",
                                "url": {
                                    "raw": "https://api.example.com/articles",
                                    "path": ["articles"],
                                },
                            },
                        },
                        {
                            "name": "All Articles",
                            "request": {
                                "method": "GET",
                                "url": {
                                    "raw": "https://api.example.com/articles",
                                    "path": ["articles"],
                                },
                            },
                        },
                    ],
                }
            ],
        },
    )

    capabilities = await importer.discover()

    assert [cap.name for cap in capabilities] == [
        "articles.all_articles",
        "articles.all_articles_2",
    ]
