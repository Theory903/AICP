"""Approval queue commands."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from aicp_cli.context import get_runtime_context


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
def appr_ls(status: str, limit: int) -> None:
    """List pending or historical approval requests."""
    asyncio.run(_run_appr_list(status=status, limit=limit))


@appr_group.command("show")
@click.argument("approval_id")
def appr_show(approval_id: str) -> None:
    """Show full details for a single approval request."""
    asyncio.run(_run_appr_show(approval_id))


@appr_group.command("ok")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", show_default=True, help="Approver identity.")
@click.option("--reason", "-r", help="Approval reason.")
def appr_ok(approval_id: str, approver: str, reason: str | None) -> None:
    """Approve a pending request."""
    asyncio.run(_run_appr_decide(approval_id, "approved", approver, reason))


@appr_group.command("no")
@click.argument("approval_id")
@click.option("--approver", "-a", default="cli-user", show_default=True, help="Rejector identity.")
@click.option("--reason", "-r", help="Rejection reason.")
def appr_no(approval_id: str, approver: str, reason: str | None) -> None:
    """Reject a pending request."""
    asyncio.run(_run_appr_decide(approval_id, "rejected", approver, reason))


def _normalize_approval(record: Any) -> dict[str, Any]:
    """Normalize approval records from model/dict/object forms into a dictionary."""
    if record is None:
        return {}

    if isinstance(record, dict):
        return dict(record)

    model_dump = getattr(record, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)

    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return to_dict()

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


async def _run_appr_list(status: str, limit: int) -> None:
    """List approvals with filtering and formatting."""
    runtime = get_runtime_context()

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
        click.secho(f"{req_status.upper():<10}", fg=_status_color(req_status), nl=False)
        click.echo(f" @ {timestamp}")

        if req.get("message"):
            click.secho(f"      Message: {req['message']}", fg="bright_black")

        if req.get("reason") and req_status != "pending":
            click.secho(f"      Reason: {req['reason']}", fg="bright_black")

        if req.get("decided_by") and req_status != "pending":
            click.secho(f"      By: {req['decided_by']}", fg="bright_black")


async def _run_appr_show(approval_id: str) -> None:
    """Show a single approval in detail."""
    runtime = get_runtime_context()

    try:
        record = await runtime.approvals.get_approval(approval_id)
    except Exception as exc:
        raise click.ClickException(f"Failed to load approval '{approval_id}': {exc}") from exc

    approval = _normalize_approval(record)
    if not approval:
        raise click.ClickException(f"Approval not found: {approval_id}")

    status = str(approval.get("status", "pending"))

    click.secho(f"Approval: {approval.get('id', approval_id)}", fg="white", bold=True)
    click.echo(f"Capability:   {approval.get('capability_name', '?')}")
    click.secho(f"Status:       {status}", fg=_status_color(status))
    click.echo(f"Requested At: {_approval_timestamp(approval) or '?'}")

    if approval.get("approver_role"):
        click.echo(f"Approver Role:  {approval['approver_role']}")
    if approval.get("approver_email"):
        click.echo(f"Approver Email: {approval['approver_email']}")
    if approval.get("execution_id"):
        click.echo(f"Execution ID: {approval['execution_id']}")
    if approval.get("workflow_id"):
        click.echo(f"Workflow ID:  {approval['workflow_id']}")
    if approval.get("decided_by"):
        click.echo(f"Decided By:   {approval['decided_by']}")
    if approval.get("decided_at"):
        click.echo(f"Decided At:   {approval['decided_at']}")
    if approval.get("reason"):
        click.echo(f"Reason:       {approval['reason']}")

    if approval.get("risk"):
        click.echo("Risk:")
        click.echo(f"  {approval['risk']}")

    if approval.get("arguments"):
        click.echo("Arguments:")
        for key, value in approval["arguments"].items():
            click.echo(f"  {key}: {value}")


async def _run_appr_decide(
    approval_id: str,
    decision: str,
    approver: str,
    reason: str | None,
) -> None:
    """Approve or reject an approval request."""
    runtime = get_runtime_context()

    try:
        await runtime.approvals.decide(
            approval_id=approval_id,
            decision=decision,
            approver=approver,
            reason=reason,
        )
    except Exception as exc:
        raise click.ClickException(f"Failed to record {decision} decision: {exc}") from exc

    color = "green" if decision == "approved" else "red"
    click.secho(f"✓ {decision.title()} [{approval_id}]", fg=color, bold=True)

    if reason:
        click.secho(f"  Reason: {reason}", fg="bright_black")