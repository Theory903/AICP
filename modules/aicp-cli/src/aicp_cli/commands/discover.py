"""Discovery command for the AICP CLI."""

from __future__ import annotations

import json
from typing import Any


def _normalize(value: Any) -> Any:
    """Normalize objects for JSON serialization."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_normalize(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(value, "__dict__"):
        return {
            key: _normalize(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


async def cmd_discover(registry, args) -> int:
    """Print registry discovery output."""
    del args

    try:
        discovery = registry.discovery_response()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Failed to generate discovery response: {exc}",
                }
            )
        )
        return 1

    print(json.dumps(_normalize(discovery), indent=2, default=str))
    return 0
