"""aicp init — Scaffold a new AICP project.

Creates:
    aicp.yaml                   Project config
    aicp/capabilities/          Capability definitions
    aicp/policies/              Policy files
    aicp/workflows/             Workflow definitions
    aicp/fixtures/              Test fixtures
"""

from pathlib import Path

import click


@click.command()
@click.option("--app", "app_path", help="FastAPI app module (e.g., app:app)")
@click.option("--openapi", "openapi_path", help="Path to OpenAPI spec")
@click.option("--force", is_flag=True, help="Overwrite existing aicp.yaml")
def init(app_path, openapi_path, force):
    """Initialize a new AICP project.

    Creates an aicp.yaml config file and directory structure for
    capabilities, policies, workflows, and fixtures.

    Examples:
        aicp init
        aicp init --app myapp:app
        aicp init --openapi ./openapi.yaml
    """
    import yaml

    from aicp.config import AicpProjectConfig, find_config_file, save_project_config

    # Check for existing config
    existing = find_config_file()
    if existing and not force:
        click.secho(f"Project already initialized ({existing})", fg="yellow")
        click.echo("Use --force to overwrite.")
        return

    # Build config
    config = AicpProjectConfig()
    if app_path:
        config.app = f"fastapi:{app_path}"
    if openapi_path:
        config.openapi = openapi_path

    # Create directory structure
    dirs = [
        Path(config.capabilities_dir),
        Path(config.policies_dir),
        Path(config.workflows_dir),
        Path(config.fixtures_dir),
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # Write config
    config_path = save_project_config(config)

    # Print summary
    click.secho("✓ Initialized AICP project", fg="green", bold=True)
    click.echo()
    click.echo("  Created:")
    click.echo(f"    {config_path}")
    for d in dirs:
        click.echo(f"    {d}/")
    click.echo()

    # Suggest next steps
    click.echo("  Next steps:")
    if app_path:
        click.echo(f"    1. aicp scan fastapi {app_path.split(':')[-1] if ':' in app_path else app_path}")
    else:
        click.echo("    1. aicp scan fastapi <your_module:app>")
    click.echo("    2. aicp dev")
    click.echo("    3. aicp ls")
