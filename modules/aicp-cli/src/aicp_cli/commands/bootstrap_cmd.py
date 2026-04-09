"""aicp bootstrap — One-command project scaffolding and scanning."""

from __future__ import annotations

from dataclasses import dataclass

import click

from aicp_cli.commands.doctor_cmd import doctor
from aicp_cli.commands.init_cmd import init
from aicp_cli.commands.scan_cmd import scan_fastapi


@dataclass(slots=True)
class BootstrapStepResult:
    """Track a bootstrap step result."""

    name: str
    ok: bool
    error: str | None = None


@click.group()
def bootstrap() -> None:
    """Bootstrap a new AICP project in one step.

    Runs init, scan, and doctor in sequence.
    """
    pass


@bootstrap.command("fastapi")
@click.argument("app_spec")
@click.pass_context
def bootstrap_fastapi(ctx: click.Context, app_spec: str) -> None:
    """Bootstrap an AICP project for a FastAPI app.

    APP_SPEC is the import path like 'app:app' or 'mypackage.main:app'

    Example:
        aicp bootstrap fastapi app:app
    """
    console = _get_console()

    _print_banner(console, app_spec)

    results: list[BootstrapStepResult] = []

    results.append(
        _run_step(
            console,
            title="Step 1: Initializing project structure",
            fn=lambda: ctx.invoke(
                init, app_path=app_spec, openapi_path=None, force=True
            ),
            step_name="init",
        )
    )

    results.append(
        _run_step(
            console,
            title="Step 2: Scanning application & exporting YAML",
            fn=lambda: ctx.invoke(
                scan_fastapi, module_app=app_spec, output=None, write=True
            ),
            step_name="scan",
        )
    )

    results.append(
        _run_step(
            console,
            title="Step 3: Running diagnostics & governance checks",
            fn=lambda: ctx.invoke(doctor, fix=False, verbose=False),
            step_name="doctor",
        )
    )

    _print_summary(console, results)


def _run_step(
    console,
    *,
    title: str,
    fn,
    step_name: str,
) -> BootstrapStepResult:
    """Run a bootstrap step and capture success/failure."""
    _print_step_header(console, title)

    try:
        fn()
        click.echo()
        return BootstrapStepResult(name=step_name, ok=True)
    except click.ClickException as exc:
        click.secho(f"Error: {exc.format_message()}", fg="red")
        click.echo()
        return BootstrapStepResult(name=step_name, ok=False, error=exc.format_message())
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            click.echo()
            return BootstrapStepResult(name=step_name, ok=True)

        message = f"{step_name} exited with status {code}"
        click.secho(f"Error: {message}", fg="red")
        click.echo()
        return BootstrapStepResult(name=step_name, ok=False, error=message)
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red")
        click.echo()
        return BootstrapStepResult(name=step_name, ok=False, error=str(exc))


def _get_console():
    """Return a rich console if available, else None."""
    try:
        from rich.console import Console

        return Console()
    except ImportError:
        return None


def _print_banner(console, app_spec: str) -> None:
    """Print bootstrap banner."""
    if console is not None:
        console.print(f"[blue bold]🚀 Bootstrapping AICP for {app_spec}[/]")
    else:
        click.secho(f"🚀 Bootstrapping AICP for {app_spec}", fg="blue", bold=True)
    click.echo()


def _print_step_header(console, title: str) -> None:
    """Print a bootstrap step header."""
    if console is not None:
        console.print(f"[cyan bold]── {title} ──[/]")
    else:
        click.secho(f"── {title} ──", fg="cyan", bold=True)


def _print_summary(console, results: list[BootstrapStepResult]) -> None:
    """Print final bootstrap summary."""
    init_ok = any(r.name == "init" and r.ok for r in results)
    scan_ok = any(r.name == "scan" and r.ok for r in results)
    doctor_ok = any(r.name == "doctor" and r.ok for r in results)
    all_ok = all(r.ok for r in results)

    click.echo()

    if console is not None:
        _print_rich_summary(
            console,
            init_ok=init_ok,
            scan_ok=scan_ok,
            doctor_ok=doctor_ok,
            all_ok=all_ok,
            results=results,
        )
    else:
        _print_plain_summary(
            init_ok=init_ok,
            scan_ok=scan_ok,
            doctor_ok=doctor_ok,
            all_ok=all_ok,
            results=results,
        )


def _print_rich_summary(
    console,
    *,
    init_ok: bool,
    scan_ok: bool,
    doctor_ok: bool,
    all_ok: bool,
    results: list[BootstrapStepResult],
) -> None:
    """Print rich bootstrap summary."""
    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.text import Text

    title = "✨ Bootstrap Complete!" if all_ok else "⚠ Bootstrap Finished with Issues"
    border_style = "green" if all_ok else "yellow"

    text = Text()

    if all_ok:
        text.append("Your project is now AICP-ready.\n\n", style="green bold")
    else:
        text.append(
            "Bootstrap finished, but some steps need attention.\n\n",
            style="yellow bold",
        )

    text.append("Step Results:\n", style="bold")
    for result in results:
        icon = "✓" if result.ok else "✗"
        style = "green" if result.ok else "red"
        text.append(f"{icon} {result.name}\n", style=style)

    text.append("\nNext Steps:\n", style="bold")

    if init_ok:
        if scan_ok:
            text.append("1. Run ", style="dim")
            text.append("aicp dev", style="cyan bold")
            text.append(" to start the runtime\n", style="dim")

            text.append("2. Run ", style="dim")
            text.append("aicp preview <capability>", style="cyan bold")
            text.append(" to inspect the generated surface\n", style="dim")

            text.append("3. Tweak policies with ", style="dim")
            text.append("aicp protect <capability>", style="cyan bold")
        else:
            text.append("1. Fix the scan error and rerun ", style="dim")
            text.append("aicp scan fastapi <module:app>", style="cyan bold")
            text.append("\n", style="dim")

            text.append("2. Run ", style="dim")
            text.append("aicp doctor", style="cyan bold")
            text.append(" to re-check the project\n", style="dim")

            text.append("3. Then start the runtime with ", style="dim")
            text.append("aicp dev", style="cyan bold")
    else:
        text.append("1. Fix initialization issues and rerun ", style="dim")
        text.append("aicp bootstrap fastapi <module:app>", style="cyan bold")

    console.print(Panel(text, title=title, border_style=border_style, box=ROUNDED))


def _print_plain_summary(
    *,
    init_ok: bool,
    scan_ok: bool,
    doctor_ok: bool,
    all_ok: bool,
    results: list[BootstrapStepResult],
) -> None:
    """Print plain-text bootstrap summary."""
    if all_ok:
        click.secho(
            "✨ Bootstrap complete! Your project is AICP-ready.", fg="green", bold=True
        )
    else:
        click.secho("⚠ Bootstrap finished with issues.", fg="yellow", bold=True)

    click.echo("Step results:")
    for result in results:
        prefix = "✓" if result.ok else "✗"
        color = "green" if result.ok else "red"
        suffix = f" — {result.error}" if result.error else ""
        click.secho(f"  {prefix} {result.name}{suffix}", fg=color)

    if init_ok and scan_ok and doctor_ok:
        click.echo("  1. Run 'aicp dev' to start the runtime")
        click.echo("  2. Run 'aicp preview <capability>' to inspect surface")
        click.echo("  3. Run 'aicp protect <capability>' to tweak policies")
    elif init_ok and not scan_ok:
        click.echo("  1. Fix the scan issue and rerun 'aicp scan fastapi <module:app>'")
        click.echo("  2. Run 'aicp doctor' to validate the setup")
        click.echo("  3. Then run 'aicp dev'")
    elif not init_ok:
        click.echo("  1. Fix initialization issues")
        click.echo("  2. Rerun 'aicp bootstrap fastapi <module:app>'")
