"""AICP Map commands - scan, inspect, graph backend capabilities."""

from __future__ import annotations

import json
from pathlib import Path

import click

from aicp_cli.map import MapScanner


@click.group(name="map")
def map_group():
    """Map backend to discoverable capabilities and workflows."""
    pass


@map_group.command(name="scan")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--deep", is_flag=True, help="Deep scan with AI-assisted inference")
@click.option("--output", "-o", type=click.Choice(["json", "text"]), default="text")
def scan(path: str, deep: bool, output: str):
    """Scan a backend and infer capabilities."""
    scanner = MapScanner()
    result = scanner.scan(path, deep=deep)

    if output == "json":
        envelope = scanner.to_envelope(result)
        click.echo(json.dumps(envelope, indent=2))
    else:
        _print_scan_summary(result)


@map_group.command(name="capabilities")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--family", "-f", help="Filter by family (users, orders, payments, etc)")
@click.option("--risk", "-r", type=click.Choice(["low", "medium", "high"]), help="Filter by risk level")
def capabilities(path: str, family: str | None, risk: str | None):
    """List inferred capability candidates."""
    scanner = MapScanner()
    result = scanner.scan(path)

    caps = result.capability_candidates
    if family:
        caps = [c for c in caps if c.get("family") == family]
    if risk:
        caps = [c for c in caps if c.get("risk") == risk]

    if not caps:
        click.echo("No capabilities found.")
        return

    for cap in caps:
        risk_badge = _risk_badge(cap.get("risk", "low"))
        click.echo(f"{risk_badge} {cap['name']}")
        click.echo(f"   {cap.get('description', '')}")
        click.echo(f"   family={cap.get('family')} kind={cap.get('kind')} side_effect={cap.get('side_effect')}")
        if cap.get("approval_required"):
            click.echo(f"   ⚠️  requires approval")
        click.echo()


@map_group.command(name="workflows")
@click.argument("path", default=".", type=click.Path(exists=True))
def workflows(path: str):
    """List inferred workflow candidates."""
    scanner = MapScanner()
    result = scanner.scan(path)

    if not result.workflow_candidates:
        click.echo("No workflow candidates inferred.")
        return

    for wf in result.workflow_candidates:
        click.echo(f"Workflow: {wf['name']}")
        click.echo(f"  Steps: {' → '.join(wf['steps'])}")
        click.echo(f"  Inferred: {wf.get('inferred', False)}")
        click.echo()


@map_group.command(name="graph")
@click.argument("path", default=".", type=click.Path(exists=True))
def graph(path: str):
    """Show action graph."""
    scanner = MapScanner()
    result = scanner.scan(path)

    click.echo("# Action Graph")
    click.echo()

    # Group by family
    families = {}
    for cap in result.capability_candidates:
        fam = cap.get("family", "unknown")
        if fam not in families:
            families[fam] = []
        families[fam].append(cap)

    for fam, caps in families.items():
        click.echo(f"## {fam.upper()}")
        for cap in caps:
            click.echo(f"  {cap['name']}")
        click.echo()

    # Show workflows
    if result.workflow_candidates:
        click.echo("## Workflows")
        for wf in result.workflow_candidates:
            click.echo(f"  {' → '.join(wf['steps'])}")
        click.echo()


@map_group.command(name="risks")
@click.argument("path", default=".", type=click.Path(exists=True))
def risks(path: str):
    """Show risk summary."""
    scanner = MapScanner()
    result = scanner.scan(path)

    click.echo("# Risk Summary")
    click.echo()
    for level, count in result.risk_summary.items():
        badge = _risk_badge(level)
        click.echo(f"{badge} {level.upper()}: {count}")
    click.echo()

    # Show high-risk capabilities
    high_risk = [c for c in result.capability_candidates if c.get("risk") == "high"]
    if high_risk:
        click.echo("## High-Risk Capabilities")
        for cap in high_risk:
            click.echo(f"  - {cap['name']}: {cap.get('description', '')}")


def _print_scan_summary(result) -> None:
    """Print human-readable scan summary."""
    click.echo(f"# Map Scan Results")
    click.echo()
    click.echo(f"Framework: {result.backend_framework or 'unknown'} (confidence: {result.backend_confidence})")
    click.echo(f"Scan time: {result.scan_time_ms}ms")
    click.echo()

    click.echo("## Extracted")
    click.echo(f"  Routes: {len(result.routes)}")
    click.echo(f"  Entities: {len(result.entities)}")
    click.echo(f"  Services: {len(result.services)}")
    click.echo()

    click.echo("## Inferred")
    click.echo(f"  Capabilities: {len(result.capability_candidates)}")
    click.echo(f"  Workflows: {len(result.workflow_candidates)}")
    click.echo()

    click.echo("## Risk Summary")
    for level, count in result.risk_summary.items():
        click.echo(f"  {level}: {count}")

    click.echo()
    click.echo("## Family Summary")
    for family, count in result.family_summary.items():
        click.echo(f"  {family}: {count}")


def _risk_badge(risk: str) -> str:
    """Get risk badge."""
    badges = {
        "low": "✓",
        "medium": "⚠",
        "high": "✗",
    }
    return badges.get(risk, "?")