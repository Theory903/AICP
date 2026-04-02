"""Preview capability command."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from aicp_cli.context import require_runtime_context


@click.command("preview")
@click.argument("capability")
def preview_cmd(capability: str) -> None:
    """Show detailed technical and governance metadata for a capability.

    This includes matched policy rules, limits, tags, and full schemas.
    """
    exit_code = asyncio.run(_run_preview(capability))
    raise SystemExit(exit_code)


def _normalize(value: Any) -> Any:
    """Normalize values for display serialization."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_normalize(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True, mode="json")

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(value, "__dict__"):
        return {
            key: _normalize(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def _effect_color(effect: str) -> str:
    """Map policy effect to click color."""
    return {
        "allow": "green",
        "ask": "yellow",
        "limit": "magenta",
        "deny": "red",
    }.get(effect, "white")


def _status_color(is_deprecated: bool) -> str:
    """Map capability status to click color."""
    return "yellow" if is_deprecated else "green"


def _bool_color(value: bool) -> str:
    """Map boolean state to click color."""
    return "red" if value else "green"


def _dump_yaml(data: Any) -> str:
    """Render YAML safely."""
    try:
        import yaml
    except ImportError as exc:
        raise click.ClickException(
            "PyYAML is required for capability preview output"
        ) from exc

    return yaml.dump(
        _normalize(data),
        indent=2,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()


def _print_section(title: str) -> None:
    """Render a section heading."""
    click.echo()
    click.secho(title, fg="blue", bold=True)


async def _run_preview(capability_name: str) -> int:
    """Load and render a capability preview."""
    runtime = require_runtime_context()
    cap = await runtime.repository.get_capability(capability_name)

    if cap is None:
        click.secho(
            f"Error: Capability '{capability_name}' not found.", fg="red", bold=True
        )
        return 1

    is_destructive = bool(getattr(cap, "is_destructive", False))
    risk = getattr(cap, "risk", None)

    decision = await runtime.policy_engine.evaluate(
        capability_name,
        {},
        {
            "kind": cap.kind.value,
            "is_destructive": is_destructive,
            "tags": cap.tags,
        },
    )

    _print_header(cap)
    _print_metadata(cap)
    _print_governance(decision, is_destructive=is_destructive, risk=risk)
    _print_interface(cap)
    _print_hints(cap)

    return 0


def _print_header(cap: Any) -> None:
    """Render capability header."""
    click.secho(f"Capability: {cap.name}", fg="cyan", bold=True)
    if cap.description:
        click.echo(cap.description)


def _print_metadata(cap: Any) -> None:
    """Render general capability metadata."""
    _print_section("Metadata")

    click.echo(f"  Kind:        {cap.kind.value}")

    if cap.provider:
        provider_name = cap.provider.name or "unknown"
        provider_type = f" ({cap.provider.type})" if cap.provider.type else ""
        click.echo(f"  Provider:    {provider_name}{provider_type}")
        if cap.provider.url:
            click.echo(
                f"  Provider URL:{' ' if len('Provider URL:') < 12 else ''}{cap.provider.url}"
            )

    if cap.version:
        click.echo(f"  Version:     {cap.version}")

    if cap.tags:
        click.echo(f"  Tags:        {', '.join(cap.tags)}")

    click.echo("  Status:      ", nl=False)
    click.secho(
        "DEPRECATED" if cap.deprecated else "ACTIVE",
        fg=_status_color(cap.deprecated),
        bold=cap.deprecated,
    )

    if cap.deprecation_message:
        click.echo(f"  Deprecation: {cap.deprecation_message}")


def _print_governance(decision: Any, *, is_destructive: bool, risk: str | None) -> None:
    """Render governance and policy information."""
    _print_section("Governance")

    effect = decision.effect.value
    click.echo("  Effective Effect: ", nl=False)
    click.secho(effect.upper(), fg=_effect_color(effect), bold=True)

    click.echo(f"  Reason:           {decision.reason}")

    matched_rule = decision.metadata.get("matched_rule")
    if matched_rule:
        click.echo(f"  Matched Rule:     {matched_rule}")

    rpm = decision.metadata.get("rpm")
    if rpm:
        click.echo(f"  Rate Limit:       {rpm} requests per minute")

    if risk:
        risk_color = {
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "magenta",
        }.get(risk, "white")
        click.echo("  Risk:             ", nl=False)
        click.secho(risk.upper(), fg=risk_color)

    click.echo("  Destructive:      ", nl=False)
    click.secho("YES" if is_destructive else "NO", fg=_bool_color(is_destructive))


def _print_interface(cap: Any) -> None:
    """Render input/output schemas."""
    _print_section("Interface Definitions")

    click.secho("  Input Schema:", fg="cyan")
    click.echo(_dump_yaml(cap.input_schema))

    if cap.output_schema:
        click.secho("  Output Schema:", fg="cyan")
        click.echo(_dump_yaml(cap.output_schema))


def _print_hints(cap: Any) -> None:
    """Render render/continuation hints."""
    if not cap.render and not cap.continuation:
        return

    _print_section("UX & Flow Hints")

    if cap.render:
        click.echo(f"  Render Format:    {cap.render.format}")
        if cap.render.fields:
            click.echo(f"  Render Fields:    {', '.join(cap.render.fields)}")
        if cap.render.syntax:
            click.echo(f"  Render Syntax:    {cap.render.syntax}")
        if cap.render.max_length is not None:
            click.echo(f"  Max Length:       {cap.render.max_length}")
        click.echo(f"  Truncate:         {'YES' if cap.render.truncate else 'NO'}")

    if cap.continuation:
        click.echo(
            f"  Can Continue:     {'YES' if cap.continuation.can_continue else 'NO'}"
        )
        if cap.continuation.next_capabilities:
            click.echo(
                f"  Next Suggested:   {', '.join(cap.continuation.next_capabilities)}"
            )
        if cap.continuation.next_hint:
            click.echo(f"  Next Hint:        {cap.continuation.next_hint}")
