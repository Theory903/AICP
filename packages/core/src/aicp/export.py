"""AICP Capability Exporter.

Exports capabilities as individual YAML files for git-committable config.
This is the output of `aicp scan` — each capability becomes a readable
YAML file in aicp/capabilities/.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aicp.capability import Capability


class CapabilityExportError(ValueError):
    """Raised when a capability cannot be exported safely."""


def _compact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None, empty dicts, and empty lists recursively."""
    compact: dict[str, Any] = {}

    for key, value in data.items():
        if value is None:
            continue

        if isinstance(value, dict):
            nested = _compact_mapping(value)
            if nested:
                compact[key] = nested
            continue

        if isinstance(value, list):
            if value:
                compact[key] = value
            continue

        compact[key] = value

    return compact


def _extract_attrs(
    obj: Any,
    field_names: list[str],
) -> dict[str, Any]:
    """Extract a subset of fields from an object or dict."""
    result: dict[str, Any] = {}

    if obj is None:
        return result

    if isinstance(obj, dict):
        for field in field_names:
            value = obj.get(field)
            if value is not None:
                result[field] = value
        return result

    for field in field_names:
        value = getattr(obj, field, None)
        if value is not None:
            result[field] = value

    return result


def capability_to_dict(capability: Capability) -> dict[str, Any]:
    """Convert a Capability to a clean dictionary for YAML export.

    Strips empty/None fields to keep output minimal and readable.
    """
    data: dict[str, Any] = {
        "name": capability.name,
        "kind": capability.kind.value,
        "description": capability.description,
        "tags": list(capability.tags or []),
        "version": getattr(capability, "version", None),
    }

    input_schema = getattr(capability, "input_schema", None)
    if input_schema is not None:
        input_data = _extract_attrs(
            input_schema,
            [
                "type",
                "properties",
                "required",
                "items",
                "enum",
                "format",
                "description",
                "additionalProperties",
            ],
        )
        input_data = _compact_mapping(input_data)
        if input_data:
            data["input_schema"] = input_data

    output_schema = getattr(capability, "output_schema", None)
    if output_schema is not None:
        output_data = _extract_attrs(
            output_schema,
            [
                "type",
                "properties",
                "required",
                "items",
                "enum",
                "format",
                "description",
                "additionalProperties",
            ],
        )
        output_data = _compact_mapping(output_data)
        if output_data:
            data["output_schema"] = output_data

    continuation = _extract_attrs(
        getattr(capability, "continuation", None),
        ["can_continue", "next_capabilities", "next_hint"],
    )
    continuation = _compact_mapping(continuation)
    if continuation:
        data["continuation"] = continuation

    render = _extract_attrs(
        getattr(capability, "render", None),
        ["format", "fields"],
    )
    render = _compact_mapping(render)
    if render:
        data["render"] = render

    provider = _extract_attrs(
        getattr(capability, "provider", None),
        ["name", "type", "url"],
    )
    provider = _compact_mapping(provider)
    if provider:
        data["provider"] = provider

    return _compact_mapping(data)


def capability_filename(capability_name: str) -> str:
    """Build a filesystem-safe filename for a capability."""
    cleaned = capability_name.strip()
    if not cleaned:
        raise CapabilityExportError("Capability name cannot be empty")

    # Keep dots for namespace readability, replace path-hostile chars.
    cleaned = re.sub(r"[\\/:\0]+", "-", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned)

    return f"{cleaned}.yaml"


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
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for YAML export. Install with: pip install pyyaml"
        ) from exc

    data = capability_to_dict(capability)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    return path


def export_all_capabilities(
    capabilities: list[Capability],
    output_dir: str | Path,
    *,
    overwrite: bool = True,
) -> list[Path]:
    """Write all capabilities as individual YAML files.

    Each capability is written to: <output_dir>/<capability_name>.yaml

    Args:
        capabilities: List of capabilities to export
        output_dir: Directory to write files to
        overwrite: Whether existing files may be replaced

    Returns:
        List of written file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    seen_names: set[str] = set()

    for capability in capabilities:
        if capability.name in seen_names:
            raise CapabilityExportError(
                f"Duplicate capability name during export: {capability.name}"
            )
        seen_names.add(capability.name)

        file_path = output_path / capability_filename(capability.name)

        if file_path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {file_path}")

        export_capability_yaml(capability, file_path)
        written.append(file_path)

    return written