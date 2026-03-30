"""AICP Capability Exporter.

Exports capabilities as individual YAML files for git-committable config.
This is the output of `aicp scan` — each capability becomes a readable
YAML file in aicp/capabilities/.
"""

from pathlib import Path
from typing import Any

from .capability import Capability


def capability_to_dict(capability: Capability) -> dict[str, Any]:
    """Convert a Capability to a clean dictionary for YAML export.

    Strips empty/None fields to keep output minimal and readable.
    """
    data: dict[str, Any] = {
        "name": capability.name,
        "kind": capability.kind.value,
    }

    if capability.description:
        data["description"] = capability.description

    # Tags (including risk & destructive)
    if capability.tags:
        data["tags"] = capability.tags

    # Input schema — only include if there are properties
    input_schema = capability.input_schema
    if input_schema and input_schema.properties:
        schema_dict: dict[str, Any] = {"type": input_schema.type}
        if input_schema.properties:
            schema_dict["properties"] = input_schema.properties
        if input_schema.required:
            schema_dict["required"] = input_schema.required
        data["input_schema"] = schema_dict

    # Output schema
    output_schema = capability.output_schema
    if output_schema and output_schema.properties:
        schema_dict = {"type": output_schema.type}
        if output_schema.properties:
            schema_dict["properties"] = output_schema.properties
        data["output_schema"] = schema_dict

    # Continuation hints
    if capability.continuation:
        c = capability.continuation
        cont = {}
        if isinstance(c, dict):
            if c.get("can_continue") is not None:
                cont["can_continue"] = c["can_continue"]
            if c.get("next_capabilities"):
                cont["next_capabilities"] = c["next_capabilities"]
            if c.get("next_hint"):
                cont["next_hint"] = c["next_hint"]
        else:
            if getattr(c, "can_continue", None) is not None:
                cont["can_continue"] = getattr(c, "can_continue")
            if getattr(c, "next_capabilities", None):
                cont["next_capabilities"] = getattr(c, "next_capabilities")
            if getattr(c, "next_hint", None):
                cont["next_hint"] = getattr(c, "next_hint")
        if cont:
            data["continuation"] = cont

    # Render hints
    if capability.render:
        r = capability.render
        render = {}
        if isinstance(r, dict):
            if r.get("format"):
                render["format"] = r["format"]
            if r.get("fields"):
                render["fields"] = r["fields"]
        else:
            if getattr(r, "format", None):
                render["format"] = getattr(r, "format")
            if getattr(r, "fields", None):
                render["fields"] = getattr(r, "fields")
        if render:
            data["render"] = render

    # Provider info
    if capability.provider:
        p = capability.provider
        provider = {}
        if isinstance(p, dict):
            if p.get("name"):
                provider["name"] = p["name"]
            if p.get("type"):
                provider["type"] = p["type"]
            if p.get("url"):
                provider["url"] = p["url"]
        else:
            if getattr(p, "name", None):
                provider["name"] = getattr(p, "name")
            if getattr(p, "type", None):
                provider["type"] = getattr(p, "type")
            if getattr(p, "url", None):
                provider["url"] = getattr(p, "url")
        if provider:
            data["provider"] = provider

    # Version
    if capability.version:
        data["version"] = capability.version

    return data


def export_capability_yaml(capability: Capability, path: Path) -> Path:
    """Write a single capability as a YAML file.

    Args:
        capability: Capability to export
        path: Output file path

    Returns:
        Path to the written file
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML export. Install with: pip install pyyaml"
        )

    data = capability_to_dict(capability)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return path


def export_all_capabilities(
    capabilities: list[Capability],
    output_dir: str | Path,
) -> list[Path]:
    """Write all capabilities as individual YAML files.

    Each capability is written to: <output_dir>/<capability_name>.yaml

    Args:
        capabilities: List of capabilities to export
        output_dir: Directory to write files to

    Returns:
        List of written file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written = []
    for cap in capabilities:
        filename = f"{cap.name}.yaml"
        file_path = output_path / filename
        export_capability_yaml(cap, file_path)
        written.append(file_path)

    return written
