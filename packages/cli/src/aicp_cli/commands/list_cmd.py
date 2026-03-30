"""List capabilities command."""

import click
from aicp_cli.context import get_runtime_context


@click.command("ls")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "yaml"]), default="table")
@click.option("--all", "-a", is_flag=True, help="Show all internal capabilities")
@click.option("--verbose", "-v", is_flag=True, help="Show more detail")
@click.pass_context
def ls_cmd(ctx, fmt, all, verbose):
    """List all registered capabilities in the project.
    
    The table shows govnernance metadata including Risk and Destructive status.
    """
    import asyncio
    return asyncio.run(_run_ls(fmt, all, verbose))


async def _run_ls(fmt, show_all, verbose):
    runtime = get_runtime_context()
    
    # Debug warnings
    for warning in runtime.project.warnings:
        click.secho(f"Warning: {warning}", fg="yellow", err=True)

    capabilities = runtime.project.capabilities
    
    if not capabilities:
        click.secho("No capabilities found in the project.", fg="yellow")
        return

    # Filter internal or hidden caps if needed (simplified for now)
    if not show_all:
        capabilities = [c for c in capabilities if not c.name.startswith("_")]

    if fmt == "json":
        import json
        click.echo(json.dumps([c.model_dump(mode="json") for c in capabilities], indent=2))
        return
    
    if fmt == "yaml":
        import yaml
        click.echo(yaml.dump([c.model_dump(mode="json") for c in capabilities], default_flow_style=False))
        return

    # Table format (Rich)
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold blue", box=None)
        table.add_column("Name", style="cyan", width=30)
        table.add_column("Kind", width=12)
        table.add_column("Risk", width=10)
        table.add_column("Dstr", width=5)  # Destructive
        if verbose:
            table.add_column("Rule Match", width=20)
        table.add_column("Description")

        for cap in capabilities:
            # Eval policy for each to get risk/rule info (optional optimization later)
            decision = await runtime.project.policy_engine.evaluate(
                cap.name, {}, {"kind": cap.kind.value}
            )
            
            risk_color = "green" if decision.effect.value == "allow" else "yellow" if decision.effect.value == "ask" else "red"
            is_destructive = getattr(cap, "is_destructive", False)
            dstr_str = "●" if is_destructive else "○"
            dstr_color = "red" if is_destructive else "dim white"
            
            row = [
                cap.name,
                cap.kind.value,
                f"[{risk_color}]{decision.effect.value.upper()}[/{risk_color}]",
                f"[{dstr_color}]{dstr_str}[/{dstr_color}]"
            ]
            
            if verbose:
                row.append(decision.metadata.get("matched_rule") or "-")
                
            desc = cap.description or ""
            row.append((desc[:50] + "...") if len(desc) > 50 else desc)
            
            table.add_row(*row)
            
        console.print(table)
        
    except ImportError:
        # Fallback without rich
        header = f"{'Name':<30} {'Kind':<12} {'Risk':<10} {'Dstr':<5} {'Description'}"
        click.echo(header)
        click.echo("-" * len(header))
        for cap in capabilities:
            is_destructive = getattr(cap, "is_destructive", False)
            dstr_str = "YES" if is_destructive else "NO"
            click.echo(f"{cap.name:<30} {cap.kind.value:<12} {'ALLOW':<10} {dstr_str:<5} {cap.description[:40]}")
