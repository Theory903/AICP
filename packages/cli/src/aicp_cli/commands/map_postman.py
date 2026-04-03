"""Postman mapping command for the AICP CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aicp_connect_postman import PostmanCollectionImporter


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


def _load_collection(file_path: Path) -> dict[str, Any]:
    """Load and validate a Postman collection file."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to read file: {exc}") from exc

    try:
        collection = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(collection, dict):
        raise ValueError("Postman collection root must be a JSON object")

    info = collection.get("info")
    items = collection.get("item")

    if not isinstance(info, dict):
        raise ValueError("Invalid Postman collection: missing or invalid 'info' object")

    if not isinstance(items, list):
        raise ValueError("Invalid Postman collection: missing or invalid 'item' list")

    return collection


def _build_output(
    *,
    name: str,
    collection: dict[str, Any],
    capabilities: list[Any],
) -> dict[str, Any]:
    """Build stable JSON output for mapped capabilities."""
    info = collection.get("info", {})

    return {
        "source": name,
        "source_type": "postman",
        "collection_name": info.get("name"),
        "collection_description": info.get("description"),
        "postman_schema": info.get("schema"),
        "capability_count": len(capabilities),
        "capabilities": [_normalize(cap) for cap in capabilities],
    }


def _write_output(output_path: Path, content: str) -> None:
    """Write output JSON safely."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


async def cmd_map_postman(args) -> int:
    """Map Postman collection to capabilities."""
    file_arg = getattr(args, "file", None)
    if not file_arg:
        print(json.dumps({"error": "Missing Postman collection file path"}))
        return 1

    file_path = Path(file_arg)
    if not file_path.exists():
        print(json.dumps({"error": f"File not found: {file_path}"}))
        return 1

    try:
        collection = _load_collection(file_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "file": str(file_path),
                    "source_type": "postman",
                },
                indent=2,
            )
        )
        return 1

    name = getattr(args, "name", None) or file_path.stem

    try:
        importer = PostmanCollectionImporter(name=name, collection=collection)
        capabilities = await importer.discover()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Error parsing Postman collection: {exc}",
                    "file": str(file_path),
                    "source": name,
                    "source_type": "postman",
                },
                indent=2,
            )
        )
        return 1

    output = _build_output(name=name, collection=collection, capabilities=capabilities)
    output_json = json.dumps(output, indent=2, default=str)

    output_arg = getattr(args, "output", None)
    if output_arg:
        try:
            output_path = Path(output_arg)
            _write_output(output_path, output_json)
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
