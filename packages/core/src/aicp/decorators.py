"""Tool decorator for creating AICP capabilities from Python functions.

Automatically generates capability definitions from function signatures and type hints.
"""

import inspect
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin, get_type_hints

from aicp import Capability, CapabilityKind, InputSchema, OutputSchema

_capabilities: list[Capability] = []


def get_registered_capabilities() -> list[Capability]:
    """Get all capabilities registered via the decorator."""
    return _capabilities.copy()


def clear_capabilities() -> None:
    """Clear all registered capabilities."""
    _capabilities.clear()


def _python_type_to_json_type(py_type) -> str:
    """Convert Python type to JSON Schema type."""
    origin = get_origin(py_type)

    if origin is Union:
        non_none = [a for a in get_args(py_type) if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_json_type(non_none[0])

    if origin in (list, list):
        return "array"
    if origin in (dict, dict):
        return "object"

    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        Any: "object",
    }
    return mapping.get(py_type, "object")


def _generate_schema(func: Callable) -> tuple[InputSchema, OutputSchema]:
    """Generate input and output schemas from function signature."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    input_properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        py_type = hints.get(param_name, str)
        input_properties[param_name] = {"type": _python_type_to_json_type(py_type)}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    input_schema = InputSchema(
        type="object",
        properties=input_properties,
        required=required if required else None,
    )

    return_type = hints.get("return")
    output_schema = OutputSchema(type="object")

    if return_type:
        output_schema.properties = {"result": {"type": _python_type_to_json_type(return_type)}}

    return input_schema, output_schema


def capability(
    name: str | None = None,
    description: str | None = None,
    kind: CapabilityKind = CapabilityKind.ACTION,
    tags: list[str] | None = None,
):
    """Decorator to create an AICP capability from a Python function.

    Args:
        name: Capability name (defaults to function name).
        description: Description (defaults to docstring).
        kind: Capability kind (defaults to ACTION).
        tags: Tags for categorization.

    Example:
        @capability(name="payments.transfer", kind=CapabilityKind.ACTION)
        async def transfer(to_account: str, amount: float) -> dict:
            '''Transfer funds to another account'''
            return {"status": "success"}
    """

    def decorator(func: Callable) -> Callable:
        cap_name = name or func.__name__
        cap_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        cap_tags = tags or ["python"]

        input_schema, output_schema = _generate_schema(func)

        capability_obj = Capability(
            name=cap_name,
            description=cap_desc,
            kind=kind,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=cap_tags,
        )

        _capabilities.append(capability_obj)

        func._aicp_capability = capability_obj

        return func

    return decorator
