"""Preview capability command."""

import click
import yaml
from aicp_cli.context import get_runtime_context


@click.command("preview")
@click.argument("capability")
@click.pass_context
def preview_cmd(ctx, capability):
    """Show detailed technical and governance metadata for a capability.
    
    This includes the matched policy rule, rate limits, and full schemas.
    """
    import asyncio
    return asyncio.run(_run_preview(capability))


async def _run_preview(capability_name):
    runtime = get_runtime_context()
    cap = await runtime.project.repository.get_capability(capability_name)
    
    if not cap:
        click.secho(f"Error: Capability '{capability_name}' not found.", fg="red", bold=True)
        return

    # 1. Evaluate policy with full context
    is_destructive = getattr(cap, "is_destructive", False)
    decision = await runtime.project.policy_engine.evaluate(
        capability_name, 
        {}, 
        {
            "kind": cap.kind.value,
            "is_destructive": is_destructive,
            "tags": cap.tags
        }
    )

    # 2. Render Header
    click.secho(f"Capability: {cap.name}", fg="cyan", bold=True)
    if cap.description:
        click.echo(f"{cap.description}")
    
    # 3. Component Metadata
    click.echo("\nMetadata:")
    click.echo(f"  Kind:        {cap.kind.value}")
    if cap.provider:
        p_name = cap.provider.name or "unknown"
        click.echo(f"  Provider:    {p_name}")
    if cap.tags:
        click.echo(f"  Tags:        {', '.join(cap.tags)}")
    status_str = "DEPRECATED" if cap.deprecated else "ACTIVE"
    status_color = "yellow" if cap.deprecated else "green"
    click.echo(f"  Status:      ", nl=False)
    click.secho(status_str, fg=status_color)

    # 4. Governance Section
    click.echo("\nGovernance:")
    effect = decision.effect.value
    color = "green" if effect == "allow" else "yellow" if effect == "ask" else "red"
    
    click.echo(f"  Effective Effect: ", nl=False)
    click.secho(effect.upper(), fg=color, bold=True)
    
    click.echo(f"  Reason:           {decision.reason}")
    
    if decision.metadata.get("matched_rule"):
        click.echo(f"  Matched Rule:     {decision.metadata['matched_rule']}")
    
    if decision.metadata.get("rpm"):
        click.echo(f"  Rate Limit:       {decision.metadata['rpm']} requests per minute")
        
    dstr_str = "YES (High Risk)" if is_destructive else "NO"
    dstr_color = "red" if is_destructive else "green"
    click.echo(f"  Destructive:      ", nl=False)
    click.secho(dstr_str, fg=dstr_color)

    # 5. Interface Section
    click.echo("\nInterface Definitions:")
    
    click.secho("  Input Schema:", fg="blue")
    click.echo(yaml.dump(cap.input_schema.model_dump(exclude_none=True), indent=4))
    
    if cap.output_schema:
        click.secho("  Output Schema:", fg="blue")
        click.echo(yaml.dump(cap.output_schema.model_dump(exclude_none=True), indent=4))
    
    # 6. Hints Section
    if cap.render or cap.continuation:
        click.echo("\nUX & Flow Hints:")
        if cap.render:
            click.echo(f"  Render Format:    {cap.render.format}")
        if cap.continuation and cap.continuation.next_capabilities:
            click.echo(f"  Next Suggested:   {', '.join(cap.continuation.next_capabilities)}")
