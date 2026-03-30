"""Call command for the AICP CLI."""

import json


async def cmd_call(registry, executor, args) -> int:
    """Call a capability through the executor."""
    del registry
    try:
        call_args = json.loads(args.args)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in --args")
        return 1

    result = await executor.execute(args.name, call_args)
    print(json.dumps(result.model_dump(), indent=2))
    return 0 if result.status.value == "success" else 1
