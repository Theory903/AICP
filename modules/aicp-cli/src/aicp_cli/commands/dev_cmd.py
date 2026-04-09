"""aicp dev — One-command local AICP development stack.

Starts:
    - Runtime server (discovery, execution, approvals, audit)
    - Mounts on user's app if configured
    - Hot reload
    - Capability summary at startup
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import click


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, show_default=True, help="Port")
@click.option("--app", "app_path", default=None, help="FastAPI app module override")
@click.option("--no-reload", is_flag=True, help="Disable hot reload")
def dev(host: str, port: int, app_path: str | None, no_reload: bool) -> None:
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

    asyncio.run(_dev(host, port, app_path, reload_enabled=not no_reload))


async def _dev(
    host: str,
    port: int,
    app_path: str | None,
    *,
    reload_enabled: bool,
) -> None:
    """Launch the development server."""
    from aicp.config import load_project_config
    from aicp.project_loader import load_project
    from aicp_runtime.server.app import create_app

    config = load_project_config()
    project = load_project()

    effective_app_path = app_path or config.app

    if effective_app_path:
        user_app = _try_import_app(effective_app_path)
        if user_app is not None:
            try:
                from aicp_connect_fastapi import mount_aicp

                mount_aicp(user_app)
                runtime_app = create_app(
                    capability_provider=project.repository,
                    policy_engine=project.policy_engine,
                )
                user_app.include_router(runtime_app.router, prefix="")
                runtime_app = user_app
                mounted = True
            except ImportError:
                click.secho(
                    "Warning: aicp-connect-fastapi not installed, using standalone runtime",
                    fg="yellow",
                )
                runtime_app = create_app(
                    capability_provider=project.repository,
                    policy_engine=project.policy_engine,
                )
                mounted = False
        else:
            runtime_app = create_app(
                capability_provider=project.repository,
                policy_engine=project.policy_engine,
            )
            mounted = False
    else:
        runtime_app = create_app(
            capability_provider=project.repository,
            policy_engine=project.policy_engine,
        )
        mounted = False

    _print_banner()
    _print_project_summary(
        host=host,
        port=port,
        config=config,
        project=project,
        mounted=mounted,
        app_path=effective_app_path,
        reload_enabled=reload_enabled,
    )

    await _serve_app(
        runtime_app,
        host=host,
        port=port,
        reload_enabled=reload_enabled,
        app_import_path=effective_app_path,
    )


def _try_import_app(app_spec: str) -> Any | None:
    """Try to import a user FastAPI app from module:app notation."""
    module_name, app_name = _parse_app_spec(app_spec)

    if "." not in sys.path:
        sys.path.insert(0, ".")

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        click.secho(
            f"Warning: Cannot import '{module_name}' ({exc}) — running standalone",
            fg="yellow",
        )
        return None

    app = getattr(module, app_name, None)
    if app is None:
        click.secho(
            f"Warning: No attribute '{app_name}' in module '{module_name}' — running standalone",
            fg="yellow",
        )
        return None

    return app


def _parse_app_spec(app_spec: str) -> tuple[str, str]:
    """Parse fastapi:module:app or module:app notation."""
    cleaned = app_spec.removeprefix("fastapi:")
    parts = cleaned.split(":")
    module_name = parts[0]
    app_name = parts[1] if len(parts) > 1 else "app"
    return module_name, app_name


def _print_banner() -> None:
    """Print startup banner."""
    click.echo()
    click.secho("╔══════════════════════════════════════════╗", fg="cyan")
    click.secho("║          AICP Development Server         ║", fg="cyan", bold=True)
    click.secho("╚══════════════════════════════════════════╝", fg="cyan")
    click.echo()


def _print_project_summary(
    *,
    host: str,
    port: int,
    config: Any,
    project: Any,
    mounted: bool,
    app_path: str | None,
    reload_enabled: bool,
) -> None:
    """Print startup summary for the loaded project."""
    from aicp.risk import infer_risk

    if mounted:
        click.secho("✓ AICP mounted on your FastAPI app", fg="green")
    elif app_path:
        click.secho("• Running standalone AICP runtime", fg="yellow")
    else:
        click.secho("• Running standalone AICP runtime", fg="yellow")

    if getattr(project, "warnings", None):
        for warning in project.warnings:
            click.secho(f"Warning: {warning}", fg="yellow")

    click.echo()

    capabilities = list(getattr(project, "capabilities", []))
    if capabilities:
        click.echo(f"  Capabilities: {len(capabilities)} loaded")
        for cap in capabilities[:10]:
            risk = infer_risk(cap.name, cap.kind)
            effect = config.effective_effect(
                capability_name=cap.name,
                kind=cap.kind.value,
                is_destructive=getattr(cap, "is_destructive", False),
            )
            click.echo(f"    • {cap.name:<34} {risk.value:<8} → {effect}")

        if len(capabilities) > 10:
            click.echo(f"    ... and {len(capabilities) - 10} more")
    else:
        caps_dir = Path(config.capabilities_dir)
        if caps_dir.exists():
            click.secho("  No capabilities loaded. Run 'aicp scan' first.", fg="yellow")
        else:
            click.secho(
                "  No capabilities directory found. Run 'aicp init' first.", fg="yellow"
            )

    click.echo()
    click.echo(f"  Server:    http://{host}:{port}")
    click.echo(f"  Discovery: http://{host}:{port}/.well-known/aicp")
    click.echo(f"  Approvals: http://{host}:{port}/approvals/")
    click.echo(f"  Audit:     http://{host}:{port}/history")
    click.echo(f"  Reload:    {'enabled' if reload_enabled else 'disabled'}")
    click.echo()
    click.secho("  Press Ctrl+C to stop", fg="bright_black")
    click.echo()


async def _serve_app(
    app: Any,
    *,
    host: str,
    port: int,
    reload_enabled: bool,
    app_import_path: str | None,
) -> None:
    """Serve the dev app via uvicorn."""
    import uvicorn

    # Reload works best with import strings, not live app objects.
    if reload_enabled and app_import_path:
        serve_target: Any = app_import_path.removeprefix("fastapi:")
    else:
        serve_target = app

    server_config = uvicorn.Config(
        serve_target,
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()
