"""Tests for CLI governance commands."""

import argparse
import json

import pytest

from aicp_cli.__main__ import create_parser
from aicp_cli.commands.approvals import cmd_approvals_decide, cmd_approvals_list
from aicp_cli.commands.history import cmd_history_list


class FakeApprovalService:
    async def list_approvals(self):
        return [
            {"id": "apr-1", "status": "pending", "capability_name": "payments.transfer"}
        ]

    async def decide(
        self, approval_id, decision, approver, reason=None, modified_arguments=None
    ):
        return {
            "id": "dec-1",
            "request_id": approval_id,
            "decision": decision,
            "approver": approver,
            "reason": reason,
            "modified_arguments": modified_arguments,
        }


class FakeAuditService:
    async def list_entries(
        self, workflow_id=None, capability_name=None, approval_request_id=None
    ):
        return [
            {
                "id": "audit-1",
                "event_type": "approval_request_created",
                "workflow_id": workflow_id,
                "capability_name": capability_name,
                "approval_request_id": approval_request_id,
            }
        ]


@pytest.mark.asyncio
async def test_cmd_approvals_list_prints_approval_queue(capsys) -> None:
    exit_code = await cmd_approvals_list(FakeApprovalService(), argparse.Namespace())
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload[0]["id"] == "apr-1"


@pytest.mark.asyncio
async def test_cmd_approvals_decide_prints_decision(capsys) -> None:
    args = argparse.Namespace(
        approval_id="apr-1",
        decision="approved",
        approver="manager-1",
        reason="ok",
        modified_arguments=None,
    )

    exit_code = await cmd_approvals_decide(FakeApprovalService(), args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["request_id"] == "apr-1"
    assert payload["decision"] == "approved"


@pytest.mark.asyncio
async def test_cmd_history_list_prints_filtered_history(capsys) -> None:
    args = argparse.Namespace(
        workflow_id="wf-1", capability_name=None, approval_request_id=None
    )

    exit_code = await cmd_history_list(FakeAuditService(), args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload[0]["workflow_id"] == "wf-1"


def test_parser_supports_approvals_and_history_commands() -> None:
    parser = create_parser()

    approvals_args = parser.parse_args(
        [
            "approvals",
            "decide",
            "apr-1",
            "--decision",
            "approved",
            "--approver",
            "manager-1",
        ]
    )
    history_args = parser.parse_args(["history", "--workflow-id", "wf-1"])

    assert approvals_args.command == "approvals"
    assert approvals_args.approvals_command == "decide"
    assert approvals_args.approval_id == "apr-1"
    assert history_args.command == "history"
    assert history_args.workflow_id == "wf-1"
