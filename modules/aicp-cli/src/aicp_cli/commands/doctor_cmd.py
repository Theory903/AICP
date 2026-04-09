"""aicp doctor — Validate project configuration.

Checks:
    - aicp.yaml schema validity
    - Existence of referenced capability/policy files
    - Missing descriptions & invalid schemas
    - Dangerous wildcard rules
    - Destructive capabilities lacking protection
    - Import availability (FastAPI, uvicorn, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click


@dataclass(slots=True)
class DoctorReport:
    """Structured doctor report."""

    ok: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def add_ok(self, message: str) -> None:
        self.ok.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_issue(self, message: str) -> None:
        self.issues.append(message)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    @property
    def is_clean(self) -> bool:
        return not self.issues and not self.warnings


@click.command()
@click.option("--fix", is_flag=True, help="Auto-fix simple issues")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def doctor(fix: bool, verbose: bool) -> None:
    """Validate your AICP project configuration."""
    report = DoctorReport()

    try:
        _run_doctor(report, fix=fix, verbose=verbose)
    except Exception as exc:
        raise click.ClickException(f"Doctor failed unexpectedly: {exc}") from exc

    _print_report(report)

    if report.has_issues:
        raise SystemExit(1)


def _run_doctor(report: DoctorReport, *, fix: bool, verbose: bool) -> None:
    """Run all doctor checks."""
    from aicp.config import find_config_file, load_project_config
    from aicp.project_loader import load_project

    config_file = find_config_file()
    if config_file is None:
        report.add_issue("No aicp.yaml found. Run 'aicp init' first.")
        return

    report.add_ok(f"Config file: {config_file}")

    try:
        config = load_project_config(config_file)
        report.add_ok("Config schema: valid")
    except Exception as exc:
        report.add_issue(f"Config parse error: {exc}")
        return

    _check_directories(report, config=config, fix=fix)
    _check_policy_rules(report, config=config, verbose=verbose)
    _check_app_config(report, config=config)
    _check_optional_packages(report, verbose=verbose)

    try:
        project = load_project()
    except Exception as exc:
        report.add_issue(f"Project load failed: {exc}")
        return

    for warning in getattr(project, "warnings", []):
        report.add_warning(warning)

    _check_capabilities(report, config=config, project=project, verbose=verbose)


def _check_directories(report: DoctorReport, *, config: Any, fix: bool) -> None:
    """Check configured project directories."""
    for dir_attr in (
        "capabilities_dir",
        "policies_dir",
        "workflows_dir",
        "fixtures_dir",
    ):
        dir_path = Path(getattr(config, dir_attr))

        if dir_path.exists():
            report.add_ok(f"Directory: {dir_path}/")
        else:
            report.add_warning(
                f"Directory missing: {dir_path}/ — run 'aicp init' to create"
            )
            if fix:
                dir_path.mkdir(parents=True, exist_ok=True)
                report.add_ok(f"  → Created {dir_path}/")

    policies_dir = Path(config.policies_dir)
    if policies_dir.exists():
        policy_files = list(policies_dir.rglob("*.yaml")) + list(
            policies_dir.rglob("*.yml")
        )
        if policy_files:
            report.add_warning(
                f"Orphaned policy files: Found {len(policy_files)} files in {policies_dir}/ not explicitly linked."
            )


def _check_capabilities(
    report: DoctorReport, *, config: Any, project: Any, verbose: bool
) -> None:
    """Validate loaded capability definitions."""
    capabilities = list(getattr(project, "capabilities", []))

    if not capabilities:
        caps_dir = Path(config.capabilities_dir)
        if caps_dir.exists():
            report.add_warning(
                "No capability files found. Run 'aicp scan' to generate them."
            )
        else:
            report.add_warning("Capabilities directory missing")
        return

    report.add_ok(f"Capabilities: {len(capabilities)} loaded")

    for cap in capabilities:
        cap_name = getattr(cap, "name", None) or "<unknown>"
        kind = getattr(cap, "kind", None)

        if not cap_name or cap_name == "<unknown>":
            report.add_issue("Capability missing name")
            continue

        if kind is None:
            report.add_issue(f"Missing 'kind' in capability '{cap_name}'")
            continue

        if not getattr(cap, "description", ""):
            report.add_warning(
                f"Missing description in {cap_name} (agents need this to understand the capability)"
            )

        input_schema = getattr(cap, "input_schema", None)
        output_schema = getattr(cap, "output_schema", None)

        if (
            input_schema
            and hasattr(input_schema, "properties")
            and input_schema.properties == {}
        ):
            report.add_warning(
                f"Empty properties defined in input_schema for {cap_name}"
            )

        if (
            output_schema
            and hasattr(output_schema, "properties")
            and output_schema.properties == {}
        ):
            report.add_warning(
                f"Empty properties defined in output_schema for {cap_name}"
            )

        is_destructive = bool(getattr(cap, "is_destructive", False))
        if is_destructive:
            effect = config.effective_effect(
                capability_name=cap_name,
                kind=kind.value if hasattr(kind, "value") else str(kind),
                is_destructive=True,
            )
            if effect == "allow":
                report.add_issue(
                    f"CRITICAL: Destructive capability '{cap_name}' has effective policy '{effect}'. "
                    "Must be 'ask', 'require_approval', or 'deny'."
                )

        if verbose:
            report.add_ok(f"  ✓ {cap_name} — valid")


def _check_policy_rules(report: DoctorReport, *, config: Any, verbose: bool) -> None:
    """Validate configured policy rules."""
    valid_effects = {"allow", "deny", "ask", "require_approval", "limit"}

    if not config.rules:
        if verbose:
            report.add_warning("No policy rules defined — using defaults only")
        return

    report.add_ok(f"Policy rules: {len(config.rules)} defined")

    for rule in config.rules:
        if rule.effect not in valid_effects:
            report.add_issue(
                f"Invalid effect '{rule.effect}' in rule matching '{rule.match}'"
            )

        if rule.match in {"*", "**", ".*"} and rule.effect == "allow":
            report.add_warning(
                f"Dangerous wildcard rule: '{rule.match}' -> '{rule.effect}'. "
                "Agents have unrestricted access by default."
            )

        if rule.effect == "limit" and not rule.rpm:
            report.add_warning(
                f"Rule '{rule.match}' has effect 'limit' but no 'rpm' set"
            )


def _check_app_config(report: DoctorReport, *, config: Any) -> None:
    """Check configured app entry."""
    if config.app:
        report.add_ok(f"App configured: {config.app}")
    else:
        report.add_warning(
            "No 'app' configured — 'aicp dev' will run standalone runtime"
        )


def _check_optional_packages(report: DoctorReport, *, verbose: bool) -> None:
    """Check availability of optional packages commonly used by CLI/runtime."""
    packages = {
        "fastapi": "FastAPI integration",
        "uvicorn": "runtime server",
        "yaml": "config loading (pyyaml)",
        "click": "CLI framework",
        "rich": "CLI UI components",
    }

    for package_name, purpose in packages.items():
        try:
            __import__(package_name)
            if verbose:
                report.add_ok(f"Package {package_name}: installed ({purpose})")
        except ImportError:
            report.add_warning(
                f"Package '{package_name}' not found — needed for {purpose}"
            )


def _print_report(report: DoctorReport) -> None:
    """Render the doctor report."""
    try:
        from rich.console import Console

        console = Console()
        console.print("[cyan bold]AICP Doctor Report[/]")
        console.print("=" * 40)

        if report.ok:
            console.print("\n[green bold]✓ Passing[/]")
            for item in report.ok:
                console.print(f"  {item}")

        if report.warnings:
            console.print(f"\n[yellow bold]⚠ Warnings ({len(report.warnings)})[/]")
            for item in report.warnings:
                console.print(f"  [yellow]{item}[/]")

        if report.issues:
            console.print(f"\n[red bold]✗ Issues ({len(report.issues)})[/]")
            for item in report.issues:
                console.print(f"  [red]{item}[/]")

        console.print()
        if report.is_clean:
            console.print("[green bold]✓ All checks passed! Golden path achieved.[/]")
        elif report.has_issues:
            console.print(f"[red]Found {len(report.issues)} issue(s) to fix.[/]")
        else:
            console.print(
                f"[yellow]No critical issues. {len(report.warnings)} warning(s) to review.[/]"
            )
    except ImportError:
        click.secho("AICP Doctor Report", fg="cyan", bold=True)
        click.echo("=" * 40)

        if report.ok:
            click.echo()
            click.secho("✓ Passing", fg="green", bold=True)
            for item in report.ok:
                click.echo(f"  {item}")

        if report.warnings:
            click.echo()
            click.secho(f"⚠ Warnings ({len(report.warnings)})", fg="yellow", bold=True)
            for item in report.warnings:
                click.echo(f"  {item}")

        if report.issues:
            click.echo()
            click.secho(f"✗ Issues ({len(report.issues)})", fg="red", bold=True)
            for item in report.issues:
                click.echo(f"  {item}")

        click.echo()
        if report.is_clean:
            click.secho(
                "✓ All checks passed! Golden path achieved.", fg="green", bold=True
            )
        elif report.has_issues:
            click.secho(f"Found {len(report.issues)} issue(s) to fix.", fg="red")
        else:
            click.secho(
                f"No critical issues. {len(report.warnings)} warning(s) to review.",
                fg="yellow",
            )
