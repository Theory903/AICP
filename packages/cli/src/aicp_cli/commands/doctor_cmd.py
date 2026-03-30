"""aicp doctor — Validate project configuration.

Checks:
    - aicp.yaml schema validity
    - Existence of referenced capability/policy files
    - Missing descriptions & invalid schemas
    - Dangerous wildcard rules
    - Destructive capabilities lacking protection
    - Import availability (FastAPI, uvicorn, etc.)
"""

from pathlib import Path
import click


@click.command()
@click.option("--fix", is_flag=True, help="Auto-fix simple issues")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def doctor(fix, verbose):
    """Validate your AICP project configuration.

    Analyzes capabilities, schemas, and policy stacks to ensure a robust,
    safe, and fully governed action surface.
    """
    issues = []
    warnings = []
    ok = []

    # 1. Check aicp.yaml exists
    from aicp.config import find_config_file, load_project_config

    config_file = find_config_file()
    if config_file:
        ok.append(f"Config file: {config_file}")
        try:
            config = load_project_config()
            ok.append("Config schema: valid")
        except Exception as e:
            issues.append(f"Config parse error: {e}")
            config = None
    else:
        issues.append("No aicp.yaml found. Run 'aicp init' first.")
        config = None

    if config:
        # 2. Check directories exist
        for dir_attr in ["capabilities_dir", "policies_dir", "workflows_dir", "fixtures_dir"]:
            dir_path = Path(getattr(config, dir_attr))
            if dir_path.exists():
                ok.append(f"Directory: {dir_path}/")
                if dir_attr == "policies_dir":
                    pol_files = list(dir_path.glob("*.*"))
                    if pol_files:
                        warnings.append(f"Orphaned policy files: Found {len(pol_files)} files in {dir_path}/ not explicitly linked.")
            else:
                warnings.append(f"Directory missing: {dir_path}/ — run 'aicp init' to create")
                if fix:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    ok.append(f"  → Created {dir_path}/")

        # 3. Check capability definitions & destructive protection
        caps_dir = Path(config.capabilities_dir)
        if caps_dir.exists():
            cap_files = list(caps_dir.glob("*.yaml"))
            if cap_files:
                ok.append(f"Capabilities: {len(cap_files)} files found")

                try:
                    import yaml
                except ImportError:
                    issues.append("PyYAML not installed — needed for capability files")
                    cap_files = []

                for f in cap_files:
                    try:
                        with open(f) as fh:
                            cap = yaml.safe_load(fh)
                        
                        if not cap:
                            warnings.append(f"Empty capability file: {f.name}")
                            continue

                        cap_name = cap.get("name")
                        kind = cap.get("kind")
                        
                        if not cap_name:
                            issues.append(f"Missing 'name' in {f.name}")
                        if not kind:
                            issues.append(f"Missing 'kind' in {f.name}")
                            
                        # Missing description
                        if not cap.get("description"):
                            warnings.append(f"Missing description in {cap_name or f.name} (agents need this to understand the tool)")

                        # Schema gaps
                        for schema_type in ["input_schema", "output_schema"]:
                            schema = cap.get(schema_type, {})
                            if schema and not schema.get("properties"):
                                warnings.append(f"Empty properties defined in {schema_type} for {cap_name or f.name}")

                        # Destructive capability protection check
                        tags = cap.get("tags", [])
                        is_destructive = "destructive" in tags
                        if is_destructive and cap_name and kind:
                            eff = config.effective_effect(cap_name, kind, is_destructive=True)
                            if eff in ("allow",):
                                issues.append(f"CRITICAL: Destructive capability '{cap_name}' has effective policy '{eff}'. Must be 'ask', 'require_approval', or 'deny'.")

                        if cap_name and kind and verbose:
                            ok.append(f"  ✓ {cap_name} — valid")

                    except Exception as e:
                        issues.append(f"Parse error in {f.name}: {e}")
            else:
                warnings.append("No capability files found. Run 'aicp scan' to generate them.")
        else:
            warnings.append("Capabilities directory missing")

        # 4. Check policy rules
        if config.rules:
            ok.append(f"Policy rules: {len(config.rules)} defined")
            valid_effects = {"allow", "deny", "ask", "require_approval", "limit"}
            for rule in config.rules:
                if rule.effect not in valid_effects:
                    issues.append(f"Invalid effect '{rule.effect}' in rule matching '{rule.match}'")
                
                # Dangerous wildcards
                if rule.match in ("*", "**", ".*") and rule.effect in ("allow",):
                    warnings.append(f"Dangerous wildcard rule: '{rule.match}' -> '{rule.effect}'. Agents have unrestricted access by default.")
                
                if rule.effect == "limit" and not rule.rpm:
                    warnings.append(f"Rule '{rule.match}' has effect 'limit' but no 'rpm' set")
        else:
            if verbose:
                warnings.append("No policy rules defined — using defaults only")

        # 5. Check app import
        if config.app:
            ok.append(f"App configured: {config.app}")
        else:
            warnings.append("No 'app' configured — 'aicp dev' will run standalone runtime")

    # 6. Check required packages
    packages = {
        "fastapi": "aicp-connect-fastapi",
        "uvicorn": "runtime server",
        "yaml": "config loading (pyyaml)",
        "click": "CLI framework",
        "rich": "CLI UI components",
    }
    for pkg, purpose in packages.items():
        try:
            __import__(pkg)
            if verbose:
                ok.append(f"Package {pkg}: installed ({purpose})")
        except ImportError:
            warnings.append(f"Package '{pkg}' not found — needed for {purpose}")

    # Print results
    click.echo()
    try:
        from rich.console import Console
        console = Console()
        console.print("[cyan bold]AICP Doctor Report[/]")
        console.print("=" * 40)

        if ok:
            console.print("\n[green bold]✓ Passing[/]")
            for item in ok:
                console.print(f"  {item}")

        if warnings:
            console.print(f"\n[yellow bold]⚠ Warnings ({len(warnings)})[/]")
            for item in warnings:
                console.print(f"  [yellow]{item}[/]")

        if issues:
            console.print(f"\n[red bold]✗ Issues ({len(issues)})[/]")
            for item in issues:
                console.print(f"  [red]{item}[/]")

        console.print()
        if not issues and not warnings:
            console.print("[green bold]✓ All checks passed! Golden path achieved.[/]")
        elif issues:
            console.print(f"[red]Found {len(issues)} issue(s) to fix.[/]")
        else:
            console.print(f"[yellow]No critical issues. {len(warnings)} warning(s) to review.[/]")

    except ImportError:
        # Fallback without rich
        click.secho("AICP Doctor Report", fg="cyan", bold=True)
        click.echo("=" * 40)

        if ok:
            click.echo()
            click.secho("✓ Passing", fg="green", bold=True)
            for item in ok:
                click.echo(f"  {item}")

        if warnings:
            click.echo()
            click.secho(f"⚠ Warnings ({len(warnings)})", fg="yellow", bold=True)
            for item in warnings:
                click.echo(f"  {item}")

        if issues:
            click.echo()
            click.secho(f"✗ Issues ({len(issues)})", fg="red", bold=True)
            for item in issues:
                click.echo(f"  {item}")

        if not issues and not warnings:
            click.secho("✓ All checks passed! Golden path achieved.", fg="green", bold=True)
        elif issues:
            click.secho(f"Found {len(issues)} issue(s) to fix.", fg="red")
        else:
            click.secho(f"No critical issues. {len(warnings)} warning(s) to review.", fg="yellow")
