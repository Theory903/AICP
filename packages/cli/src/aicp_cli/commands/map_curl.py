"""cURL mapping command for the AICP CLI."""

import json
from pathlib import Path

from aicp_connect_curl import CurlImporter


async def cmd_map_curl(args) -> int:
    """Map cURL command text to capabilities."""
    name = args.name or "curl-import"

    try:
        importer = CurlImporter(name=name, curl_command=args.command_text)
        capabilities = await importer.discover()
    except Exception as e:
        print(f"Error parsing cURL: {e}")
        return 1

    if not capabilities:
        print("No capabilities discovered")
        return 0

    output = {
        "source": name,
        "source_type": "curl",
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
