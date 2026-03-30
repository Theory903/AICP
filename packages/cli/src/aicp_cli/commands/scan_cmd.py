"""aicp scan — Auto-detect capabilities from your application.

Supports:
    aicp scan fastapi <module:app>    Inspect live FastAPI app
    aicp scan openapi <file>          Parse OpenAPI spec
    aicp scan postman <file>          Parse Postman collection
    aicp scan har <file>              Parse HAR file
    aicp scan curl '<command>'        Parse cURL command

Writes discovered capabilities to aicp/capabilities/*.yaml
"""

from pathlib import Path

import click


@click.group()
def scan():
    """Auto-detect capabilities from your application.

    Scans your API surface and generates AICP capability
    definitions in aicp/capabilities/.

    Examples:
        aicp scan fastapi app:app
        aicp scan openapi ./openapi.yaml
    """
    pass


@scan.command("fastapi")
@click.argument("module_app")
@click.option("--output", "-o", default=None, help="Output directory (default: from aicp.yaml)")
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_fastapi(module_app, output, write):
    """Scan a FastAPI application for capabilities.

    MODULE_APP is the import path like 'app:app' or 'mypackage.main:app'

    Examples:
        aicp scan fastapi app:app
        aicp scan fastapi server:app --output ./custom/
    """
    import asyncio

    asyncio.run(_scan_fastapi(module_app, output, write))


async def _scan_fastapi(module_app, output, write):
    """Inspect FastAPI routes and generate capabilities."""
    import importlib
    import sys

    import yaml

    from aicp.config import load_project_config
    from aicp.export import export_all_capabilities
    from aicp.risk import infer_risk, risk_to_default_effect

    # Parse module:app format
    if ":" in module_app:
        module_name, app_name = module_app.rsplit(":", 1)
    else:
        module_name = module_app
        app_name = "app"

    # Add cwd to path for local imports
    if "." not in sys.path:
        sys.path.insert(0, ".")

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        click.secho(f"Error: Cannot import module '{module_name}': {e}", fg="red")
        click.echo("Make sure you're in the project root directory.")
        return

    app = getattr(module, app_name, None)
    if app is None:
        click.secho(f"Error: No attribute '{app_name}' in module '{module_name}'", fg="red")
        return

    # Use FastAPI adapter to inspect routes
    try:
        from aicp_connect_fastapi.inspect import inspect_routes
        from aicp_connect_fastapi.mapper import map_routes_to_capabilities
    except ImportError:
        click.secho("Error: aicp-connect-fastapi not installed", fg="red")
        return


    click.echo(f"Scanning {module_name}:{app_name}...")
    click.echo()

    # Enrich with risk inference
    config = load_project_config()

    # Inspect and map
    try:
        from aicp_connect_fastapi.types import AicpConfig
    except ImportError:
        click.secho("Error: aicp-connect-fastapi not installed", fg="red")
        return

    routes = inspect_routes(app)
    fastapi_config = AicpConfig(provider_name=config.provider_name)
    capabilities = map_routes_to_capabilities(app, fastapi_config)

    if not capabilities:
        click.secho("No capabilities detected.", fg="yellow")
        return

    # Display results
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"Detected {len(capabilities)} Capabilities", show_lines=False)
        table.add_column("#", style="dim", width=3)
        table.add_column("Capability", style="cyan bold")
        table.add_column("Kind", style="green")
        table.add_column("Risk", style="yellow")
        table.add_column("Default Policy")
        table.add_column("Source Route", style="dim")

        for i, cap in enumerate(capabilities, 1):
            risk = infer_risk(cap.name, cap.kind)
            effect = config.effective_effect(cap.name, cap.kind.value, False)

            risk_style = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}.get(risk.value, "white")
            effect_style = {"allow": "green", "ask": "yellow", "require_approval": "red", "deny": "bold red"}.get(effect, "white")

            # Find original route path
            route_path = ""
            for r in routes:
                if r.get("capability_name") == cap.name or cap.name.endswith(r.get("function_name", "")):
                    route_path = f"{r.get('method', '?')} {r.get('path', '?')}"
                    break

            table.add_row(
                str(i),
                cap.name,
                cap.kind.value,
                f"[{risk_style}]{risk.value}[/{risk_style}]",
                f"[{effect_style}]{effect}[/{effect_style}]",
                route_path,
            )

        console.print(table)
    except ImportError:
        click.echo(f"Detected {len(capabilities)} capabilities:")
        for cap in capabilities:
            risk = infer_risk(cap.name, cap.kind)
            click.echo(f"  • {cap.name} ({cap.kind.value}) — risk: {risk.value}")

    # Write capability files
    if write:
        output_dir = Path(output) if output else Path(config.capabilities_dir)
        written = export_all_capabilities(capabilities, output_dir)
        click.echo()
        click.secho(f"✓ Written {len(written)} capability files to {output_dir}/", fg="green")
        click.echo()
        click.echo("  Next steps:")
        click.echo("    1. Review generated files in aicp/capabilities/")
        click.echo("    2. Customize risk levels and descriptions")
        click.echo("    3. aicp dev — start the runtime")


@scan.command("openapi")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--base-url", help="Override base URL")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_openapi(file, name, base_url, output, write):
    """Scan an OpenAPI specification for capabilities.

    Example: aicp scan openapi ./openapi.yaml
    """
    import asyncio

    asyncio.run(_scan_openapi(file, name, base_url, output, write))


async def _scan_openapi(file, name, base_url, output, write):
    from aicp.config import load_project_config
    from aicp.export import export_all_capabilities
    from aicp.risk import infer_risk

    try:
        from aicp_connect_openapi import OpenAPIDiscoverySource
    except ImportError:
        click.secho("Error: aicp-connect-openapi not installed", fg="red")
        return

    source = OpenAPIDiscoverySource(file, name=name, base_url=base_url)
    capabilities = await source.discover()

    click.echo(f"Discovered {len(capabilities)} capabilities from OpenAPI spec:")
    for cap in capabilities:
        risk = infer_risk(cap.name, cap.kind)
        click.echo(f"  • {cap.name} ({cap.kind.value}) — risk: {risk.value}")

    if write:
        config = load_project_config()
        output_dir = Path(output) if output else Path(config.capabilities_dir)
        written = export_all_capabilities(capabilities, output_dir)
        click.echo(f"\n✓ Written {len(written)} capability files to {output_dir}/")


@scan.command("postman")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_postman(file, name, output, write):
    """Scan a Postman collection for capabilities."""
    import asyncio

    asyncio.run(_scan_postman(file, name, output, write))


async def _scan_postman(file, name, output, write):
    from aicp.config import load_project_config
    from aicp.export import export_all_capabilities

    try:
        from aicp_connect_postman import PostmanDiscoverySource
    except ImportError:
        click.secho("Error: aicp-connect-postman not installed", fg="red")
        return

    source = PostmanDiscoverySource(file, name=name)
    capabilities = await source.discover()

    click.echo(f"Discovered {len(capabilities)} capabilities from Postman collection:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    if write:
        config = load_project_config()
        output_dir = Path(output) if output else Path(config.capabilities_dir)
        written = export_all_capabilities(capabilities, output_dir)
        click.echo(f"\n✓ Written {len(written)} capability files to {output_dir}/")
