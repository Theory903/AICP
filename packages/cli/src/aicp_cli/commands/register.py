"""Register command for the AICP CLI."""

from __future__ import annotations

from typing import Any

from aicp import Capability, CapabilityKind


def _normalize_name(value: Any) -> str:
    """Normalize and validate capability name."""
    name = str(value or "").strip()
    if not name:
        raise ValueError("Capability name cannot be empty")
    return name


def _normalize_description(value: Any) -> str:
    """Normalize description text."""
    return str(value or "").strip()


def _normalize_kind(value: Any) -> CapabilityKind:
    """Normalize kind input into CapabilityKind."""
    raw = str(value or "").strip().lower()
    if not raw:
        raise ValueError("Capability kind is required")

    try:
        return CapabilityKind(raw)
    except ValueError as exc:
        allowed = ", ".join(kind.value for kind in CapabilityKind)
        raise ValueError(
            f"Invalid capability kind '{value}'. Expected one of: {allowed}"
        ) from exc


async def cmd_register(registry, args) -> int:
    """Register a capability in the local registry."""
    try:
        name = _normalize_name(getattr(args, "name", None))
        description = _normalize_description(getattr(args, "description", ""))
        kind = _normalize_kind(getattr(args, "kind", None))
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    try:
        existing = registry.get_capability(name)
    except Exception:
        existing = None

    if existing is not None:
        print(f"Error: Capability '{name}' is already registered")
        return 1

    try:
        capability = Capability(
            name=name,
            description=description,
            kind=kind,
        )
        registry.register_capability(capability)
    except Exception as exc:
        print(f"Error: Failed to register capability: {exc}")
        return 1

    print(f"Registered: {name}")
    return 0
