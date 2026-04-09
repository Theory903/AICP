"""Execute capability command."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from aicp_cli.context import get_server_client, require_runtime_context


@click.command("run")
@click.argument("capability")
@click.option("--input", "-i", "input_data", help="JSON input string or @file path")
@click.option(
    "--context",
    "-c",
    "context_data",
    default="{}",
    show_default=True,
    help="JSON context",
)
@click.option(
    "--server",
    "-u",
    "server_url",
    help="AICP server URL (default: http://127.0.0.1:8000)",
)
@click.option(
    "--yes",
    "-y",
    "auto_approve",
    is_flag=True,
    help="Auto-approve the current approval request",
)
@click.option(
    "--no-input", is_flag=True, help="Never prompt; print approval ID and exit"
)
@click.option("--verbose", is_flag=True, help="Show full approval payload")
def run_cmd(
    capability: str,
    input_data: str | None,
    context_data: str,
    server_url: str | None,
    auto_approve: bool,
    no_input: bool,
    verbose: bool,
) -> None:
    """Execute a capability by name.

    Examples:
        aicp run notes.create -i '{"title": "Hello"}'
        aicp run notes.list
        aicp run notes.delete -i @fixture.json
        aicp run notes.create -i '{"title":"Hi"}' --yes
    """
    args = _load_json_input(input_data, flag_name="--input", default={})
    context = _parse_json_object(context_data, flag_name="--context")

    exit_code = asyncio.run(
        _run_execution(
            capability,
            args,
            context,
            server_url,
            auto_approve=auto_approve,
            no_input=no_input,
            verbose=verbose,
        )
    )
    raise SystemExit(exit_code)


def _load_json_input(
    raw: str | None,
    *,
    flag_name: str,
    default: dict[str, Any],
) -> dict[str, Any]:
    """Load JSON input from inline string or @file path."""
    if raw is None or raw.strip() == "":
        return dict(default)

    try:
        if raw.startswith("@"):
            file_path = Path(raw[1:])
            with file_path.open("r", encoding="utf-8") as f:
                parsed = json.load(f)
        else:
            parsed = json.loads(raw)
    except FileNotFoundError as exc:
        raise click.ClickException(
            f"{flag_name}: file not found: {exc.filename}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{flag_name}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise click.ClickException(
            f"{flag_name}: failed to read input file: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise click.ClickException(f"{flag_name}: expected a JSON object")

    return parsed


def _parse_json_object(raw: str, *, flag_name: str) -> dict[str, Any]:
    """Parse a JSON object from a CLI flag."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{flag_name}: invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise click.ClickException(f"{flag_name}: expected a JSON object")

    return parsed


def _normalize_output(value: Any) -> Any:
    """Normalize results for JSON serialization."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_normalize_output(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize_output(item) for key, item in value.items()}

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True, mode="json")

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(value, "__dict__"):
        return {
            key: _normalize_output(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def _is_interactive() -> bool:
    """Check if stdin is a TTY (interactive terminal)."""
    return sys.stdin.isatty()


def _compact_args(args: dict[str, Any], max_width: int = 60) -> str:
    """Format arguments as a compact single-line preview."""
    compact = json.dumps(args, separators=(",", ":"), default=str)
    if len(compact) <= max_width:
        return compact
    return compact[: max_width - 3] + "..."


async def _run_execution(
    capability_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    server_url: str | None,
    *,
    auto_approve: bool = False,
    no_input: bool = False,
    verbose: bool = False,
) -> int:
    """Execute a capability using the active runtime context or server."""
    client = get_server_client(server_url)

    if client is not None:
        return await _run_execution_server(
            client,
            capability_name,
            args,
            auto_approve=auto_approve,
            no_input=no_input,
            verbose=verbose,
        )

    runtime = require_runtime_context()

    cap = await runtime.repository.get_capability(capability_name)
    if cap is None:
        click.secho(
            f"Error: Capability '{capability_name}' not found.", fg="red", bold=True
        )
        return 1

    exec_context = dict(context)
    exec_context.setdefault("kind", cap.kind.value)
    exec_context.setdefault("is_destructive", getattr(cap, "is_destructive", False))

    try:
        result = await runtime.executor.execute(capability_name, args, exec_context)
    except Exception as exc:
        click.secho(f"Execution failed: {exc}", fg="red", bold=True)
        return 1

    click.echo(json.dumps(_normalize_output(result), indent=2, default=str))

    status = getattr(result, "status", None)
    status_value = getattr(status, "value", status)
    return 0 if status_value == "success" else 1


async def _run_execution_server(
    client: Any,
    capability_name: str,
    args: dict[str, Any],
    *,
    auto_approve: bool = False,
    no_input: bool = False,
    verbose: bool = False,
    max_retries: int = 3,
) -> int:
    """Execute a capability via the server with inline approval prompt."""
    for attempt in range(max_retries):
        try:
            result = client.execute(capability_name, args)
        except Exception as exc:
            click.secho(f"Execution failed: {exc}", fg="red", bold=True)
            return 1

        if verbose:
            click.echo(json.dumps(result, indent=2, default=str))

        status = result.get("status")

        if status == "success" or status == "completed":
            if not verbose:
                click.echo(
                    json.dumps(
                        _normalize_output(result.get("data")), indent=2, default=str
                    )
                )
            return 0

        approval_req = result.get("approval_request")
        if approval_req is None:
            if not verbose:
                click.echo(json.dumps(_normalize_output(result), indent=2, default=str))
            return 1

        approval_id = approval_req.get("id")
        if not approval_id:
            return 1

        approval_status = result.get("approval_status") or approval_req.get(
            "status", ""
        )

        if approval_status.lower() in ("approved",):
            continue

        if approval_status.lower() in ("rejected",):
            click.secho("Approval was rejected.", fg="red")
            return 1

        if approval_status.lower() != "pending":
            return 1

        reason = result.get("error", {}).get("message", "") or approval_req.get(
            "trigger", {}
        ).get("reason", "")
        approval_args = approval_req.get("arguments", {})
        compact_input = _compact_args(approval_args)

        click.echo()
        click.secho("Approval required", fg="yellow", bold=True)
        click.echo(f"  Capability: {capability_name}")
        click.echo(f"  Reason:     {reason}")
        click.echo(f"  Input:      {compact_input}")
        click.echo()

        if no_input or (not auto_approve and not _is_interactive()):
            click.echo(f"  Approval ID: {approval_id}")
            click.echo("  Run: aicp appr ok " + approval_id)
            return 1

        if auto_approve:
            decision = "y"
        else:
            decision = click.prompt(
                "  Approve this request",
                type=click.Choice(["y", "n"], case_sensitive=False),
                default="n",
                show_default=False,
            )

        if decision.lower() != "y":
            try:
                client.decide_approval(
                    approval_id, "rejected", "cli-user", "Rejected by user"
                )
            except Exception:
                pass
            click.secho("  Rejected.", fg="red")
            return 1

        try:
            client.decide_approval(approval_id, "approved", "cli-user")
        except Exception as exc:
            click.secho(f"  Failed to approve: {exc}", fg="red")
            return 1

        click.secho("  Approved. Retrying execution...", fg="green")
        continue

    return 1


async def _wait_for_approval(client: Any, approval_id: str, max_wait: int = 60) -> bool:
    """Poll for approval decision."""
    import time

    for _ in range(max_wait):
        time.sleep(1)
        try:
            approval = client.get_approval(approval_id)
            status = str(approval.get("status") or "").strip().lower()
            if status in ("approved", "rejected"):
                return status == "approved"
        except Exception:
            pass
    return False
