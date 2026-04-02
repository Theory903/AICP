"""Approval queue commands."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import click

from aicp_cli.context import get_server_client, require_runtime_context


APPROVAL_STATUSES = ("pending", "approved", "rejected", "revoked", "expired", "all")


@click.group("appr")
def appr_group() -> None:
    """Approval queue operations for governance flows."""
    pass


@appr_group.command("ls")
@click.option(
    "--status",
    "-s",
    type=click.Choice(APPROVAL_STATUSES),
    default="pending",
    show_default=True,
)
@click.option("--limit", "-n", type=int, default=50, show_default=True, help="Maximum approvals to display.")
@click.option("--server", "-u", "server_url", help="AICP server URL (default: http://127.0.0.1:8000)")
def appr_ls(status: str, limit: int, server_url: str | None) -> None:
    """List pending or historical approval requests."""
    asyncio.run(_run_appr_list(status=status, limit=limit, server_url=server_url))


@appr_group.command("show")
@click.argument("approval_id")
@click.option("--server", "-u", "server_url", help="AICP server URL")
def appr_show(approval_id: str, server_url: str | None) -> None:
    """Show full details for a single approval request."""
    asyncio.run(_run_appr_show(approval_id, server_url))


@appr_group.command("ok")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", show_default=True, help="Approver identity.")
@click.option("--reason", "-r", help="Approval reason.")
@click.option("--server", "-u", "server_url", help="AICP server URL")
def appr_ok(approval_id: str, approver: str, reason: str | None, server_url: str | None) -> None:
    """Approve a pending request."""
    asyncio.run(_run_appr_decide(approval_id, "approved", approver, reason, server_url))


@appr_group.command("no")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", show_default=True, help="Rejector identity.")
@click.option("--reason", "-r", help="Rejection reason.")
@click.option("--server", "-u", "server_url", help="AICP server URL")
def appr_no(approval_id: str, approver: str, reason: str | None, server_url: str | None) -> None:
    """Reject a pending request."""
    asyncio.run(_run_appr_decide(approval_id, "rejected", approver, reason, server_url))


def _normalize_approval(record: Any) -> dict[str, Any]:
    """Normalize approval records from model/dict/object forms into a dictionary."""
    if record is None:
        return {}

    if isinstance(record, dict):
        return dict(record)

    model_dump = getattr(record, "model_dump", None)
    if callable(model_dump):
        return cast(dict[str, Any], model_dump(exclude_none=True))

    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return cast(dict[str, Any], to_dict())

    result: dict[str, Any] = {}
    for field in (
        "id",
        "capability_name",
        "status",
        "requested_at",
        "created_at",
        "message",
        "reason",
        "decided_by",
        "decided_at",
        "approver_role",
        "approver_email",
        "execution_id",
        "workflow_id",
        "arguments",
        "risk",
    ):
        if hasattr(record, field):
            value = getattr(record, field)
            if value is not None:
                result[field] = value

    return result


def _approval_timestamp(record: dict[str, Any]) -> str:
    """Extract the best available timestamp for display/sorting."""
    return str(
        record.get("requested_at")
        or record.get("created_at")
        or record.get("timestamp")
        or ""
    )


def _status_color(status: str) -> str:
    """Map approval status to a CLI color."""
    return {
        "pending": "yellow",
        "approved": "green",
        "rejected": "red",
        "revoked": "magenta",
        "expired": "bright_black",
    }.get(status, "white")


async def _run_appr_list(status: str, limit: int, server_url: str | None) -> None:
    """List approvals with filtering and formatting."""
    client = get_server_client(server_url)

    if client is not None:
        await _run_appr_list_server(client, status, limit)
        client.close()
        return

    runtime = require_runtime_context()

    if limit < 1:
        raise click.ClickException("--limit must be at least 1")

    try:
        approvals = await runtime.approvals.list_approvals()
    except Exception as exc:
        raise click.ClickException(f"Failed to load approvals: {exc}") from exc

    normalized = [_normalize_approval(item) for item in approvals]

    if status != "all":
        normalized = [item for item in normalized if item.get("status", "pending") == status]

    normalized.sort(key=_approval_timestamp, reverse=True)
    normalized = normalized[:limit]

    if not normalized:
        click.echo(f"No {status} approval requests found.")
        return

    for req in normalized:
        req_id = str(req.get("id", "?"))
        capability_name = str(req.get("capability_name", "?"))
        req_status = str(req.get("status", "pending"))
        timestamp = _approval_timestamp(req) or "?"

        click.echo("  [", nl=False)
        click.secho(req_id, fg="white", bold=True, nl=False)
        click.echo("] ", nl=False)

        click.secho(f"{capability_name:<34}", fg="cyan", nl=False)
        click.echo(" ", nl=False)
        click.secho(req_status, fg=_status_color(req_status), nl=False)
        click.echo(f" @ {timestamp}")


async def _run_appr_list_server(client: Any, status: str, limit: int) -> None:
    """List approvals from server."""
    try:
        approvals = client.list_approvals(status=status)
    except Exception as exc:
        raise click.ClickException(f"Failed to load approvals from server: {exc}") from exc

    approvals.sort(key=lambda x: x.get("requested_at", ""), reverse=True)
    approvals = approvals[:limit]

    if not approvals:
        click.echo(f"No {status} approval requests found.")
        return

    for req in approvals:
        req_id = str(req.get("id", "?"))
        capability_name = str(req.get("capability_name", "?"))
        req_status = str(req.get("status", "pending"))
        timestamp = req.get("requested_at") or req.get("created_at") or "?"

        click.echo("  [", nl=False)
        click.secho(req_id, fg="white", bold=True, nl=False)
        click.echo("] ", nl=False)

        click.secho(f"{capability_name:<34}", fg="cyan", nl=False)
        click.echo(" ", nl=False)
        click.secho(req_status, fg=_status_color(req_status), nl=False)
        click.echo(f" @ {timestamp}")


async def _run_appr_show(approval_id: str, server_url: str | None) -> None:
    """Show approval details."""
    client = get_server_client(server_url)

    if client is not None:
        await _run_appr_show_server(client, approval_id)
        client.close()
        return

    runtime = require_runtime_context()

    try:
        approval = await runtime.approvals.get_approval(approval_id)
    except Exception as exc:
        raise click.ClickException(f"Failed to get approval: {exc}") from exc

    normalized = _normalize_approval(approval)

    click.echo(f"Approval: {normalized.get('id', '?')}")
    click.echo(f"Capability: {normalized.get('capability_name', '?')}")
    click.echo(f"Status: {normalized.get('status', 'pending')}")
    click.echo(f"Requested: {normalized.get('requested_at', '?')}")
    click.echo(f"Arguments: {normalized.get('arguments', {})}")


async def _run_appr_show_server(client: Any, approval_id: str) -> None:
    """Show approval details from server."""
    try:
        approval = client.get_approval(approval_id)
    except Exception as exc:
        raise click.ClickException(f"Failed to get approval: {exc}") from exc

    click.echo(f"Approval: {approval.get('id', '?')}")
    click.echo(f"Capability: {approval.get('capability_name', '?')}")
    click.echo(f"Status: {approval.get('status', 'pending')}")
    click.echo(f"Requested: {approval.get('requested_at', '?')}")
    click.echo(f"Arguments: {approval.get('arguments', {})}")


async def _run_appr_decide(
    approval_id: str,
    decision: str,
    approver: str,
    reason: str | None,
    server_url: str | None,
) -> None:
    """Approve or reject an approval request."""
    client = get_server_client(server_url)

    if client is not None:
        await _run_appr_decide_server(client, approval_id, decision, approver, reason)
        client.close()
        return

    runtime = require_runtime_context()

    try:
        await runtime.approvals.decide(approval_id, decision, approver, reason)
    except Exception as exc:
        raise click.ClickException(f"Failed to record {decision} decision: {exc}") from exc

    status_word = "Approved" if decision == "approved" else "Rejected"
    click.secho(f"{status_word} [{approval_id}]", fg="green" if decision == "approved" else "red")


async def _run_appr_decide_server(
    client: Any,
    approval_id: str,
    decision: str,
    approver: str,
    reason: str | None,
) -> None:
    """Approve or reject from server."""
    try:
        client.decide_approval(approval_id, decision, approver, reason)
    except Exception as exc:
        raise click.ClickException(f"Failed to record {decision} decision: {exc}") from exc

    status_word = "Approved" if decision == "approved" else "Rejected"
    click.secho(f"{status_word} [{approval_id}]", fg="green" if decision == "approved" else "red")