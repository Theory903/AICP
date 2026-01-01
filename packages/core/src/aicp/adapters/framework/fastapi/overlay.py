"""Overlay support for AICP configuration.

Allows merging optional aicp.yaml overlay with auto-detected capabilities.
"""

from pathlib import Path
from typing import Any

from aicp.adapters.framework.fastapi.types import AicpConfig, RouteMapping


def load_overlay(path: str | Path | None) -> dict[str, Any] | None:
    """Load AICP overlay from YAML file.

    Args:
        path: Path to aicp.yaml file

    Returns:
        Overlay dictionary or None if file doesn't exist
    """
    if path is None:
        return None

    path = Path(path)
    if not path.exists():
        return None

    try:
        import yaml

        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        # yaml not installed, skip overlay
        return None


def merge_overlay(
    config: AicpConfig,
    overlay: dict[str, Any],
) -> AicpConfig:
    """Merge overlay with existing configuration.

    Args:
        config: Base AICP configuration
        overlay: Overlay configuration

    Returns:
        Merged configuration
    """
    # Override version
    if "version" in overlay:
        config.version = overlay["version"]

    # Override provider info
    if "provider" in overlay:
        provider = overlay["provider"]
        if "name" in provider:
            config.provider_name = provider["name"]
        if "url" in provider:
            config.provider_url = provider["url"]

    # Add explicit capability overrides
    if "capabilities" in overlay:
        for cap_override in overlay["capabilities"]:
            cap_name = cap_override.get("name")
            existing = None
            for mapping in config.route_mappings:
                if mapping.capability_name == cap_name:
                    existing = mapping
                    break

            if existing:
                if "description" in cap_override:
                    existing.description = cap_override["description"]
                if "kind" in cap_override:
                    existing.kind = cap_override["kind"]
            else:
                config.route_mappings.append(
                    RouteMapping(
                        route_path=cap_override.get("route", "/"),
                        capability_name=cap_name,
                        description=cap_override.get("description", ""),
                        kind=cap_override.get("kind", "action"),
                    )
                )

    return config


def find_overlay_file(base_path: str | Path) -> Path | None:
    """Find aicp.yaml file in the given directory.

    Args:
        base_path: Base directory to search

    Returns:
        Path to aicp.yaml or None
    """
    base_path = Path(base_path)

    candidates = [
        base_path / "aicp.yaml",
        base_path / "aicp.yml",
        base_path / ".aicp.yaml",
        base_path / ".aicp.yml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None
