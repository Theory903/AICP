"""Tests for CLI HAR mapping command."""

import argparse
import json

import pytest

from aicp_cli.commands.map_har import cmd_map_har


@pytest.mark.asyncio
async def test_cmd_map_har_outputs_capabilities_with_nested_provider(tmp_path, capsys) -> None:
    har_file = tmp_path / "checkout.har"
    har_file.write_text(
        json.dumps(
            {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "method": "POST",
                                "url": "https://api.example.com/orders/123/checkout",
                                "queryString": [],
                                "postData": {"mimeType": "application/json", "text": '{"coupon":"SAVE10"}'},
                            }
                        }
                    ]
                }
            }
        )
    )
    args = argparse.Namespace(file=str(har_file), name=None, output=None)

    exit_code = await cmd_map_har(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["capability_count"] == 1
    assert payload["capabilities"][0]["provider"]["name"] == "checkout"
    assert payload["capabilities"][0]["name"] == "orders.checkout"


@pytest.mark.asyncio
async def test_cmd_map_har_writes_output_file(tmp_path, capsys) -> None:
    har_file = tmp_path / "users.har"
    output_file = tmp_path / "mapped.json"
    har_file.write_text(
        json.dumps(
            {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "method": "GET",
                                "url": "https://api.example.com/users?limit=10",
                                "queryString": [{"name": "limit", "value": "10"}],
                            }
                        }
                    ]
                }
            }
        )
    )
    args = argparse.Namespace(file=str(har_file), name="users-har", output=str(output_file))

    exit_code = await cmd_map_har(args)
    output = capsys.readouterr().out
    payload = json.loads(output_file.read_text())

    assert exit_code == 0
    assert "Mapped 1 capabilities" in output
    assert payload["capabilities"][0]["name"] == "users.list"
