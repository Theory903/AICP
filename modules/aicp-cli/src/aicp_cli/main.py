"""AICP CLI — click-based command-line interface.

The governed action runtime for AI agents. Turn APIs into
discoverable, policy-enforced, stateful capabilities.
"""

from __future__ import annotations

import click
from aicp import __version__

from aicp_cli.commands.approval_cmd import appr_group, appr_ls
from aicp_cli.commands.bootstrap_cmd import bootstrap
from aicp_cli.commands.dev_cmd import dev
from aicp_cli.commands.doctor_cmd import doctor
from aicp_cli.commands.execute_cmd import run_cmd
from aicp_cli.commands.history_cmd import logs_cmd
from aicp_cli.commands.import_cmd import import_group
from aicp_cli.commands.init_cmd import init
from aicp_cli.commands.list_cmd import ls_cmd
from aicp_cli.commands.map_cmd import map_group
from aicp_cli.commands.policy_shortcuts import approve, ask, deny, limit, protect, safe
from aicp_cli.commands.preview_cmd import preview_cmd
from aicp_cli.commands.scan_cmd import scan
from aicp_cli.commands.serve_cmd import serve_cmd
from aicp_cli.commands.test_cmd import (
    test_cmd as runtime_test_cmd,
    test_execute_cmd as runtime_test_execute_cmd,
    test_approvals_cmd as runtime_test_approvals_cmd,
    test_approve_cmd as runtime_test_approve_cmd,
    test_review_cmd as runtime_test_review_cmd,
    test_rank_cmd as runtime_test_rank_cmd,
    test_health_cmd as runtime_test_health_cmd,
    test_sessions_cmd as runtime_test_sessions_cmd,
    test_interactions_cmd as runtime_test_interactions_cmd,
)

CORE_COMMANDS = [
    bootstrap,
    init,
    scan,
    dev,
    doctor,
    map_group,
]

RUNTIME_COMMANDS = [
    ls_cmd,
    preview_cmd,
    run_cmd,
    logs_cmd,
    appr_group,
    serve_cmd,
    import_group,
    runtime_test_cmd,
    runtime_test_execute_cmd,
    runtime_test_approvals_cmd,
    runtime_test_approve_cmd,
    runtime_test_review_cmd,
    runtime_test_rank_cmd,
    runtime_test_health_cmd,
    runtime_test_sessions_cmd,
    runtime_test_interactions_cmd,
]

POLICY_COMMANDS = [
    safe,
    ask,
    deny,
    approve,
    protect,
    limit,
]


@click.group()
@click.version_option(version=__version__, prog_name="aicp")
def cli() -> None:
    """AICP — AI Capability Protocol CLI.

    The governed action runtime for AI agents. Turn APIs into
    discoverable, policy-enforced, stateful capabilities.

    Getting started:
        aicp bootstrap fastapi app:app
        aicp dev

    Full docs: https://aicp.dev
    """
    ...


def _register_commands() -> None:
    """Register command groups onto the root CLI."""
    for command in CORE_COMMANDS:
        cli.add_command(command)

    for command in RUNTIME_COMMANDS:
        cli.add_command(command)

    for command in POLICY_COMMANDS:
        cli.add_command(command)


_register_commands()


@cli.command("approvals", hidden=True)
@click.pass_context
def approvals_alias(ctx: click.Context) -> None:
    """Deprecated alias for 'aicp appr ls'."""
    click.secho(
        "Notice: 'aicp approvals' is deprecated. Forwarding to 'aicp appr ls'...",
        fg="yellow",
        err=True,
    )
    ctx.invoke(appr_ls, status="pending")


if __name__ == "__main__":
    cli()
