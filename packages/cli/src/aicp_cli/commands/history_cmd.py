"""Audit logs history command."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import click

from aicp_cli.context import require_runtime_context


@click.command("logs")
@click.option("--tail", "-n", default=20, show_default=True, help="Number of entries")
@click.option("--capability", "-c", "cap_filter", help="Filter by capability")
@click.option("--workflow", "-w", "wf_filter", help="Filter by workflow ID")
def logs_cmd(tail: int, cap_filter: str | None, wf_filter: str | None) -> None:
    """Show audit log entries from the runtime journal.

    Examples:
        aicp logs
        aicp logs -n 50
        aicp logs -c notes.create
    """
    if tail < 1:
        raise click.ClickException("--tail must be at least 1")

    exit_code = asyncio.run(_run_logs(tail, cap_filter, wf_filter))
    raise SystemExit(exit_code)


def _normalize_entry(entry: Any) -> dict[str, Any]:
    """Normalize audit entries from model/dict/object forms into a dictionary."""
    if entry is None:
        return {}

    if isinstance(entry, dict):
        return dict(entry)

    model_dump = getattr(entry, "model_dump", None)
    if callable(model_dump):
        return cast(dict[str, Any], model_dump(exclude_none=True))

    to_dict = getattr(entry, "to_dict", None)
    if callable(to_dict):
        return cast(dict[str, Any], to_dict())

    result: dict[str, Any] = {}
    for field in (
        "timestamp",
        "capability_name",
        "event_type",
        "actor",
        "status",
        "error",
        "reason",
        "workflow_id",
        "approval_request_id",
    ):
        if hasattr(entry, field):
            value = getattr(entry, field)
            if value is not None:
                result[field] = value

    return result


def _entry_timestamp(entry: dict[str, Any]) -> str:
    """Extract best available timestamp for sorting/display."""
    return str(
        entry.get("timestamp")
        or entry.get("created_at")
        or entry.get("updated_at")
        or ""
    )


def _status_color(status: str) -> str:
    """Map log status to CLI color."""
    normalized = status.lower()
    if normalized in {"success", "completed", "approved"}:
        return "green"
    if normalized in {"failure", "failed", "error", "rejected"}:
        return "red"
    if normalized in {"warning", "warn"}:
        return "yellow"
    return "blue"


def _render_entry(entry: dict[str, Any]) -> None:
    """Render a single normalized audit entry."""
    ts = _entry_timestamp(entry) or "?"
    name = str(entry.get("capability_name") or entry.get("event_type") or "?")
    actor = str(entry.get("actor", "system"))
    status = str(entry.get("status", "info"))

    click.echo(f"[{ts}] ", nl=False)
    click.secho(f"{name:<25}", fg="cyan", nl=False)
    click.echo(f"  {actor:<10}  ", nl=False)
    click.secho(status.upper(), fg=_status_color(status))

    if entry.get("error"):
        click.secho(f"      Error: {entry['error']}", fg="bright_black")
    elif entry.get("reason"):
        click.secho(f"      Reason: {entry['reason']}", fg="bright_black")


async def _run_logs(tail: int, cap_filter: str | None, wf_filter: str | None) -> int:
    """Load and render audit log entries."""
    runtime = require_runtime_context()

    try:
        entries = await runtime.audit.list_entries(
            capability_name=cap_filter,
            workflow_id=wf_filter,
        )
    except Exception as exc:
        raise click.ClickException(f"Failed to load audit entries: {exc}") from exc

    normalized = [_normalize_entry(entry) for entry in entries]
    normalized.sort(key=_entry_timestamp, reverse=True)
    display_entries = normalized[:tail]

    if not display_entries:
        click.echo("No audit entries found in the current persistence backend.")
        return 0

    for entry in display_entries:
        _render_entry(entry)

    return 0
