"""AICP CLI — click-based command-line interface.

The governed action runtime for AI agents. Turn APIs into
discoverable, policy-enforced, stateful capabilities.
"""

import click

# ── Import Command Modules ──────────────────────────────────────
from aicp_cli.commands.init_cmd import init
from aicp_cli.commands.scan_cmd import scan
from aicp_cli.commands.dev_cmd import dev
from aicp_cli.commands.doctor_cmd import doctor
from aicp_cli.commands.bootstrap_cmd import bootstrap
from aicp_cli.commands.policy_shortcuts import safe, ask, deny, approve, protect, limit

# New modular commands
from aicp_cli.commands.list_cmd import ls_cmd
from aicp_cli.commands.preview_cmd import preview_cmd
from aicp_cli.commands.execute_cmd import run_cmd
from aicp_cli.commands.history_cmd import logs_cmd
from aicp_cli.commands.approval_cmd import appr_group
from aicp_cli.commands.serve_cmd import serve_cmd
from aicp_cli.commands.import_cmd import import_group


@click.group()
@click.version_option(version="0.1.0", prog_name="aicp")
def cli():
    """AICP — AI Capability Protocol CLI.

    The governed action runtime for AI agents. Turn APIs into
    discoverable, policy-enforced, stateful capabilities.

    Getting started:
        aicp bootstrap fastapi app:app
        aicp dev           Start the local runtime

    Full docs: https://aicp.dev
    """
    pass


# ── Core workflow commands ──────────────────────────────────────
cli.add_command(bootstrap)
cli.add_command(init)
cli.add_command(scan)
cli.add_command(dev)
cli.add_command(doctor)

# ── Capability & Runtime commands ───────────────────────────────
cli.add_command(ls_cmd)
cli.add_command(preview_cmd)
cli.add_command(run_cmd)
cli.add_command(logs_cmd)
cli.add_command(appr_group)
cli.add_command(serve_cmd)
cli.add_command(import_group)

# ── Policy shortcuts ────────────────────────────────────────────
cli.add_command(safe)
cli.add_command(ask)
cli.add_command(deny)
cli.add_command(approve)
cli.add_command(protect)
cli.add_command(limit)


# ── Backward compat aliases ─────────────────────────────────────

@cli.command("approvals", hidden=True)
@click.pass_context
def approvals_alias(ctx):
    """(Deprecated) Forward to 'aicp appr ls'."""
    click.secho("Notice: 'aicp approvals' is deprecated. Forwarding to 'aicp appr ls'...", fg="yellow")
    # Using ctx.invoke to properly forward to the other command
    from aicp_cli.commands.approval_cmd import appr_ls
    ctx.invoke(appr_ls)


if __name__ == "__main__":
    cli()
