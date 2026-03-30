"""aicp dev — One-command local AICP development stack.

Starts:
    - Runtime server (discovery, execution, approvals, audit)
    - Mounts on user's app if configured
    - Hot reload
    - Capability summary at startup
"""

import click


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port")
@click.option("--app", "app_path", default=None, help="FastAPI app module override")
@click.option("--no-reload", is_flag=True, help="Disable hot reload")
def dev(host, port, app_path, no_reload):
    """Start the AICP development server.

    Loads aicp.yaml, starts the runtime with discovery,
    execution, approvals, and audit endpoints, and optionally
    mounts AICP on your FastAPI application.

    Examples:
        aicp dev
        aicp dev --port 9000
        aicp dev --app myapp:app
    """
    import asyncio

    asyncio.run(_dev(host, port, app_path, not no_reload))


async def _dev(host, port, app_path, reload):
    """Launch the development server."""
    import importlib
    import sys
    from pathlib import Path

    from aicp.config import load_project_config
    from aicp.risk import infer_risk

    config = load_project_config()

    # Determine app source
    effective_app_path = app_path or config.app
    user_app = None

    if effective_app_path:
        # Parse fastapi:module:app or module:app format
        parts = effective_app_path.replace("fastapi:", "").split(":")
        module_name = parts[0]
        app_name = parts[1] if len(parts) > 1 else "app"

        if "." not in sys.path:
            sys.path.insert(0, ".")

        try:
            module = importlib.import_module(module_name)
            user_app = getattr(module, app_name, None)
        except ImportError:
            click.secho(f"Warning: Cannot import '{module_name}' — running standalone", fg="yellow")

    # Create the AICP runtime app
    from aicp_runtime.server.app import create_app

    if user_app:
        # Mount AICP onto user's app
        try:
            from aicp_connect_fastapi import mount_aicp

            mount_aicp(user_app)
            runtime_app = user_app
            click.secho("✓ AICP mounted on your FastAPI app", fg="green")
        except ImportError:
            click.secho("Warning: aicp-connect-fastapi not installed, using standalone", fg="yellow")
            runtime_app = create_app()
    else:
        runtime_app = create_app()

    # Print startup banner
    click.echo()
    click.secho("╔══════════════════════════════════════════╗", fg="cyan")
    click.secho("║          AICP Development Server         ║", fg="cyan", bold=True)
    click.secho("╚══════════════════════════════════════════╝", fg="cyan")
    click.echo()

    # Show loaded capabilities
    caps_dir = Path(config.capabilities_dir)
    if caps_dir.exists():
        cap_files = list(caps_dir.glob("*.yaml"))
        if cap_files:
            click.echo(f"  Capabilities: {len(cap_files)} loaded")
            try:
                import yaml

                for f in sorted(cap_files)[:10]:
                    with open(f) as fh:
                        cap = yaml.safe_load(fh)
                        if cap:
                            risk = infer_risk(cap.get("name", ""), cap.get("kind"))
                            effect = config.effective_effect(
                                cap.get("name", ""),
                                cap.get("kind", "action"),
                            )
                            click.echo(f"    • {cap['name']:<30} {risk.value:<8} → {effect}")
                if len(cap_files) > 10:
                    click.echo(f"    ... and {len(cap_files) - 10} more")
            except Exception:
                pass
        else:
            click.secho("  No capabilities found. Run 'aicp scan' first.", fg="yellow")
    else:
        click.secho("  No capabilities directory. Run 'aicp init' first.", fg="yellow")

    # Show endpoints
    click.echo()
    click.echo(f"  Server:    http://{host}:{port}")
    click.echo(f"  Discovery: http://{host}:{port}/.well-known/aicp")
    click.echo(f"  Approvals: http://{host}:{port}/approvals/")
    if reload:
        click.echo(f"  Reload:    enabled")
    click.echo()
    click.secho("  Press Ctrl+C to stop", fg="dim")
    click.echo()

    # Start server
    import uvicorn

    uvi_config = uvicorn.Config(
        runtime_app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
    server = uvicorn.Server(uvi_config)
    await server.serve()
