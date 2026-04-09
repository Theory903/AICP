"""Tests for modular registry-oriented CLI commands."""

import argparse
import json

import pytest

from aicp import AicpExecutor, AicpRegistry, Capability, CapabilityKind
from aicp.implementations import InMemoryCapabilityRepository
from aicp_cli.commands.call import cmd_call
from aicp_cli.commands.list import cmd_list
from aicp_cli.commands.register import cmd_register


@pytest.mark.asyncio
async def test_cmd_register_adds_capability_to_registry(capsys) -> None:
    registry = AicpRegistry()
    args = argparse.Namespace(name="users.list", description="List users", kind="query")

    exit_code = await cmd_register(registry, args)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Registered: users.list" in output
    assert registry.get_capability("users.list") is not None


@pytest.mark.asyncio
async def test_cmd_list_prints_registered_capabilities(capsys) -> None:
    registry = AicpRegistry()
    registry.register_capability(
        Capability(
            name="users.list", description="List users", kind=CapabilityKind.QUERY
        )
    )

    exit_code = await cmd_list(registry, argparse.Namespace())

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "users.list" in output


@pytest.mark.asyncio
async def test_cmd_call_executes_capability(capsys) -> None:
    repo = InMemoryCapabilityRepository()
    repo.add_capability(
        Capability(
            name="payments.transfer", description="Transfer", kind=CapabilityKind.ACTION
        )
    )
    executor = AicpExecutor(repo)
    args = argparse.Namespace(name="payments.transfer", args='{"amount": 25}')

    exit_code = await cmd_call(AicpRegistry(), executor, args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["data"]["args"]["amount"] == 25
