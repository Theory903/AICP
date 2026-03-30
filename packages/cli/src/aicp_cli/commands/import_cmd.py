"""Import capabilities command group."""

import click
from pathlib import Path
from aicp_cli.context import get_runtime_context


@click.group("import")
def import_group():
    """Import capabilities from external specifications."""
    pass


@import_group.command("openapi")
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--base-url", help="Override base URL")
@click.option("--output", "-o", help="Output directory (defaults to aicp/capabilities/raw)")
@click.pass_context
def import_openapi(ctx, spec_file, name, base_url, output):
    """Import capabilities from an OpenAPI specification file."""
    import asyncio
    return asyncio.run(_run_import_openapi(spec_file, name, base_url, output))


async def _run_import_openapi(spec_file, name, base_url, output):
    from aicp_connect_openapi import OpenAPIDiscoverySource
    from aicp.export import export_all_capabilities
    
    runtime = get_runtime_context()
    output_path = output or runtime.project.config.capabilities_dir + "/raw"
    
    click.echo(f"Importing from OpenAPI: {spec_file}...")
    source = OpenAPIDiscoverySource(spec_file, name=name, base_url=base_url)
    capabilities = await source.discover()
    
    if not capabilities:
        click.secho("No capabilities discovered from the spec.", fg="yellow")
        return

    click.echo(f"Discovered {len(capabilities)} capabilities:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    written = export_all_capabilities(capabilities, output_path)
    click.secho(f"\n✓ Successfully exported {len(written)} capabilities to {output_path}/", fg="green", bold=True)


@import_group.command("postman")
@click.argument("collection_file", type=click.Path(exists=True))
@click.option("--name", help="Source name")
@click.option("--output", "-o", help="Output directory")
def import_postman(collection_file, name, output):
    """Import capabilities from a Postman collection JSON."""
    import asyncio
    return asyncio.run(_run_import_postman(collection_file, name, output))


async def _run_import_postman(collection_file, name, output):
    import json as _json
    from aicp_connect_postman import PostmanCollectionImporter
    from aicp.export import export_all_capabilities
    
    runtime = get_runtime_context()
    output_path = output or runtime.project.config.capabilities_dir + "/raw"
    
    with open(collection_file) as f:
        collection = _json.load(f)

    source_name = name or collection.get("info", {}).get("name", "postman")
    source = PostmanCollectionImporter(name=source_name, collection=collection)
    capabilities = await source.discover()

    if not capabilities:
        click.secho("No capabilities discovered from the collection.", fg="yellow")
        return

    click.echo(f"Discovered {len(capabilities)} capabilities from Postman:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    written = export_all_capabilities(capabilities, output_path)
    click.secho(f"\n✓ Successfully exported {len(written)} capabilities to {output_path}/", fg="green", bold=True)
