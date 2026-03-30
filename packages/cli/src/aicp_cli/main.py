"""AICP CLI — click-based command-line interface.

Command tree:
    aicp init                       Scaffold project
    aicp scan [fastapi|openapi|..] Detect & generate capabilities
    aicp dev                        Run local full stack
    aicp serve                      Run runtime server
    aicp doctor                     Validate config
    aicp ls                         List capabilities
    aicp run <cap> --input <json>   Execute capability
    aicp logs                       Audit tail
    aicp appr ls|ok|no              Approval queue
    aicp pol ls|add|rm              Policy management
    aicp import openapi|postman|..  Import from external specs
    aicp safe|ask|deny <cap>        Policy shortcuts
"""

import click

from aicp_cli.commands.init_cmd import init
from aicp_cli.commands.scan_cmd import scan
from aicp_cli.commands.dev_cmd import dev
from aicp_cli.commands.doctor_cmd import doctor
from aicp_cli.commands.policy_shortcuts import safe, ask, deny, approve, protect, limit
from aicp_cli.commands.preview_cmd import preview
from aicp_cli.commands.bootstrap_cmd import bootstrap


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
cli.add_command(preview)

# ── Policy shortcuts ────────────────────────────────────────────

cli.add_command(safe)
cli.add_command(ask)
cli.add_command(deny)
cli.add_command(approve)
cli.add_command(protect)
cli.add_command(limit)


# ── Capability commands ─────────────────────────────────────────

@cli.command("ls")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "yaml"]), default="table")
@click.option("--kind", "-k", type=click.Choice(["query", "action", "workflow", "async_action", "batch_action"]))
@click.option("--tag", "-t", help="Filter by tag")
def ls(fmt, kind, tag):
    """List all registered capabilities."""
    import asyncio
    asyncio.run(_list_capabilities(fmt, kind, tag))


async def _list_capabilities(fmt, kind, tag):
    """List capabilities from config or runtime."""
    from pathlib import Path

    from aicp.config import load_project_config
    from aicp.risk import infer_risk

    config = load_project_config()
    caps_dir = Path(config.capabilities_dir)

    if not caps_dir.exists():
        click.echo("No capabilities directory found. Run 'aicp scan' first.")
        return

    try:
        import yaml
    except ImportError:
        click.echo("PyYAML required. Install with: pip install pyyaml")
        return

    capabilities = []
    for f in sorted(caps_dir.glob("*.yaml")):
        with open(f) as fh:
            cap = yaml.safe_load(fh)
            if cap:
                capabilities.append(cap)

    if kind:
        capabilities = [c for c in capabilities if c.get("kind") == kind]
    if tag:
        capabilities = [c for c in capabilities if tag in c.get("tags", [])]

    if not capabilities:
        click.echo("No capabilities found.")
        return

    if fmt == "json":
        import json
        click.echo(json.dumps(capabilities, indent=2))
    elif fmt == "yaml":
        import yaml
        click.echo(yaml.dump(capabilities, default_flow_style=False))
    else:
        # Table format using rich
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="AICP Capabilities", show_lines=False)
            table.add_column("Name", style="cyan bold")
            table.add_column("Kind", style="green")
            table.add_column("Risk", style="yellow")
            table.add_column("Description", style="dim")

            for cap in capabilities:
                risk = infer_risk(cap["name"], cap.get("kind")).value
                # Check for risk in tags
                for t in cap.get("tags", []):
                    if t.startswith("risk:"):
                        risk = t.split(":")[1]
                        break

                risk_style = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}.get(risk, "white")
                table.add_row(
                    cap["name"],
                    cap.get("kind", "?"),
                    f"[{risk_style}]{risk}[/{risk_style}]",
                    (cap.get("description", "")[:50] + "...") if len(cap.get("description", "")) > 50 else cap.get("description", ""),
                )

            console.print(table)
        except ImportError:
            # Fallback without rich
            click.echo(f"{'Name':<30} {'Kind':<15} {'Description'}")
            click.echo("-" * 70)
            for cap in capabilities:
                click.echo(f"{cap['name']:<30} {cap.get('kind', '?'):<15} {cap.get('description', '')[:40]}")


# ── Run command ──────────────────────────────────────────────────

@cli.command("run")
@click.argument("capability")
@click.option("--input", "-i", "input_data", help="JSON input string or @file path")
@click.option("--context", "-c", "context_data", default="{}", help="JSON context")
def run_capability(capability, input_data, context_data):
    """Execute a capability by name.

    Examples:
        aicp run notes.create -i '{"title": "Hello"}'
        aicp run notes.list
        aicp run notes.delete -i @fixture.json
    """
    import asyncio
    import json

    args = {}
    if input_data:
        if input_data.startswith("@"):
            with open(input_data[1:]) as f:
                args = json.load(f)
        else:
            args = json.loads(input_data)

    ctx = json.loads(context_data)
    asyncio.run(_run_capability(capability, args, ctx))


async def _run_capability(capability_name, args, context):
    """Execute capability via the AICP executor."""
    import json

    from aicp import AicpExecutor
    from aicp.implementations import InMemoryCapabilityRepository

    repo = InMemoryCapabilityRepository()
    executor = AicpExecutor(repo)

    try:
        result = await executor.execute(capability_name, args, context)
        click.echo(json.dumps(result, indent=2, default=str))
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")


# ── Logs command ─────────────────────────────────────────────────

@cli.command("logs")
@click.option("--tail", "-n", default=20, help="Number of entries")
@click.option("--capability", "-c", "cap_filter", help="Filter by capability")
@click.option("--workflow", "-w", "wf_filter", help="Filter by workflow ID")
def logs(tail, cap_filter, wf_filter):
    """Show audit log entries.

    Examples:
        aicp logs
        aicp logs -n 50
        aicp logs -c notes.create
    """
    import asyncio
    asyncio.run(_show_logs(tail, cap_filter, wf_filter))


async def _show_logs(tail, cap_filter, wf_filter):
    from aicp.config import load_project_config
    from aicp_runtime.persistence import InMemoryRuntimeStore
    from aicp_runtime.services import AuditService

    load_project_config()  # Validate config exists
    store = InMemoryRuntimeStore()
    audit = AuditService(store)

    entries = await audit.list_audit_entries(
        limit=tail,
        capability_name=cap_filter,
        workflow_id=wf_filter,
    )

    if not entries:
        click.echo("No audit entries found.")
        return

    for entry in entries:
        ts = getattr(entry, "timestamp", "?")
        name = getattr(entry, "capability_name", "?")
        status = getattr(entry, "status", "?")
        click.echo(f"[{ts}] {name} → {status}")


# ── Serve command (legacy compat) ──────────────────────────────

@cli.command("serve")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--app", "app_path", help="FastAPI app module (e.g., myapp:app)")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload")
@click.option("--store-backend", type=click.Choice(["memory", "file", "sqlite"]), default="memory")
@click.option("--store-path", help="Path for durable state")
def serve(host, port, app_path, reload, store_backend, store_path):
    """Start the AICP runtime server (standalone).

    For development, prefer 'aicp dev' instead.
    """
    import asyncio
    asyncio.run(_serve(host, port, app_path, reload, store_backend, store_path))


async def _serve(host, port, app_path, reload, store_backend, store_path):
    import uvicorn
    from aicp_runtime.server.app import create_app

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, reload=reload)
    server = uvicorn.Server(config)
    await server.serve()


# ── Approval commands ────────────────────────────────────────────

@cli.group("appr")
def appr():
    """Approval queue operations.

    Aliases: approvals, appr
    """
    pass


@appr.command("ls")
@click.option("--status", "-s", type=click.Choice(["pending", "approved", "rejected"]), default="pending")
def appr_ls(status):
    """List approval requests."""
    import asyncio
    asyncio.run(_appr_list(status))


async def _appr_list(status):
    from aicp_runtime.persistence import InMemoryRuntimeStore
    from aicp_runtime.services import ApprovalService

    store = InMemoryRuntimeStore()
    service = ApprovalService(store)
    requests = await service.list_approval_requests()

    if status:
        requests = [r for r in requests if getattr(r, "status", "pending") == status]

    if not requests:
        click.echo(f"No {status} approval requests.")
        return

    for req in requests:
        click.echo(f"  [{req.id}] {req.capability_name} — {req.status}")


@appr.command("ok")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", help="Approver identity")
@click.option("--reason", "-r", help="Approval reason")
def appr_ok(approval_id, approver, reason):
    """Approve a pending request."""
    import asyncio
    asyncio.run(_appr_decide(approval_id, "approved", approver, reason))


@appr.command("no")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", help="Approver identity")
@click.option("--reason", "-r", help="Rejection reason")
def appr_no(approval_id, approver, reason):
    """Reject a pending request."""
    import asyncio
    asyncio.run(_appr_decide(approval_id, "rejected", approver, reason))


async def _appr_decide(approval_id, decision, approver, reason):
    from aicp_runtime.persistence import InMemoryRuntimeStore
    from aicp_runtime.services import ApprovalService

    store = InMemoryRuntimeStore()
    service = ApprovalService(store)

    try:
        await service.decide(
            approval_id=approval_id,
            decision=decision,
            approver=approver,
            reason=reason,
        )
        color = "green" if decision == "approved" else "red"
        click.secho(f"✓ {decision.title()} [{approval_id}]", fg=color)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")


# ── Import group (replaces old 'map') ───────────────────────────

@cli.group("import")
def import_group():
    """Import capabilities from external specifications.

    Aliases: import, map (deprecated)
    """
    pass


@import_group.command("openapi")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--base-url", help="Override base URL")
@click.option("--output", "-o", help="Output directory")
def import_openapi(file, name, base_url, output):
    """Import from OpenAPI spec.

    Example: aicp import openapi ./openapi.yaml
    """
    import asyncio
    asyncio.run(_import_openapi(file, name, base_url, output))


async def _import_openapi(file, name, base_url, output):
    from aicp_connect_openapi import OpenAPIDiscoverySource

    source = OpenAPIDiscoverySource(file, name=name, base_url=base_url)
    capabilities = await source.discover()

    click.echo(f"Discovered {len(capabilities)} capabilities from OpenAPI spec:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    if output:
        from aicp.export import export_all_capabilities
        written = export_all_capabilities(capabilities, output)
        click.echo(f"\nWritten {len(written)} capability files to {output}/")


@import_group.command("postman")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--output", "-o", help="Output directory")
def import_postman(file, name, output):
    """Import from Postman collection."""
    import asyncio
    asyncio.run(_import_postman(file, name, output))


async def _import_postman(file, name, output):
    from aicp_connect_postman import PostmanDiscoverySource

    source = PostmanDiscoverySource(file, name=name)
    capabilities = await source.discover()

    click.echo(f"Discovered {len(capabilities)} capabilities from Postman collection:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    if output:
        from aicp.export import export_all_capabilities
        written = export_all_capabilities(capabilities, output)
        click.echo(f"\nWritten {len(written)} capability files to {output}/")


# ── Backward compat aliases ─────────────────────────────────────

@cli.command("approvals", hidden=True)
@click.pass_context
def approvals_alias(ctx):
    """(Deprecated) Use 'aicp appr' instead."""
    click.echo("Hint: 'aicp approvals' is deprecated. Use 'aicp appr ls' instead.")


if __name__ == "__main__":
    cli()
