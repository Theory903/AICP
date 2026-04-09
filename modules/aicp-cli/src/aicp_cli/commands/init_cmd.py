"""aicp init — Scaffold a new AICP project.

Creates:
    aicp.yaml                   Project config
    aicp/capabilities/          Capability definitions
    aicp/policies/              Policy files
    aicp/workflows/             Workflow definitions
    aicp/fixtures/              Test fixtures
"""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
@click.option("--app", "app_path", help="FastAPI app module (e.g., app:app)")
@click.option("--openapi", "openapi_path", help="Path to OpenAPI spec")
@click.option("--force", is_flag=True, help="Overwrite existing aicp.yaml")
def init(app_path: str | None, openapi_path: str | None, force: bool) -> None:
    """Initialize a new AICP project.

    Creates an aicp.yaml config file and directory structure for
    capabilities, policies, workflows, and fixtures.

    Examples:
        aicp init
        aicp init --app myapp:app
        aicp init --openapi ./openapi.yaml
    """
    from aicp.config import find_config_file, save_project_config

    _validate_init_options(app_path=app_path, openapi_path=openapi_path)

    existing = find_config_file()
    if existing and not force:
        raise click.ClickException(
            f"Project already initialized ({existing}). Use --force to overwrite."
        )

    config = _build_config(app_path=app_path, openapi_path=openapi_path)
    created_dirs = _create_project_directories(config)
    config_path = save_project_config(config)

    _print_summary(
        config_path=config_path, created_dirs=created_dirs, app_path=app_path
    )


def _validate_init_options(*, app_path: str | None, openapi_path: str | None) -> None:
    """Validate init command options."""
    if app_path and openapi_path:
        raise click.ClickException(
            "Use either --app or --openapi during initialization, not both."
        )


def _build_config(*, app_path: str | None, openapi_path: str | None):
    """Build initial project config."""
    from aicp.config import AicpProjectConfig

    config = AicpProjectConfig()

    if app_path:
        config.app = (
            app_path if app_path.startswith("fastapi:") else f"fastapi:{app_path}"
        )

    if openapi_path:
        config.openapi = openapi_path

    return config


def _create_project_directories(config) -> list[Path]:
    """Create the initial AICP project directory structure."""
    directories = [
        Path(config.capabilities_dir),
        Path(config.policies_dir),
        Path(config.workflows_dir),
        Path(config.fixtures_dir),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    return directories


def _print_summary(
    *, config_path: Path, created_dirs: list[Path], app_path: str | None
) -> None:
    """Print initialization summary and next steps."""
    click.secho("✓ Initialized AICP project", fg="green", bold=True)
    click.echo()
    click.echo("  Created:")
    click.echo(f"    {config_path}")
    for directory in created_dirs:
        click.echo(f"    {directory}/")
    click.echo()

    click.echo("  Next steps:")
    if app_path:
        click.echo(f"    1. aicp scan fastapi {app_path.removeprefix('fastapi:')}")
    else:
        click.echo("    1. aicp scan fastapi <your_module:app>")
    click.echo("    2. aicp dev")
    click.echo("    3. aicp ls")
