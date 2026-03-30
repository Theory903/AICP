"""Tests for the cURL Connect importer."""

import pytest

from aicp_connect_curl import CurlImporter


@pytest.mark.asyncio
async def test_curl_importer_maps_post_request_to_capability() -> None:
    importer = CurlImporter(
        name="payments-curl",
        curl_command="curl -X POST https://api.example.com/payments/123/transfer -H 'Content-Type: application/json' -d '{\"amount\":100}'",
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.name == "payments.transfer"
    assert capability.kind == "action"
    assert capability.provider is not None
    assert capability.provider.name == "payments-curl"
    assert capability.provider.type == "curl"
    assert capability.input_schema.required == ["body"]


@pytest.mark.asyncio
async def test_curl_importer_maps_get_query_params() -> None:
    importer = CurlImporter(
        name="users-curl",
        curl_command="curl 'https://api.example.com/users?limit=10&status=active'",
    )

    capabilities = await importer.discover()

    assert len(capabilities) == 1
    capability = capabilities[0]
    assert capability.name == "users.list"
    assert capability.kind == "query"
    assert "limit" in capability.input_schema.properties
    assert "status" in capability.input_schema.properties
    assert capability.input_schema.required == []


@pytest.mark.asyncio
async def test_curl_importer_handles_empty_inputs_without_required_none() -> None:
    importer = CurlImporter(
        name="health-curl",
        curl_command="curl https://api.example.com/health",
    )

    capabilities = await importer.discover()

    dumped = capabilities[0].model_dump(exclude_none=True, mode="json")
    assert dumped["input_schema"]["required"] == []


@pytest.mark.asyncio
async def test_curl_importer_preserves_auth_and_header_tags() -> None:
    importer = CurlImporter(
        name="secure-curl",
        curl_command="curl -H 'Authorization: Bearer secret' -H 'X-Trace-Id: abc' https://api.example.com/users",
    )

    capability = (await importer.discover())[0]

    assert "auth:bearer" in capability.tags
    assert "header:authorization" in capability.tags
    assert "header:x-trace-id" in capability.tags
