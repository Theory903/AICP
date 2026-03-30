"""Postman mapping command for the AICP CLI."""

import json
from pathlib import Path

from aicp_connect_postman import PostmanCollectionImporter


async def cmd_map_postman(args) -> int:
    """Map Postman collection to capabilities."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    try:
        collection = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1

    name = args.name or file_path.stem

    try:
        importer = PostmanCollectionImporter(name=name, collection=collection)
        capabilities = await importer.discover()
    except Exception as e:
        print(f"Error parsing Postman collection: {e}")
        return 1

    if not capabilities:
        print("No capabilities discovered")
        return 0

    output = {
        "source": name,
        "source_type": "postman",
        "capability_count": len(capabilities),
        "capabilities": [cap.model_dump(exclude_none=True, mode="json") for cap in capabilities],
    }

    output_json = json.dumps(output, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_json)
        print(f"Mapped {len(capabilities)} capabilities to {output_path}")
    else:
        print(output_json)

    return 0
