"""Tests for CLI Postman mapping command."""

import argparse
import json

import pytest

from aicp_cli.commands.map_postman import cmd_map_postman


@pytest.mark.asyncio
async def test_cmd_map_postman_outputs_capabilities_with_nested_provider(
    tmp_path, capsys
) -> None:
    collection_file = tmp_path / "payments.postman_collection.json"
    collection_file.write_text(
        json.dumps(
            {
                "info": {"name": "Payments Collection"},
                "item": [
                    {
                        "name": "Transfer Funds",
                        "request": {
                            "method": "POST",
                            "url": {
                                "raw": "https://api.example.com/payments/:payment_id",
                                "path": ["payments", ":payment_id"],
                            },
                            "body": {"mode": "raw", "raw": '{"amount": 100}'},
                        },
                    }
                ],
            }
        )
    )
    args = argparse.Namespace(file=str(collection_file), name=None, output=None)

    exit_code = await cmd_map_postman(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["capability_count"] == 1
    assert (
        payload["capabilities"][0]["provider"]["name"] == "payments.postman_collection"
    )
    assert payload["capabilities"][0]["input_schema"]["required"] == [
        "payment_id",
        "body",
    ]


@pytest.mark.asyncio
async def test_cmd_map_postman_writes_output_file(tmp_path, capsys) -> None:
    collection_file = tmp_path / "users.postman_collection.json"
    output_file = tmp_path / "mapped.json"
    collection_file.write_text(
        json.dumps(
            {
                "info": {"name": "Users Collection"},
                "item": [
                    {
                        "name": "List Users",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "https://api.example.com/users",
                                "path": ["users"],
                            },
                        },
                    }
                ],
            }
        )
    )
    args = argparse.Namespace(
        file=str(collection_file), name="users-collection", output=str(output_file)
    )

    exit_code = await cmd_map_postman(args)
    output = capsys.readouterr().out
    payload = json.loads(output_file.read_text())

    assert exit_code == 0
    assert "Mapped 1 capabilities" in output
    assert payload["capabilities"][0]["name"] == "users.list_users"
