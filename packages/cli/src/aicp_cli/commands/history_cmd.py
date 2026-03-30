"""Audit logs history command."""

import click
from aicp_cli.context import get_runtime_context


@click.command("logs")
@click.option("--tail", "-n", default=20, help="Number of entries")
@click.option("--capability", "-c", "cap_filter", help="Filter by capability")
@click.option("--workflow", "-w", "wf_filter", help="Filter by workflow ID")
@click.pass_context
def logs_cmd(ctx, tail, cap_filter, wf_filter):
    """Show audit log entries from the runtime journal.
    
    Examples:
        aicp logs
        aicp logs -n 50
        aicp logs -c notes.create
    """
    import asyncio
    return asyncio.run(_run_logs(tail, cap_filter, wf_filter))


async def _run_logs(tail, cap_filter, wf_filter):
    runtime = get_runtime_context()
    
    entries = await runtime.audit.list_entries(
        capability_name=cap_filter,
        workflow_id=wf_filter,
    )

    if not entries:
        click.echo("No audit entries found in the current persistence backend.")
        return

    # Sort by timestamp (newest first) and tail
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    display_entries = entries[:tail]

    for entry in display_entries:
        ts = entry.get("timestamp", "?")
        name = entry.get("capability_name") or entry.get("event_type", "?")
        actor = entry.get("actor", "system")
        status = entry.get("status", "info")
        
        # Color coding status
        status_color = "green" if status == "success" else "red" if status == "failure" else "blue"
        
        click.echo(f"[{ts}] ", nl=False)
        click.secho(f"{name:<25}", fg="cyan", nl=False)
        click.echo(f"  {actor:<10}  ", nl=False)
        click.secho(status.upper(), fg=status_color)
        
        if entry.get("error"):
            click.secho(f"      Error: {entry['error']}", fg="dim red")
        elif entry.get("reason"):
             click.secho(f"      Reason: {entry['reason']}", fg="dim white")
