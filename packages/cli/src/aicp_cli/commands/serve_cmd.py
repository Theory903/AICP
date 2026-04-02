"""Serve runtime command."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from aicp_cli.context import require_runtime_context


@click.command("serve")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload")
@click.option("--store-backend", type=click.Choice(["memory", "file", "sqlite"]))
@click.option("--store-path", help="Path for durable state")
def serve_cmd(
    host: str,
    port: int,
    reload: bool,
    store_backend: str | None,
    store_path: str | None,
) -> None:
    """Start the AICP runtime server as a standalone process.

    This provides an HTTP API for discovery, execution, and history.
    """
    exit_code = asyncio.run(_run_serve(host, port, reload, store_backend, store_path))
    raise SystemExit(exit_code)


def _validate_serve_args(host: str, port: int) -> None:
    """Validate serve command arguments."""
    if not str(host).strip():
        raise click.ClickException("Host cannot be empty.")

    if not (1 <= int(port) <= 65535):
        raise click.ClickException("Port must be between 1 and 65535.")


def _load_uvicorn() -> tuple[Any, Any]:
    """Load uvicorn lazily."""
    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException(
            "uvicorn is not installed. Install it with: pip install uvicorn"
        ) from exc

    return uvicorn.Config, uvicorn.Server


def _resolve_runtime_settings(
    runtime: Any,
    store_backend: str | None,
    store_path: str | None,
) -> tuple[str, str | None]:
    """Resolve runtime persistence settings using CLI overrides or config defaults."""
    backend = store_backend or runtime.config.runtime.store_backend
    path = store_path or runtime.config.runtime.store_path

    if backend == "memory":
        return backend, None

    if path:
        return backend, str(Path(path))

    if backend == "sqlite":
        return backend, str(Path(".aicp") / "runtime.db")

    if backend == "file":
        return backend, str(Path(".aicp") / "runtime")

    return backend, None


def _print_startup_banner(
    host: str, port: int, backend: str, path: str | None, reload: bool
) -> None:
    """Print startup information."""
    click.secho(f"Starting AICP Runtime on http://{host}:{port}", fg="green", bold=True)

    if backend == "memory":
        click.echo("Persistence: memory (non-durable)")
    else:
        click.echo(f"Persistence: {backend} ({path})")

    click.echo(f"Reload: {'enabled' if reload else 'disabled'}")


async def _run_serve(
    host: str,
    port: int,
    reload: bool,
    store_backend: str | None,
    store_path: str | None,
) -> int:
    """Create and serve the standalone runtime app."""
    from aicp_runtime.server.app import create_app

    _validate_serve_args(host, port)
    Config, Server = _load_uvicorn()

    try:
        runtime = require_runtime_context()
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(
            f"Failed to initialize runtime context: {exc}"
        ) from exc

    backend, path = _resolve_runtime_settings(runtime, store_backend, store_path)

    try:
        app = create_app(
            capability_provider=runtime.project.repository,
            policy_engine=runtime.project.policy_engine,
            store_path=path,
            store_backend=backend,
        )
    except Exception as exc:
        raise click.ClickException(f"Failed to create runtime app: {exc}") from exc

    _print_startup_banner(host, port, backend, path, reload)

    try:
        config = Config(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
        server = Server(config)
        await server.serve()
    except Exception as exc:
        raise click.ClickException(f"Runtime server failed: {exc}") from exc

    return 0
