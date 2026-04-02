"""HAR mapping command for the AICP CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aicp_connect_har import HarImporter


def _normalize(value: Any) -> Any:
    """Normalize values for JSON serialization."""
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
        return model_dump(exclude_none=True, mode="json")

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


async def cmd_map_har(args) -> int:
    """Map HAR file to capabilities."""
    file_arg = getattr(args, "file", None)
    if not file_arg:
        print(json.dumps({"error": "Missing HAR file path"}))
        return 1

    file_path = Path(file_arg)
    if not file_path.exists():
        print(json.dumps({"error": f"File not found: {file_path}"}))
        return 1

    try:
        har = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            json.dumps(
                {
                    "error": f"Invalid JSON: {exc}",
                    "file": str(file_path),
                },
                indent=2,
            )
        )
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Error reading file: {exc}",
                    "file": str(file_path),
                },
                indent=2,
            )
        )
        return 1

    name = getattr(args, "name", None) or file_path.stem

    try:
        importer = HarImporter(name=name, har=har)
        capabilities = await importer.discover()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Error parsing HAR: {exc}",
                    "source": name,
                    "source_type": "har",
                },
                indent=2,
            )
        )
        return 1

    if not capabilities:
        print(
            json.dumps(
                {
                    "source": name,
                    "source_type": "har",
                    "capability_count": 0,
                    "capabilities": [],
                },
                indent=2,
            )
        )
        return 0

    output = {
        "source": name,
        "source_type": "har",
        "capability_count": len(capabilities),
        "capabilities": [_normalize(cap) for cap in capabilities],
    }

    output_json = json.dumps(output, indent=2, default=str)

    output_arg = getattr(args, "output", None)
    if output_arg:
        try:
            output_path = Path(output_arg)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_json, encoding="utf-8")
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "error": f"Failed to write output file: {exc}",
                        "path": str(output_arg),
                    },
                    indent=2,
                )
            )
            return 1

        print(f"Mapped {len(capabilities)} capabilities to {output_path}")
        return 0

    print(output_json)
    return 0
