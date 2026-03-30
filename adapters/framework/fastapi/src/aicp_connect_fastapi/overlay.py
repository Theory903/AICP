"""Overlay support for AICP configuration."""

from pathlib import Path
from typing import Any

from aicp_connect_fastapi.types import AicpConfig, RouteMapping


def load_overlay(path: str | Path | None) -> dict[str, Any] | None:
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
        return None


def merge_overlay(config: AicpConfig, overlay: dict[str, Any]) -> AicpConfig:
    if "version" in overlay:
        config.version = overlay["version"]

    if "provider" in overlay:
        provider = overlay["provider"]
        if "name" in provider:
            config.provider_name = provider["name"]
        if "url" in provider:
            config.provider_url = provider["url"]

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
