"""Import capabilities command group."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from aicp_cli.context import get_runtime_context


@click.group("import")
def import_group() -> None:
    """Import capabilities from external specifications."""
    pass


@import_group.command("openapi")
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", help="Source name")
@click.option("--base-url", help="Override base URL")
@click.option(
    "--output", "-o", help="Output directory (defaults to aicp/capabilities/raw)"
)
def import_openapi(
    spec_file: Path,
    name: str | None,
    base_url: str | None,
    output: str | None,
) -> None:
    """Import capabilities from an OpenAPI specification file."""
    exit_code = asyncio.run(_run_import_openapi(spec_file, name, base_url, output))
    raise SystemExit(exit_code)


@import_group.command("postman")
@click.argument("collection_file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", help="Source name")
@click.option(
    "--output", "-o", help="Output directory (defaults to aicp/capabilities/raw)"
)
def import_postman(
    collection_file: Path,
    name: str | None,
    output: str | None,
) -> None:
    """Import capabilities from a Postman collection JSON."""
    exit_code = asyncio.run(_run_import_postman(collection_file, name, output))
    raise SystemExit(exit_code)


async def _run_import_openapi(
    spec_file: Path,
    name: str | None,
    base_url: str | None,
    output: str | None,
) -> int:
    """Import and export capabilities from an OpenAPI spec."""
    try:
        from aicp_connect_openapi import OpenAPIDiscoverySource
    except ImportError as exc:
        raise click.ClickException("aicp-connect-openapi is not installed") from exc

    try:
        spec = _load_openapi_spec(spec_file)
        source = OpenAPIDiscoverySource(
            name=name or spec_file.stem,
            spec=spec,
            spec_url=str(spec_file),
            base_url=base_url,
        )
        capabilities = await source.discover()
    except Exception as exc:
        raise click.ClickException(f"Failed to import OpenAPI spec: {exc}") from exc

    return _finalize_import(
        capabilities=capabilities,
        output=output,
        source_label=f"OpenAPI: {spec_file}",
    )


async def _run_import_postman(
    collection_file: Path,
    name: str | None,
    output: str | None,
) -> int:
    """Import and export capabilities from a Postman collection."""
    try:
        from aicp_connect_postman import PostmanCollectionImporter
    except ImportError as exc:
        raise click.ClickException("aicp-connect-postman is not installed") from exc

    try:
        with collection_file.open("r", encoding="utf-8") as f:
            collection = json.load(f)
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"Invalid JSON in Postman collection: {exc}"
        ) from exc
    except OSError as exc:
        raise click.ClickException(f"Failed to read Postman collection: {exc}") from exc

    source_name = name or collection.get("info", {}).get("name", "postman")

    try:
        source = PostmanCollectionImporter(name=source_name, collection=collection)
        capabilities = await source.discover()
    except Exception as exc:
        raise click.ClickException(
            f"Failed to import Postman collection: {exc}"
        ) from exc

    return _finalize_import(
        capabilities=capabilities,
        output=output,
        source_label=f"Postman: {collection_file}",
    )


def _finalize_import(
    *,
    capabilities: list[Any],
    output: str | None,
    source_label: str,
) -> int:
    """Print import summary and export discovered capabilities."""
    from aicp.export import export_all_capabilities

    click.echo(f"Importing from {source_label}...")

    if not capabilities:
        click.secho("No capabilities discovered.", fg="yellow")
        return 0

    click.echo(f"Discovered {len(capabilities)} capabilities:")
    for cap in capabilities:
        click.echo(f"  • {cap.name} ({cap.kind.value})")

    output_path = _resolve_output_path(output)

    try:
        written = export_all_capabilities(capabilities, output_path)
    except Exception as exc:
        raise click.ClickException(f"Failed to export capabilities: {exc}") from exc

    click.secho(
        f"\n✓ Successfully exported {len(written)} capabilities to {output_path}/",
        fg="green",
        bold=True,
    )
    return 0


def _resolve_output_path(output: str | None) -> Path:
    """Resolve output path, defaulting to the project's raw capability directory."""
    if output:
        return Path(output)

    try:
        runtime = get_runtime_context()
        return Path(runtime.project.config.capabilities_dir) / "raw"
    except Exception:
        # Fallback for import use outside a fully initialized project.
        return Path("aicp/capabilities/raw")


def _load_openapi_spec(spec_file: Path) -> dict[str, Any]:
    """Load an OpenAPI file from JSON or YAML."""
    try:
        with spec_file.open("r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        raise click.ClickException(f"Failed to read OpenAPI spec: {exc}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    try:
        import yaml
    except ImportError as exc:
        raise click.ClickException(
            "PyYAML is required to import YAML OpenAPI specs"
        ) from exc

    try:
        loaded = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Invalid YAML in OpenAPI spec: {exc}") from exc

    if not isinstance(loaded, dict):
        raise click.ClickException("OpenAPI spec must parse to a JSON/YAML object")

    return loaded
