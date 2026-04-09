"""aicp safe|ask|deny|approve|protect|limit — Quick policy effect shortcuts.

Usage:
    aicp safe notes.list              -> allow
    aicp ask payments.transfer        -> ask
    aicp deny notes.delete_all        -> deny
    aicp approve notes.delete         -> allow
    aicp protect notes.delete_all     -> require_approval
    aicp limit search.notes --rpm 60  -> limit with rpm=60

These update the rules in aicp.yaml directly.
"""

from __future__ import annotations

from pathlib import Path

import click

VALID_EFFECTS = {"allow", "ask", "deny", "require_approval", "limit"}


def _normalize_capability_name(capability: str) -> str:
    """Normalize a capability matcher string."""
    normalized = capability.strip()
    if not normalized:
        raise click.ClickException("Capability matcher cannot be empty.")
    return normalized


def _load_config_and_path() -> tuple[Path, object]:
    """Load the project config and its source path."""
    from aicp.config import find_config_file, load_project_config

    config_path = find_config_file()
    if config_path is None:
        raise click.ClickException("No aicp.yaml found. Run 'aicp init' first.")

    config = load_project_config(config_path)
    return config_path, config


def _find_rule_index(config: object, capability: str) -> int | None:
    """Find an existing rule index by exact matcher."""
    for index, rule in enumerate(config.rules):
        if rule.match == capability:
            return index
    return None


def _validate_policy_update(effect: str, rpm: int | None) -> None:
    """Validate effect-specific inputs."""
    if effect not in VALID_EFFECTS:
        raise click.ClickException(f"Invalid policy effect: {effect}")

    if effect == "limit":
        if rpm is None:
            raise click.ClickException("'limit' requires --rpm.")
        if rpm <= 0:
            raise click.ClickException("--rpm must be greater than 0.")
    elif rpm is not None:
        raise click.ClickException("--rpm is only valid with the 'limit' effect.")


def _print_rule_change(
    *,
    capability: str,
    effect: str,
    old_effect: str | None,
    rpm: int | None,
) -> None:
    """Print a small change preview."""
    action = "Updated" if old_effect is not None else "Added"

    click.secho(f"  {action}: ", fg="cyan", nl=False)
    click.echo(f"{capability}  ", nl=False)

    if old_effect is not None:
        click.secho(old_effect, fg="red", nl=False)
        click.echo(" -> ", nl=False)
        click.secho(effect, fg="green")
    else:
        click.echo("-> ", nl=False)
        click.secho(effect, fg="green")

    if rpm is not None:
        click.echo(f"    rpm: {rpm}")


def _set_policy_effect(
    capability: str,
    effect: str,
    reason: str | None = None,
    rpm: int | None = None,
) -> None:
    """Set a policy effect for a capability in aicp.yaml."""
    from aicp.config import PolicyRule, save_project_config

    capability = _normalize_capability_name(capability)
    _validate_policy_update(effect, rpm)

    config_path, config = _load_config_and_path()
    existing_idx = _find_rule_index(config, capability)
    old_effect = config.rules[existing_idx].effect if existing_idx is not None else None

    rule_kwargs: dict[str, object] = {
        "match": capability,
        "effect": effect,
    }
    if reason:
        rule_kwargs["reason"] = reason.strip()
    if rpm is not None:
        rule_kwargs["rpm"] = rpm

    new_rule = PolicyRule(**rule_kwargs)

    if existing_idx is not None:
        config.rules[existing_idx] = new_rule
    else:
        config.rules.append(new_rule)

    _print_rule_change(
        capability=capability,
        effect=effect,
        old_effect=old_effect,
        rpm=rpm,
    )

    save_project_config(config, config_path)

    click.echo()
    click.secho(f"✓ Saved to {config_path}", fg="green")


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why this capability is safe")
def safe(capability: str, reason: str | None) -> None:
    """Mark a capability as safe (allow without confirmation)."""
    _set_policy_effect(capability, "allow", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why confirmation is needed")
def ask(capability: str, reason: str | None) -> None:
    """Require confirmation before executing a capability."""
    _set_policy_effect(capability, "ask", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why this capability is denied")
def deny(capability: str, reason: str | None) -> None:
    """Block a capability from execution."""
    _set_policy_effect(capability, "deny", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Reason for approval")
def approve(capability: str, reason: str | None) -> None:
    """Approve a capability (allow without confirmation).

    Like 'safe', but reads better for governing workflows.
    """
    _set_policy_effect(capability, "allow", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Reason for protection")
def protect(capability: str, reason: str | None) -> None:
    """Protect a capability (require strict approval).

    Like 'ask', but maps to 'require_approval' instead of interactive confirmation.
    """
    _set_policy_effect(capability, "require_approval", reason)


@click.command()
@click.argument("capability")
@click.option("--rpm", type=int, required=True, help="Requests per minute limit")
@click.option("--reason", "-r", help="Reason for rate limit")
def limit(capability: str, rpm: int, reason: str | None) -> None:
    """Rate limit a capability.

    Example: aicp limit search.notes --rpm 60
    """
    _set_policy_effect(capability, "limit", reason, rpm)
