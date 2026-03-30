"""HAR mapping command for the AICP CLI."""

import json
from pathlib import Path

from aicp_connect_har import HarImporter


async def cmd_map_har(args) -> int:
    """Map HAR file to capabilities."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    try:
        har = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1

    name = args.name or file_path.stem

    try:
        importer = HarImporter(name=name, har=har)
        capabilities = await importer.discover()
    except Exception as e:
        print(f"Error parsing HAR: {e}")
        return 1

    if not capabilities:
        print("No capabilities discovered")
        return 0

    output = {
        "source": name,
        "source_type": "har",
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
