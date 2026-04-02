"""Call command for the AICP CLI."""

from __future__ import annotations

import json
from typing import Any


def _normalize_result(value: Any) -> Any:
    """Normalize result objects for JSON output."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_normalize_result(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize_result(item) for key, item in value.items()}

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_dict()

    if hasattr(value, "__dict__"):
        return {
            key: _normalize_result(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def _parse_json_arg(raw: str | None, *, flag_name: str) -> tuple[Any, str | None]:
    """Parse a JSON CLI argument."""
    if raw is None or raw.strip() == "":
        return {}, None

    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {flag_name}: {exc}"


async def cmd_call(registry, executor, args) -> int:
    """Call a capability through the executor."""
    del registry

    if not getattr(args, "name", None):
        print(json.dumps({"error": "Missing capability name"}))
        return 1

    call_args, args_error = _parse_json_arg(
        getattr(args, "args", None), flag_name="--args"
    )
    if args_error:
        print(json.dumps({"error": args_error}))
        return 1

    context, context_error = _parse_json_arg(
        getattr(args, "context", None), flag_name="--context"
    )
    if context_error:
        print(json.dumps({"error": context_error}))
        return 1

    if not isinstance(call_args, dict):
        print(json.dumps({"error": "--args must decode to a JSON object"}))
        return 1

    if not isinstance(context, dict):
        print(json.dumps({"error": "--context must decode to a JSON object"}))
        return 1

    try:
        result = await executor.execute(args.name, call_args, context)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Execution failed: {exc}",
                    "capability": args.name,
                },
                indent=2,
            )
        )
        return 1

    output = _normalize_result(result)
    print(json.dumps(output, indent=2, default=str))

    status = getattr(result, "status", None)
    status_value = getattr(status, "value", status)
    return 0 if status_value == "success" else 1
