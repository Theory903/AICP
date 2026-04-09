"""Execute command for the AICP CLI."""

from __future__ import annotations

import json
from typing import Any


def _normalize(value: Any) -> Any:
    """Normalize values for JSON output."""
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
        return model_dump(exclude_none=True)

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


def _parse_json_object(
    raw: str | None, *, flag_name: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a JSON CLI flag and require an object result."""
    if raw is None or raw.strip() == "":
        return {}, None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {flag_name}: {exc}"

    if not isinstance(parsed, dict):
        return None, f"{flag_name} must decode to a JSON object"

    return parsed, None


async def cmd_execute(registry, executor, args) -> int:
    """Execute a capability and print normalized output."""
    del registry

    capability_name = getattr(args, "capability", None)
    if not capability_name:
        print(json.dumps({"error": "Missing capability name"}))
        return 1

    exec_args, args_error = _parse_json_object(
        getattr(args, "args", None), flag_name="--args"
    )
    if args_error:
        print(json.dumps({"error": args_error}))
        return 1

    exec_context, context_error = _parse_json_object(
        getattr(args, "context", None), flag_name="--context"
    )
    if context_error:
        print(json.dumps({"error": context_error}))
        return 1

    try:
        result = await executor.execute(
            capability_name, exec_args or {}, exec_context or {}
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": f"Execution failed: {exc}",
                    "capability": capability_name,
                },
                indent=2,
            )
        )
        return 1

    output = _normalize(result)
    print(json.dumps(output, indent=2, default=str))

    status = getattr(result, "status", None)
    status_value = getattr(status, "value", status)
    return 0 if status_value == "success" else 1
