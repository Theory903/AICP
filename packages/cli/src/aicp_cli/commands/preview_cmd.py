"""aicp preview — Inspect a capability and its effective policy stack."""

import logging
from pathlib import Path

import click
import yaml

from aicp.config import load_project_config

# Disable logging so aicp core info logs don't clutter the CLI output
logging.getLogger("aicp").setLevel(logging.WARNING)


@click.command()
@click.argument("capability_name")
def preview(capability_name):
    """Preview a capability and its effective policy stack.

    Loads the capability from your local capabilities directory and
    calculates its exact runtime governance effects based on aicp.yaml.

    Example:
        aicp preview notes.delete
    """
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.box import ROUNDED
    except ImportError:
        click.secho("The 'rich' library is required. Run: pip install rich", fg="red")
        return

    console = Console()

    # 1. Load config and policy
    try:
        config = load_project_config()
    except Exception as e:
        console.print(f"[red]Error loading aicp.yaml:[/] {e}")
        return

    # 2. Load capability file
    caps_dir = Path(config.capabilities_dir)
    cap_file = caps_dir / f"{capability_name}.yaml"

    if not cap_file.exists():
        console.print(f"[red]Capability not found:[/] {cap_file}")
        return

    try:
        with open(cap_file) as f:
            cap_data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Error parsing {cap_file.name}:[/] {e}")
        return

    kind = cap_data.get("kind", "unknown")
    desc = cap_data.get("description", "No description provided.")
    tags = cap_data.get("tags", [])
    
    # Extract risk and destructive
    risk = "unknown"
    destructive = False
    for t in tags:
        if t.startswith("risk:"):
            risk = t.split(":", 1)[1]
        elif t == "destructive":
            destructive = True

    # 3. Calculate effective policy
    # We use the config object to resolve the effect
    effect = config.effective_effect(capability_name, kind)
    
    # Determine the rule that matched (for transparency)
    import fnmatch
    matched_rule = None
    for rule in config.rules:
        if fnmatch.fnmatch(capability_name, rule.match):
            matched_rule = rule
            break
            
    # Default fallback reason
    rule_source = "Matched explicit rule in aicp.yaml" if matched_rule else "Default fallback policy"
    if matched_rule and matched_rule.reason:
        rule_source += f" (Reason: {matched_rule.reason})"

    # 4. Render
    
    # 4a. Header panel
    risk_colors = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}
    risk_color = risk_colors.get(risk, "white")
    
    header_text = Text()
    header_text.append("Name:        ", style="dim")
    header_text.append(f"{capability_name}\n", style="cyan bold")
    header_text.append("Kind:        ", style="dim")
    header_text.append(f"{kind}\n", style="magenta")
    header_text.append("Description: ", style="dim")
    header_text.append(f"{desc}\n")
    header_text.append("Risk:        ", style="dim")
    header_text.append(f"{risk}", style=risk_color)
    if destructive:
        header_text.append(" | ", style="dim")
        header_text.append("DESTRUCTIVE", style="bold red")

    console.print(Panel(header_text, title="[bold]Capability[/]", border_style="cyan", box=ROUNDED))

    # 4b. Governance panel
    effect_colors = {"allow": "green", "deny": "bold red", "ask": "yellow", "require_approval": "red", "limit": "blue"}
    effect_color = effect_colors.get(effect, "white")
    
    gov_text = Text()
    gov_text.append("Effective Policy: ", style="dim")
    gov_text.append(f"{effect.upper()}\n", style=f"bold {effect_color}")
    gov_text.append("Source:           ", style="dim")
    gov_text.append(f"{rule_source}")
    if matched_rule and matched_rule.rpm:
        gov_text.append("\nRate Limit:       ", style="dim")
        gov_text.append(f"{matched_rule.rpm} RPM")

    console.print(Panel(gov_text, title="[bold]Governance Stack[/]", border_style=effect_color, box=ROUNDED))

    # 4c. Schemas
    schema_text = Text()
    in_schema = cap_data.get("input_schema", {})
    if in_schema and in_schema.get("properties"):
        schema_text.append("Input Properties:\n", style="bold")
        for k, v in in_schema.get("properties", {}).items():
            req = "*" if k in in_schema.get("required", []) else " "
            schema_text.append(f"  {req}{k}: ", style="cyan")
            schema_text.append(f"{v.get('type', 'any')}\n", style="dim")
    else:
        schema_text.append("Input Properties:\n  None\n\n", style="dim")
        
    out_schema = cap_data.get("output_schema", {})
    if out_schema and out_schema.get("properties"):
        schema_text.append("\nOutput Properties:\n", style="bold")
        for k, v in out_schema.get("properties", {}).items():
            schema_text.append(f"  {k}: ", style="magenta")
            schema_text.append(f"{v.get('type', 'any')}\n", style="dim")
    else:
        schema_text.append("\nOutput Properties:\n  None", style="dim")

    console.print(Panel(schema_text, title="[bold]I/O Contract[/]", border_style="blue", box=ROUNDED))

    # 4d. Continuation hints
    continuation = cap_data.get("continuation", {})
    if continuation:
        cont_text = Text()
        if "next_hint" in continuation:
            cont_text.append("Hint: ", style="bold")
            cont_text.append(f"{continuation['next_hint']}\n")
        if "next_capabilities" in continuation:
            cont_text.append("Next Capabilities: ", style="bold")
            cont_text.append(f"{', '.join(continuation['next_capabilities'])}")
        
        console.print(Panel(cont_text, title="[bold]Workflow Hints[/]", border_style="magenta", box=ROUNDED))

    console.print()
