"""List command for the AICP CLI."""

from __future__ import annotations

from typing import Any


def _kind_value(kind: Any) -> str:
    """Render capability kind safely."""
    return getattr(kind, "value", str(kind))


async def cmd_list(registry, args) -> int:
    """List capabilities in the local registry."""
    del args

    try:
        capabilities = registry.list_capabilities()
    except Exception as exc:
        print(f"Error: failed to list capabilities: {exc}")
        return 1

    if not capabilities:
        print("No capabilities registered.")
        return 0

    capabilities = sorted(capabilities, key=lambda cap: cap.name)

    name_width = max(len(cap.name) for cap in capabilities)
    kind_width = max(len(_kind_value(cap.kind)) for cap in capabilities)

    for cap in capabilities:
        description = (cap.description or "").strip() or "-"
        print(
            f"  {cap.name:<{name_width}}  "
            f"{_kind_value(cap.kind):<{kind_width}}  "
            f"{description}"
        )

    return 0
