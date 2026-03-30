"""aicp bootstrap — One-command project scaffolding and scanning."""

import click

from aicp_cli.commands.init_cmd import init
from aicp_cli.commands.scan_cmd import scan_fastapi
from aicp_cli.commands.doctor_cmd import doctor


@click.group()
def bootstrap():
    """Bootstrap a new AICP project in one step.
    
    Runs init, scan, export, and doctor seamlessly.
    """
    pass


@bootstrap.command("fastapi")
@click.argument("app_spec")
@click.pass_context
def bootstrap_fastapi(ctx, app_spec):
    """Bootstrap an AICP project for a FastAPI app.
    
    APP_SPEC is the import path like 'app:app' or 'mypackage.main:app'
    
    Example:
        aicp bootstrap fastapi app:app
    """
    try:
        from rich.console import Console
        console = Console()
        console.print(f"[blue bold]🚀 Bootstrapping AICP for {app_spec}[/]")
    except ImportError:
        click.secho(f"🚀 Bootstrapping AICP for {app_spec}", fg="blue", bold=True)
        
    click.echo()
    
    # Step 1: Init
    click.secho("── Step 1: Initializing project structure ──", fg="cyan", bold=True)
    ctx.invoke(init, app_path=app_spec, openapi_path=None, force=True)
    click.echo()
    
    # Step 2: Scan
    click.secho("── Step 2: Scanning application & exporting YAML ──", fg="cyan", bold=True)
    ctx.invoke(scan_fastapi, module_app=app_spec, output=None, write=True)
    click.echo()
    
    # Step 3: Doctor
    click.secho("── Step 3: Running diagnostics & governance checks ──", fg="cyan", bold=True)
    ctx.invoke(doctor, fix=False, verbose=False)
    
    click.echo()
    try:
        from rich.panel import Panel
        from rich.text import Text
        from rich.box import ROUNDED
        
        t = Text()
        t.append("Your project is now AICP-ready.\n\n", style="green bold")
        t.append("Next Steps:\n", style="bold")
        t.append("1. Run ", style="dim")
        t.append("aicp dev", style="cyan bold")
        t.append(" to start the runtime\n", style="dim")
        t.append("2. Run ", style="dim")
        t.append("aicp preview <capability>", style="cyan bold")
        t.append(" to inspect the generated surface\n", style="dim")
        t.append("3. Tweak policies with ", style="dim")
        t.append("aicp protect <capability>", style="cyan bold")
        
        console.print(Panel(t, title="✨ Bootstrap Complete!", border_style="green", box=ROUNDED))
    except ImportError:
        click.secho("✨ Bootstrap complete! Your project is AICP-ready.", fg="green", bold=True)
        click.echo("  1. Run 'aicp dev' to start the runtime")
        click.echo("  2. Run 'aicp preview <capability>' to inspect surface")
        click.echo("  3. Run 'aicp protect <capability>' to tweak policies")
