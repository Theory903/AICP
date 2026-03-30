"""Execute command for the AICP CLI."""

import json


async def cmd_execute(registry, executor, args) -> int:
    """Execute a capability and print normalized output."""
    del registry
    try:
        exec_args = json.loads(args.args)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in --args")
        return 1

    try:
        exec_context = json.loads(args.context)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in --context")
        return 1

    result = await executor.execute(args.capability, exec_args, exec_context)
    print(json.dumps(result.model_dump(), indent=2))
    return 0 if result.status.value == "success" else 1
