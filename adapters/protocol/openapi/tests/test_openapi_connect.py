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


@pytest.mark.asyncio
async def test_openapi_discovery_source_generates_human_friendly_names_and_metadata() -> None:
    source = OpenAPIDiscoverySource(
        name="small-sms-openapi",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Small SMS", "version": "1.0.0"},
            "paths": {
                "/api/v1/school-years": {
                    "get": {
                        "summary": "Get School Years",
                        "responses": {"200": {"description": "Successful Response"}},
                        "tags": ["School Years"],
                    }
                },
                "/api/v1/school-years/{school_year_id}": {
                    "get": {
                        "summary": "Get School Year",
                        "responses": {"200": {"description": "Successful Response"}},
                        "tags": ["School Years"],
                    }
                },
                "/api/v1/school-years/{school_year_id}/activate": {
                    "put": {
                        "summary": "Activate School Year",
                        "description": "Set current school year",
                        "tags": ["School Years"],
                        "parameters": [
                            {
                                "name": "school_year_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Successful Response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "integer"}},
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/v1/grades/{grade_id}": {
                    "get": {
                        "summary": "Get Grade",
                        "responses": {"200": {"description": "Successful Response"}},
                        "tags": ["Grades"],
                    }
                },
                "/api/v1/subjects/{subject_id}": {
                    "get": {
                        "summary": "Get Subject",
                        "responses": {"200": {"description": "Successful Response"}},
                        "tags": ["Subjects"],
                    }
                },
                "/api/v1/grades/subjects": {
                    "post": {
                        "summary": "Assign Subject To Grade",
                        "description": "Assign subject to grade",
                        "tags": ["Grades"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "grade_id": {"type": "integer"},
                                            "subject_id": {"type": "integer"},
                                        },
                                        "required": ["grade_id", "subject_id"],
                                    }
                                }
                            },
                        },
                        "responses": {"200": {"description": "Successful Response"}},
                    }
                },
            },
        },
        spec_url="/tmp/small-sms-openapi.json",
    )

    capabilities = {cap.name: cap for cap in await source.discover()}

    activate = capabilities["school_years.activate"]
    assert activate.provider is not None
    assert activate.provider.url is None
    assert activate.description == "Activate School Year. Set current school year."
    assert "school-years" in activate.tags
    assert "method:put" in activate.tags
    assert "risk:medium" in activate.tags
    assert "governance:approval_candidate" in activate.tags
    assert activate.continuation is not None
    assert activate.continuation.next_capabilities == ["school_years.get", "school_years.list"]

    assign_subject = capabilities["grades.assign_subject"]
    assert assign_subject.description == "Assign subject to grade"
    assert "grades" in assign_subject.tags
    assert "risk:medium" in assign_subject.tags
    assert assign_subject.continuation is not None
    assert assign_subject.continuation.next_capabilities == ["grades.get", "subjects.get"]

    assert "school_years.list" in capabilities
    assert "school_years.get" in capabilities
    assert "subjects.get" in capabilities


@pytest.mark.asyncio
async def test_openapi_discovery_source_warns_and_skips_unresolvable_refs() -> None:
    source = OpenAPIDiscoverySource(
        name="broken-api",
        spec={
            "openapi": "3.0.0",
            "info": {"title": "Broken API", "version": "1.0.0"},
            "paths": {
                "/ok": {
                    "get": {
                        "operationId": "ok.list",
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/broken": {
                    "get": {
                        "operationId": "broken.list",
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Missing"}
                                    }
                                }
                            }
                        },
                    }
                },
            },
        },
    )

    capabilities = await source.discover()

    assert [cap.name for cap in capabilities] == ["ok.list"]
    assert any("Skipping path /broken" in warning for warning in source.warnings)
