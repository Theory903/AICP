"""Discovery command for the AICP CLI."""

import json


async def cmd_discover(registry, args) -> int:
    """Print registry discovery output."""
    del args
    discovery = registry.discovery_response()
    print(json.dumps(discovery, indent=2))
    return 0
