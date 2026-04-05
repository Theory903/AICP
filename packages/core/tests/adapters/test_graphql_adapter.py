"""Tests for the GraphQL protocol adapter baseline."""

from __future__ import annotations

from typing import Any

import pytest

from aicp.adapters.protocol.graphql import GraphQLDiscoverySource, GraphQLExecutor, GraphQLTransport
from aicp.interfaces import ExecutionStatus


def _graphql_type(kind: str, name: str | None = None, of_type: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"kind": kind, "name": name, "ofType": of_type}


def _introspection_payload() -> dict[str, Any]:
    user_type = _graphql_type("OBJECT", "User")
    return {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": {"name": "Mutation"},
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "listUsers",
                            "description": "List users",
                            "args": [
                                {
                                    "name": "limit",
                                    "description": "Maximum number of users",
                                    "type": _graphql_type("SCALAR", "Int"),
                                    "defaultValue": None,
                                }
                            ],
                            "type": _graphql_type("LIST", of_type=user_type),
                            "isDeprecated": False,
                            "deprecationReason": None,
                        }
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Mutation",
                    "fields": [
                        {
                            "name": "createUser",
                            "description": "Create a user",
                            "args": [
                                {
                                    "name": "email",
                                    "description": "User email",
                                    "type": _graphql_type(
                                        "NON_NULL",
                                        of_type=_graphql_type("SCALAR", "String"),
                                    ),
                                    "defaultValue": None,
                                }
                            ],
                            "type": user_type,
                            "isDeprecated": False,
                            "deprecationReason": None,
                        }
                    ],
                },
            ],
        }
    }


class StubGraphQLTransport:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.url = "https://example.com"
        self.endpoint = "/graphql"
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    @property
    def endpoint_url(self) -> str:
        return f"{self.url.rstrip('/')}/{self.endpoint.lstrip('/')}"

    async def send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_graphql_discovery_source_maps_introspection_to_capabilities() -> None:
    transport = StubGraphQLTransport(
        responses=[
            {
                "status": "success",
                "data": _introspection_payload(),
                "format_hint": "json",
            }
        ]
    )

    source = GraphQLDiscoverySource(name="users-graphql", transport=transport)
    capabilities = {cap.name: cap for cap in await source.discover()}

    assert set(capabilities) == {"users.list", "user.create"}
    assert capabilities["users.list"].provider is not None
    assert capabilities["users.list"].provider.name == "users-graphql"
    assert capabilities["users.list"].provider.type == "graphql"
    assert capabilities["users.list"].kind.value == "query"
    assert capabilities["users.list"].input_schema.required == []
    assert capabilities["users.list"].input_schema.properties["limit"]["type"] == "integer"
    assert capabilities["user.create"].kind.value == "action"
    assert capabilities["user.create"].input_schema.required == ["email"]
    assert capabilities["user.create"].output_schema.type == "object"


@pytest.mark.asyncio
async def test_graphql_executor_executes_discovered_capability_with_normalized_success() -> None:
    transport = StubGraphQLTransport(
        responses=[
            {
                "status": "success",
                "data": _introspection_payload(),
                "format_hint": "json",
            },
            {
                "status": "success",
                "data": {"listUsers": [{"__typename": "User"}]},
                "format_hint": "json",
            },
        ]
    )

    source = GraphQLDiscoverySource(name="users-graphql", transport=transport)
    executor = GraphQLExecutor(source=source)

    result = await executor.execute("users.list", {"limit": 2})

    assert result.status == ExecutionStatus.SUCCESS
    assert result.data == {"listUsers": [{"__typename": "User"}]}
    assert result.format_hint == "json"
    assert result.next is not None
    assert result.next["action"] == "complete"
    assert transport.requests[-1]["variables"] == {"limit": 2}
    assert "query listUsers" in transport.requests[-1]["query"]


@pytest.mark.asyncio
async def test_graphql_executor_maps_transport_failures_to_execution_status() -> None:
    transport = StubGraphQLTransport(
        responses=[
            {
                "status": "success",
                "data": _introspection_payload(),
                "format_hint": "json",
            },
            {
                "status": "rate_limited",
                "error": "Too many requests",
                "error_code": "rate_limited",
                "next": {"action": "wait", "hint": "Retry later."},
            },
        ]
    )

    source = GraphQLDiscoverySource(name="users-graphql", transport=transport)
    executor = GraphQLExecutor(source=source)

    result = await executor.execute("users.list", {})

    assert result.status == ExecutionStatus.RATE_LIMITED
    assert result.error == "Too many requests"
    assert result.error_code == "rate_limited"
    assert result.next == {"action": "wait", "hint": "Retry later."}
