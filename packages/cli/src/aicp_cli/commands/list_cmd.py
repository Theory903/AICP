"""List capabilities command."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
from aicp.risk import infer_risk

from aicp_cli.context import require_runtime_context


@click.command("ls")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    show_default=True,
)
@click.option("--all", "show_all", is_flag=True, help="Show internal capabilities too")
@click.option("--verbose", "-v", is_flag=True, help="Show more detail")
def ls_cmd(fmt: str, show_all: bool, verbose: bool) -> None:
    """List all registered capabilities in the project.

    The table shows governance metadata including policy effect and destructive status.
    """
    exit_code = asyncio.run(_run_ls(fmt, show_all, verbose))
    raise SystemExit(exit_code)


async def _run_ls(fmt: str, show_all: bool, verbose: bool) -> int:
    """Load and render project capabilities."""
    runtime = require_runtime_context()

    for warning in runtime.project.warnings:
        click.secho(f"Warning: {warning}", fg="yellow", err=True)

    capabilities = list(runtime.capabilities)
    if not capabilities:
        click.secho("No capabilities found in the project.", fg="yellow")
        return 0

    if not show_all:
        capabilities = [cap for cap in capabilities if not cap.name.startswith("_")]

    capabilities.sort(key=lambda cap: cap.name)

    if fmt == "json":
        click.echo(
            json.dumps(
                [_serialize_capability(cap) for cap in capabilities],
                indent=2,
                default=str,
            )
        )
        return 0

    if fmt == "yaml":
        try:
            import yaml
        except ImportError as exc:
            raise click.ClickException("PyYAML is required for YAML output") from exc

        click.echo(
            yaml.dump(
                [_serialize_capability(cap) for cap in capabilities],
                default_flow_style=False,
                sort_keys=False,
            )
        )
        return 0

    await _render_table(runtime, capabilities, verbose)
    return 0


def _serialize_capability(cap: Any) -> dict[str, Any]:
    """Serialize a capability for JSON/YAML output."""
    if hasattr(cap, "model_dump"):
        return cap.model_dump(mode="json", exclude_none=True)
    if hasattr(cap, "to_dict"):
        return cap.to_dict()
    if isinstance(cap, dict):
        return dict(cap)
    return {"name": str(getattr(cap, "name", "<unknown>"))}


async def _collect_capability_rows(
    runtime: Any, capabilities: list[Any]
) -> list[dict[str, str]]:
    """Collect rendered row metadata for each capability."""
    rows: list[dict[str, str]] = []

    for cap in capabilities:
        is_destructive = bool(getattr(cap, "is_destructive", False))
        kind = getattr(cap.kind, "value", str(cap.kind))
        decision = await runtime.project.policy_engine.evaluate(
            cap.name,
            {},
            {
                "kind": kind,
                "is_destructive": is_destructive,
            },
        )
        risk = infer_risk(cap.name, cap.kind)

        rows.append(
            {
                "name": cap.name,
                "kind": kind,
                "risk": risk.value,
                "effect": decision.effect.value,
                "destructive": "●" if is_destructive else "○",
                "rule_match": str(decision.metadata.get("matched_rule") or "-"),
                "description": (cap.description or "").strip(),
            }
        )

    return rows


async def _render_table(runtime: Any, capabilities: list[Any], verbose: bool) -> None:
    """Render capability list in table format."""
    rows = await _collect_capability_rows(runtime, capabilities)

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold blue", box=None)
        table.add_column("Name", style="cyan", width=34)
        table.add_column("Kind", width=12)
        table.add_column("Risk", width=10)
        table.add_column("Policy", width=16)
        table.add_column("Dstr", width=5)

        if verbose:
            table.add_column("Rule Match", width=24)

        table.add_column("Description")

        for row in rows:
            risk_color = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
                "critical": "bold red",
            }.get(row["risk"], "white")

            policy_color = {
                "allow": "green",
                "ask": "yellow",
                "limit": "magenta",
                "deny": "red",
            }.get(row["effect"], "white")

            dstr_color = "red" if row["destructive"] == "●" else "bright_black"

            rendered_row = [
                row["name"],
                row["kind"],
                f"[{risk_color}]{row['risk'].upper()}[/{risk_color}]",
                f"[{policy_color}]{row['effect'].upper()}[/{policy_color}]",
                f"[{dstr_color}]{row['destructive']}[/{dstr_color}]",
            ]

            if verbose:
                rendered_row.append(row["rule_match"])

            desc = row["description"]
            rendered_row.append((desc[:60] + "...") if len(desc) > 60 else desc)

            table.add_row(*rendered_row)

        console.print(table)

    except ImportError:
        _render_plain_table(rows, verbose)


def _render_plain_table(rows: list[dict[str, str]], verbose: bool) -> None:
    """Render capability list without rich."""
    if verbose:
        header = f"{'Name':<34} {'Kind':<12} {'Risk':<10} {'Policy':<16} {'Dstr':<5} {'Rule Match':<24} Description"
    else:
        header = f"{'Name':<34} {'Kind':<12} {'Risk':<10} {'Policy':<16} {'Dstr':<5} Description"

    click.echo(header)
    click.echo("-" * len(header))

    for row in rows:
        desc = row["description"]
        short_desc = (desc[:60] + "...") if len(desc) > 60 else desc

        if verbose:
            click.echo(
                f"{row['name']:<34} "
                f"{row['kind']:<12} "
                f"{row['risk'].upper():<10} "
                f"{row['effect'].upper():<16} "
                f"{row['destructive']:<5} "
                f"{row['rule_match']:<24} "
                f"{short_desc}"
            )
        else:
            click.echo(
                f"{row['name']:<34} "
                f"{row['kind']:<12} "
                f"{row['risk'].upper():<10} "
                f"{row['effect'].upper():<16} "
                f"{row['destructive']:<5} "
                f"{short_desc}"
            )
