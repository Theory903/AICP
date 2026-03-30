"""Tests for modular CLI core commands."""

import argparse
import json

import pytest

from aicp import AicpExecutor, AicpRegistry, Capability, CapabilityKind
from aicp.implementations import InMemoryCapabilityRepository
from aicp_cli.__main__ import create_parser
from aicp_cli.commands.discover import cmd_discover
from aicp_cli.commands.execute import cmd_execute


@pytest.mark.asyncio
async def test_cmd_discover_prints_registry_discovery(capsys) -> None:
    registry = AicpRegistry()
    registry.register_capability(
        Capability(name="users.list", description="List users", kind=CapabilityKind.QUERY)
    )
    args = argparse.Namespace()

    exit_code = await cmd_discover(registry, args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["capabilities"][0]["name"] == "users.list"


@pytest.mark.asyncio
async def test_cmd_execute_runs_capability_and_prints_result(capsys) -> None:
    repo = InMemoryCapabilityRepository()
    repo.add_capability(
        Capability(name="payments.transfer", description="Transfer", kind=CapabilityKind.ACTION)
    )
    executor = AicpExecutor(repo)
    args = argparse.Namespace(capability="payments.transfer", args='{"amount": 10}', context='{}')

    exit_code = await cmd_execute(AicpRegistry(), executor, args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["data"]["args"]["amount"] == 10


def test_parser_supports_execute_and_map_subcommands() -> None:
    parser = create_parser()

    execute_args = parser.parse_args(["execute", "payments.transfer", "--args", "{}"])
    map_args = parser.parse_args(["map", "openapi", "spec.json"])

    assert execute_args.command == "execute"
    assert execute_args.capability == "payments.transfer"
    assert map_args.command == "map"
    assert map_args.map_command == "openapi"
