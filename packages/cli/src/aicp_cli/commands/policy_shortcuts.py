"""aicp safe|ask|deny|approve|protect|limit — Quick policy effect shortcuts.

Usage:
    aicp safe notes.list           → allow
    aicp ask  payments.transfer    → ask (require confirmation)
    aicp deny notes.delete_all     → deny
    aicp approve notes.delete      → allow
    aicp protect notes.delete_all  → require_approval
    aicp limit search.notes --rpm 60 → limit with rpm=60

These update the rules in aicp.yaml directly.
"""

import click


def _set_policy_effect(capability: str, effect: str, reason: str | None = None, rpm: int | None = None):
    """Set a policy effect for a capability in aicp.yaml."""
    from aicp.config import PolicyRule, find_config_file, load_project_config, save_project_config

    config_file = find_config_file()
    if not config_file:
        click.secho("No aicp.yaml found. Run 'aicp init' first.", fg="red")
        return

    config = load_project_config()

    # Check if a rule already exists for this capability
    existing_idx = None
    for i, rule in enumerate(config.rules):
        if rule.match == capability:
            existing_idx = i
            break

    kwargs = {}
    if reason:
        kwargs["reason"] = reason
    if rpm is not None:
        kwargs["rpm"] = rpm

    new_rule = PolicyRule(match=capability, effect=effect, **kwargs)

    # Show a visually appealing diff preview
    action = "Updated" if existing_idx is not None else "Added"
    old_effect = config.rules[existing_idx].effect if existing_idx is not None else None
    
    if existing_idx is not None:
        config.rules[existing_idx] = new_rule
        click.secho(f"  {action}: ", fg="cyan", nl=False)
        click.echo(f"{capability}  ", nl=False)
        click.secho(f"{old_effect}", fg="red", nl=False)
        click.echo(" → ", nl=False)
        click.secho(f"{effect}", fg="green")
    else:
        config.rules.append(new_rule)
        click.secho(f"  {action}: ", fg="cyan", nl=False)
        click.echo(f"{capability} ", nl=False)
        click.echo("→ ", nl=False)
        click.secho(f"{effect}", fg="green")
        if rpm:
            click.echo(f"    rpm: {rpm}")

    save_project_config(config, config_file)
    click.echo()
    click.secho(f"✓ Saved to {config_file}", fg="green")


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why this capability is safe")
def safe(capability, reason):
    """Mark a capability as safe (allow without confirmation)."""
    _set_policy_effect(capability, "allow", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why confirmation is needed")
def ask(capability, reason):
    """Require confirmation before executing a capability."""
    _set_policy_effect(capability, "ask", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Why this capability is denied")
def deny(capability, reason):
    """Block a capability from execution."""
    _set_policy_effect(capability, "deny", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Reason for approval")
def approve(capability, reason):
    """Approve a capability (allow without confirmation).
    
    Like 'safe', but reads better for governing workflows.
    """
    _set_policy_effect(capability, "allow", reason)


@click.command()
@click.argument("capability")
@click.option("--reason", "-r", help="Reason for protection")
def protect(capability, reason):
    """Protect a capability (require strict approval).
    
    Like 'ask', but maps to 'require_approval' instead of interactive confirmation.
    """
    _set_policy_effect(capability, "require_approval", reason)


@click.command()
@click.argument("capability")
@click.option("--rpm", type=int, required=True, help="Requests per minute limit")
@click.option("--reason", "-r", help="Reason for rate limit")
def limit(capability, rpm, reason):
    """Rate limit a capability.
    
    Example: aicp limit search.notes --rpm 60
    """
    _set_policy_effect(capability, "limit", reason, rpm)
