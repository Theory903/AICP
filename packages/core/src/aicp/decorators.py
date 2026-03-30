"""Tool decorator for creating AICP capabilities from Python functions.

Automatically generates capability definitions from function signatures and type hints.
Supports risk classification, approval requirements, and destructive action marking.

Usage:
    @capability(name="payments.transfer", risk="high", approval="required")
    async def transfer(to_account: str, amount: float) -> dict:
        '''Transfer funds to another account'''
        return {"status": "success"}

    @capability("notes.list", safe=True)
    async def list_notes(skip: int = 0, limit: int = 10) -> list:
        ...

    @capability("notes.delete", destructive=True)
    async def delete_note(id: int) -> dict:
        ...
"""

import inspect
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin, get_type_hints

from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema

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
        required=required if required else [],
    )

    return_type = hints.get("return")
    output_schema = OutputSchema(type="object")

    if return_type:
        output_schema.properties = {"result": {"type": _python_type_to_json_type(return_type)}}

    return input_schema, output_schema


def _infer_kind_from_name(name: str) -> CapabilityKind:
    """Infer capability kind from its name."""
    name_lower = name.lower()
    last_part = name_lower.split(".")[-1] if "." in name_lower else name_lower

    query_indicators = {"list", "get", "search", "find", "count", "check", "ping", "health", "status"}
    if last_part in query_indicators:
        return CapabilityKind.QUERY

    return CapabilityKind.ACTION


def _infer_risk_from_name(name: str) -> str:
    """Infer risk level from capability name."""
    from aicp.risk import infer_risk

    risk = infer_risk(name)
    return risk.value


def _infer_destructive_from_name(name: str) -> bool:
    """Infer destructive flag from capability name."""
    from aicp.risk import is_destructive

    return is_destructive(name)


def capability(
    name: str | None = None,
    description: str | None = None,
    kind: CapabilityKind | None = None,
    tags: list[str] | None = None,
    risk: str | None = None,
    approval: str | None = None,
    destructive: bool | None = None,
    safe: bool = False,
):
    """Decorator to create an AICP capability from a Python function.

    Args:
        name: Capability name (defaults to function name).
        description: Description (defaults to docstring).
        kind: Capability kind (auto-inferred if not set).
        tags: Tags for categorization.
        risk: Risk level — "low", "medium", "high", "critical".
            Auto-inferred from name if not set.
        approval: Approval requirement — "none", "optional", "required".
            Auto-mapped from risk if not set.
        destructive: Whether the action is destructive.
            Auto-inferred from name/method if not set.
        safe: Shorthand for risk="low", approval="none", destructive=False.

    Example:
        @capability(name="payments.transfer", risk="high", approval="required")
        async def transfer(to_account: str, amount: float) -> dict:
            '''Transfer funds to another account'''
            return {"status": "success"}

        @capability("notes.delete", destructive=True)
        async def delete_note(id: int) -> dict: ...

        @capability("notes.list", safe=True)
        async def list_notes() -> list: ...
    """

    def decorator(func: Callable) -> Callable:
        cap_name = name or func.__name__
        cap_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        cap_tags = list(tags) if tags else ["python"]

        # Auto-infer kind
        cap_kind = kind
        if cap_kind is None:
            cap_kind = _infer_kind_from_name(cap_name)

        # Handle safe shorthand
        cap_risk = risk
        cap_approval = approval
        cap_destructive = destructive

        if safe:
            cap_risk = cap_risk or "low"
            cap_approval = cap_approval or "none"
            cap_destructive = cap_destructive if cap_destructive is not None else False
        else:
            # Auto-infer risk
            if cap_risk is None:
                cap_risk = _infer_risk_from_name(cap_name)

            # Auto-infer destructive
            if cap_destructive is None:
                cap_destructive = _infer_destructive_from_name(cap_name)

            # Auto-map approval from risk
            if cap_approval is None:
                risk_to_approval = {
                    "low": "none",
                    "medium": "optional",
                    "high": "required",
                    "critical": "required",
                }
                cap_approval = risk_to_approval.get(cap_risk, "none")

        # Add risk/approval/destructive tags
        metadata_tags = []
        if cap_risk:
            metadata_tags.append(f"risk:{cap_risk}")
        if cap_approval:
            metadata_tags.append(f"approval:{cap_approval}")
        if cap_destructive:
            metadata_tags.append("destructive")

        cap_tags.extend(metadata_tags)

        input_schema, output_schema = _generate_schema(func)

        capability_obj = Capability(
            name=cap_name,
            description=cap_desc,
            kind=cap_kind,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=cap_tags,
        )

        _capabilities.append(capability_obj)

        # Attach metadata to the function for introspection
        func._aicp_capability = capability_obj
        func._aicp_risk = cap_risk
        func._aicp_approval = cap_approval
        func._aicp_destructive = cap_destructive

        return func

    return decorator
