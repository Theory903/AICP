"""Serve runtime command."""

import click
from aicp_cli.context import get_runtime_context


@click.command("serve")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload")
@click.option("--store-backend", type=click.Choice(["memory", "file", "sqlite"]))
@click.option("--store-path", help="Path for durable state")
@click.pass_context
def serve_cmd(ctx, host, port, reload, store_backend, store_path):
    """Start the AICP runtime server as a standalone process.
    
    This provides an HTTP API for discovery, execution, and history.
    """
    import asyncio
    return asyncio.run(_run_serve(host, port, reload, store_backend, store_path))


async def _run_serve(host, port, reload, store_backend, store_path):
    import uvicorn
    from aicp_runtime.server.app import create_app
    
    # 1. Resolve runtime context to get project config defaults
    runtime = get_runtime_context()
    
    # 2. Use CLI overrides or fall back to project config
    backend = store_backend or runtime.config.runtime.store_backend
    path = store_path or runtime.config.runtime.store_path
    
    app = create_app(
        capability_provider=runtime.project.repository,
        policy_engine=runtime.project.policy_engine,
        store_path=path,
        store_backend=backend,
    )
    
    click.secho(f"Starting AICP Runtime on http://{host}:{port}", fg="green", bold=True)
    click.echo(f"Persistence: {backend} ({path or 'in-memory'})")

    config = uvicorn.Config(app, host=host, port=port, reload=reload, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
