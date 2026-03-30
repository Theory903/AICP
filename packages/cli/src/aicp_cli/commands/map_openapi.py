"""OpenAPI mapping command for the AICP CLI."""

import json
from pathlib import Path

from aicp_connect_openapi import OpenAPIDiscoverySource


async def cmd_map_openapi(args) -> int:
    """Map OpenAPI specification to capabilities."""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    try:
        import yaml

        with open(file_path, "r") as f:
            if file_path.suffix in [".yaml", ".yml"]:
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1

    name = args.name or file_path.stem

    try:
        source = OpenAPIDiscoverySource(
            name=name,
            spec=spec,
            base_url=args.base_url,
        )
        capabilities = await source.discover()
    except Exception as e:
        print(f"Error parsing OpenAPI: {e}")
        return 1

    if not capabilities:
        print("No capabilities discovered")
        return 0

    output = {
        "source": name,
        "source_type": "openapi",
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
