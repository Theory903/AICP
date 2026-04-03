"""aicp scan — Auto-detect capabilities from your application.

Supports:
    aicp scan fastapi <module:app>    Inspect live FastAPI app
    aicp scan openapi <file>          Parse OpenAPI spec
    aicp scan postman <file>          Parse Postman collection
    aicp scan har <file>              Parse HAR file
    aicp scan curl '<command>'        Parse cURL command

Writes discovered capabilities to aicp/capabilities/*.yaml
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import click


@click.group()
def scan() -> None:
    """Auto-detect capabilities from your application."""
    ...


@scan.command("fastapi")
@click.argument("module_app")
@click.option(
    "--output", "-o", default=None, help="Output directory (default: from aicp.yaml)"
)
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_fastapi(module_app: str, output: str | None, write: bool) -> None:
    """Scan a FastAPI application for capabilities."""
    asyncio.run(_scan_fastapi(module_app, output, write))


@scan.command("openapi")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", help="Source name")
@click.option("--base-url", help="Override base URL")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_openapi(
    file: Path,
    name: str | None,
    base_url: str | None,
    output: str | None,
    write: bool,
) -> None:
    """Scan an OpenAPI specification for capabilities."""
    asyncio.run(_scan_openapi(file, name, base_url, output, write))


@scan.command("postman")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", help="Source name")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--write/--no-write", default=True, help="Write capability YAML files")
def scan_postman(
    file: Path,
    name: str | None,
    output: str | None,
    write: bool,
) -> None:
    """Scan a Postman collection for capabilities."""
    asyncio.run(_scan_postman(file, name, output, write))


def _load_config():
    from aicp.config import load_project_config

    return load_project_config()


def _resolve_output_dir(output: str | None, config: Any | None = None) -> Path:
    active_config = config if config is not None else _load_config()
    return Path(output) if output else Path(active_config.capabilities_dir)


def _write_capabilities(
    capabilities: list[Any], output: str | None, config: Any | None = None
) -> None:
    from aicp.export import CapabilityExportError, export_all_capabilities

    output_dir = _resolve_output_dir(output, config)
    try:
        written = export_all_capabilities(capabilities, output_dir)
    except CapabilityExportError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo()
    click.secho(
        f"✓ Written {len(written)} capability files to {output_dir}/", fg="green"
    )


def _render_capabilities_table(
    capabilities: list[Any],
    *,
    title: str,
    effects_enabled: bool = True,
    config: Any | None = None,
) -> None:
    from aicp.risk import infer_risk

    active_config = config if config is not None else _load_config()

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=title, show_lines=False)
        table.add_column("#", style="dim", width=3)
        table.add_column("Capability", style="cyan bold")
        table.add_column("Kind", style="green")
        table.add_column("Risk", style="yellow")
        if effects_enabled:
            table.add_column("Default Policy")

        for index, cap in enumerate(capabilities, 1):
            risk = infer_risk(cap.name, cap.kind)
            risk_style = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
                "critical": "bold red",
            }.get(risk.value, "white")

            row = [
                str(index),
                cap.name,
                cap.kind.value,
                f"[{risk_style}]{risk.value}[/{risk_style}]",
            ]

            if effects_enabled:
                effect = active_config.effective_effect(
                    capability_name=cap.name,
                    kind=cap.kind.value,
                    is_destructive=getattr(cap, "is_destructive", False),
                )
                effect_style = {
                    "allow": "green",
                    "ask": "yellow",
                    "require_approval": "red",
                    "deny": "bold red",
                    "limit": "magenta",
                }.get(effect, "white")
                row.append(f"[{effect_style}]{effect}[/{effect_style}]")

            table.add_row(*row)

        console.print(table)

    except ImportError:
        click.echo(title)
        for cap in capabilities:
            risk = infer_risk(cap.name, cap.kind)
            line = f"  • {cap.name} ({cap.kind.value}) — risk: {risk.value}"
            if effects_enabled:
                effect = active_config.effective_effect(
                    capability_name=cap.name,
                    kind=cap.kind.value,
                    is_destructive=getattr(cap, "is_destructive", False),
                )
                line += f" — policy: {effect}"
            click.echo(line)


def _show_next_steps() -> None:
    click.echo()
    click.echo("  Next steps:")
    click.echo("    1. Review generated files in aicp/capabilities/")
    click.echo("    2. Customize risk levels and descriptions")
    click.echo("    3. aicp dev — start the runtime")


def _parse_module_app(module_app: str) -> tuple[str, str]:
    if ":" in module_app:
        module_name, app_name = module_app.rsplit(":", 1)
        return module_name, app_name
    return module_app, "app"


def _import_module(module_name: str):
    if "." not in sys.path:
        sys.path.insert(0, ".")

    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        raise click.ClickException(
            f"Cannot import module '{module_name}': {exc}\n"
            "Make sure you're in the project root directory and the app imports cleanly."
        ) from exc


def _handle_scan_results(
    capabilities: list[Any],
    *,
    title: str,
    output: str | None,
    write: bool,
    show_next_steps: bool = False,
    config: Any | None = None,
) -> None:
    if not capabilities:
        click.secho("No capabilities detected.", fg="yellow")
        return

    _render_capabilities_table(
        capabilities,
        title=title,
        effects_enabled=True,
        config=config,
    )

    if write:
        _write_capabilities(capabilities, output, config)
        if show_next_steps:
            _show_next_steps()


async def _scan_fastapi(module_app: str, output: str | None, write: bool) -> None:
    """Inspect FastAPI routes and generate capabilities."""
    module_name, app_name = _parse_module_app(module_app)
    module = _import_module(module_name)
    app = getattr(module, app_name, None)

    if app is None:
        raise click.ClickException(
            f"No attribute '{app_name}' in module '{module_name}'"
        )

    config = _load_config()
    click.echo(f"Scanning {module_name}:{app_name}...")
    click.echo()

    provider_url = getattr(config, "provider_url", None)
    if not provider_url:
        runtime = getattr(config, "runtime", None)
        if runtime is not None:
            provider_url = f"http://{runtime.host}:{runtime.port}"

    try:
        capabilities = await _discover_fastapi_capabilities(
            app,
            provider_name=config.provider_name,
            base_url=provider_url,
        )
    except Exception as exc:
        raise click.ClickException(f"Failed to inspect FastAPI app: {exc}") from exc

    _handle_scan_results(
        capabilities,
        title=f"Detected {len(capabilities)} Capabilities",
        output=output,
        write=write,
        show_next_steps=True,
        config=config,
    )


async def _discover_fastapi_capabilities(
    app: Any,
    *,
    provider_name: str,
    base_url: str | None = None,
) -> list[Any]:
    """Discover FastAPI capabilities, preferring the app's OpenAPI schema."""
    openapi_callable = getattr(app, "openapi", None)
    if callable(openapi_callable):
        try:
            from aicp_connect_openapi import OpenAPIDiscoverySource

            spec = openapi_callable()
            if isinstance(spec, dict):
                source = OpenAPIDiscoverySource(
                    name=provider_name,
                    spec=spec,
                    base_url=base_url,
                )
                return await source.discover()
        except ImportError:
            pass

    try:
        from aicp_connect_fastapi.mapper import map_routes_to_capabilities
        from aicp_connect_fastapi.types import AicpConfig
    except ImportError as exc:
        raise click.ClickException("aicp-connect-fastapi is not installed") from exc

    fastapi_config = AicpConfig(provider_name=provider_name)
    return map_routes_to_capabilities(app, fastapi_config)


async def _scan_openapi(
    file: Path,
    name: str | None,
    base_url: str | None,
    output: str | None,
    write: bool,
) -> None:
    try:
        from aicp_connect_openapi import OpenAPIDiscoverySource
    except ImportError as exc:
        raise click.ClickException("aicp-connect-openapi is not installed") from exc

    try:
        if file.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise click.ClickException(
                    "PyYAML is required to read YAML OpenAPI specs"
                ) from exc

            with file.open("r", encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        else:
            with file.open("r", encoding="utf-8") as f:
                spec = json.load(f)
    except Exception as exc:
        raise click.ClickException(f"Failed to read OpenAPI spec: {exc}") from exc

    if not isinstance(spec, dict):
        raise click.ClickException("OpenAPI spec root must be an object")

    source_name = name or file.stem

    try:
        source = OpenAPIDiscoverySource(
            name=source_name,
            spec=spec,
            spec_url=str(file),
            base_url=base_url,
        )
        capabilities = await source.discover()
    except Exception as exc:
        raise click.ClickException(f"Failed to scan OpenAPI spec: {exc}") from exc

    warnings = getattr(source, "warnings", []) or []
    for warning in warnings:
        click.secho(f"Warning: {warning}", fg="yellow")

    _handle_scan_results(
        capabilities,
        title=f"Discovered {len(capabilities)} capabilities from OpenAPI spec",
        output=output,
        write=write,
        config=_load_config(),
    )


async def _scan_postman(
    file: Path,
    name: str | None,
    output: str | None,
    write: bool,
) -> None:
    try:
        from aicp_connect_postman import PostmanCollectionImporter
    except ImportError as exc:
        raise click.ClickException("aicp-connect-postman is not installed") from exc

    try:
        with file.open("r", encoding="utf-8") as f:
            collection = json.load(f)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid Postman collection JSON: {exc}") from exc
    except OSError as exc:
        raise click.ClickException(f"Failed to read Postman collection: {exc}") from exc

    if not isinstance(collection, dict):
        raise click.ClickException("Postman collection root must be an object")

    source_name = name or collection.get("info", {}).get("name") or file.stem

    try:
        source = PostmanCollectionImporter(name=source_name, collection=collection)
        capabilities = await source.discover()
    except Exception as exc:
        raise click.ClickException(f"Failed to scan Postman collection: {exc}") from exc

    _handle_scan_results(
        capabilities,
        title=f"Discovered {len(capabilities)} capabilities from Postman collection",
        output=output,
        write=write,
        config=_load_config(),
    )
