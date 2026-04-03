"""Tests for CLI OpenAPI mapping command."""

import argparse
import json

import pytest

from aicp_cli.commands.map_openapi import cmd_map_openapi


@pytest.mark.asyncio
async def test_cmd_map_openapi_outputs_capabilities_with_nested_provider(
    tmp_path, capsys
) -> None:
    spec_file = tmp_path / "payments.json"
    spec_file.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Payments API", "version": "1.0.0"},
                "paths": {
                    "/payments/{payment_id}": {
                        "post": {
                            "operationId": "payments.transfer",
                            "parameters": [
                                {
                                    "name": "payment_id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"},
                                }
                            ],
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                },
            }
        )
    )
    args = argparse.Namespace(
        file=str(spec_file), name=None, base_url=None, output=None
    )

    exit_code = await cmd_map_openapi(args)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["capability_count"] == 1
    assert payload["capabilities"][0]["provider"]["name"] == "payments"
    assert payload["capabilities"][0]["input_schema"]["required"] == ["payment_id"]


@pytest.mark.asyncio
async def test_cmd_map_openapi_writes_output_file_without_workaround_message(
    tmp_path, capsys
) -> None:
    spec_file = tmp_path / "users.json"
    output_file = tmp_path / "mapped.json"
    spec_file.write_text(
        json.dumps(
            {
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
            }
        )
    )
    args = argparse.Namespace(
        file=str(spec_file),
        name="users-api",
        base_url="https://api.example.com",
        output=str(output_file),
    )

    exit_code = await cmd_map_openapi(args)
    captured = capsys.readouterr()
    payload = json.loads(output_file.read_text())

    assert exit_code == 0
    assert "workaround" not in captured.out.lower()
    assert payload["capabilities"][0]["provider"]["url"] == "https://api.example.com"
    assert payload["capabilities"][0]["input_schema"]["required"] == []
