"""Tests for CLI cURL mapping command."""

import argparse
import json

import pytest

from aicp_cli.commands.map_curl import cmd_map_curl


@pytest.mark.asyncio
async def test_cmd_map_curl_outputs_capability_with_nested_provider(capsys) -> None:
    args = argparse.Namespace(
        command_text="curl -X POST https://api.example.com/payments/123/transfer -d '{\"amount\":100}'",
        name="payments-curl",
        output=None,
    )

    exit_code = await cmd_map_curl(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["capability_count"] == 1
    assert payload["capabilities"][0]["provider"]["name"] == "payments-curl"
    assert payload["capabilities"][0]["name"] == "payments.transfer"


@pytest.mark.asyncio
async def test_cmd_map_curl_writes_output_file(tmp_path, capsys) -> None:
    output_file = tmp_path / "mapped.json"
    args = argparse.Namespace(
        command_text="curl 'https://api.example.com/users?limit=10'",
        name="users-curl",
        output=str(output_file),
    )

    exit_code = await cmd_map_curl(args)
    output = capsys.readouterr().out
    payload = json.loads(output_file.read_text())

    assert exit_code == 0
    assert "Mapped 1 capabilities" in output
    assert payload["capabilities"][0]["name"] == "users.list"
