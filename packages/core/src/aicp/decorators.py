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

from __future__ import annotations

import inspect
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal, get_args, get_origin, get_type_hints

from aicp.capability import Capability, CapabilityKind, InputSchema, OutputSchema

_REGISTERED_CAPABILITIES: dict[str, Capability] = {}

_ALLOWED_RISK = {"low", "medium", "high", "critical"}
_ALLOWED_APPROVAL = {"none", "optional", "required"}


def get_registered_capabilities() -> list[Capability]:
    """Get all capabilities registered via the decorator."""
    return list(_REGISTERED_CAPABILITIES.values())


def get_registered_capability(name: str) -> Capability | None:
    """Get a single registered capability by name."""
    return _REGISTERED_CAPABILITIES.get(name)


def clear_capabilities() -> None:
    """Clear all registered capabilities."""
    _REGISTERED_CAPABILITIES.clear()


def _is_optional_type(py_type: Any) -> tuple[bool, Any]:
    """Return (is_optional, unwrapped_type)."""
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is None:
        return False, py_type

    if origin in (__import__("typing").Union,):
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1 and len(non_none) != len(args):
            return True, non_none[0]

    # PEP 604 style: str | None
    if str(origin) in {"types.UnionType", "<class 'types.UnionType'>"}:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1 and len(non_none) != len(args):
            return True, non_none[0]

    return False, py_type


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """Convert a Python type hint into a JSON-schema-like shape."""
    if py_type is inspect.Signature.empty or py_type is Any:
        return {"type": "object"}

    is_optional, unwrapped = _is_optional_type(py_type)
    if is_optional:
        schema = _python_type_to_json_schema(unwrapped)
        schema["nullable"] = True
        return schema

    origin = get_origin(py_type)
    args = get_args(py_type)

    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type is bytes:
        return {"type": "string", "format": "binary"}
    if py_type is dict:
        return {"type": "object"}
    if py_type is list:
        return {"type": "array", "items": {"type": "object"}}
    if py_type is type(None):
        return {"type": "null"}

    if inspect.isclass(py_type) and issubclass(py_type, Enum):
        values = [member.value for member in py_type]
        inferred_type = "string"
        if values and all(isinstance(v, bool) for v in values):
            inferred_type = "boolean"
        elif values and all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            inferred_type = "integer"
        elif values and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            inferred_type = "number"

        return {"type": inferred_type, "enum": values}

    if origin in (list, tuple, set):
        item_schema = _python_type_to_json_schema(args[0]) if args else {"type": "object"}
        return {"type": "array", "items": item_schema}

    if origin is dict:
        return {"type": "object"}

    if origin is Literal:
        literal_values = list(args)
        if literal_values:
            sample = literal_values[0]
            if isinstance(sample, bool):
                literal_type = "boolean"
            elif isinstance(sample, int) and not isinstance(sample, bool):
                literal_type = "integer"
            elif isinstance(sample, float):
                literal_type = "number"
            else:
                literal_type = "string"
            return {"type": literal_type, "enum": literal_values}
        return {"type": "string"}

    if inspect.isclass(py_type) and hasattr(py_type, "model_json_schema"):
        # Pydantic v2 model
        try:
            schema = py_type.model_json_schema()
            if "type" not in schema:
                schema["type"] = "object"
            return schema
        except Exception:
            return {"type": "object"}

    if inspect.isclass(py_type) and hasattr(py_type, "schema"):
        # Pydantic v1 fallback
        try:
            schema = py_type.schema()
            if "type" not in schema:
                schema["type"] = "object"
            return schema
        except Exception:
            return {"type": "object"}

    if inspect.isclass(py_type) and py_type.__name__ in {"datetime", "date", "time"}:
        format_map = {
            "datetime": "date-time",
            "date": "date",
            "time": "time",
        }
        return {"type": "string", "format": format_map[py_type.__name__]}

    return {"type": "object"}


def _generate_schema(func: Callable[..., Any]) -> tuple[InputSchema, OutputSchema]:
    """Generate input and output schemas from function signature."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    input_properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in {"self", "cls"}:
            continue
        if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue

        hinted_type = hints.get(param_name, Any)
        input_properties[param_name] = _python_type_to_json_schema(hinted_type)

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    input_schema = InputSchema(
        type="object",
        properties=input_properties,
        required=required,
    )

    return_type = hints.get("return", Any)
    output_schema_data = _python_type_to_json_schema(return_type)

    if output_schema_data.get("type") == "object":
        output_schema = OutputSchema(**output_schema_data)
    else:
        output_schema = OutputSchema(
            type="object",
            properties={"result": output_schema_data},
        )

    return input_schema, output_schema


def _infer_kind_from_name(name: str) -> CapabilityKind:
    """Infer capability kind from its name."""
    name_lower = name.lower()
    last_part = name_lower.split(".")[-1] if "." in name_lower else name_lower

    query_indicators = {
        "list",
        "get",
        "search",
        "find",
        "count",
        "check",
        "ping",
        "health",
        "status",
        "read",
        "fetch",
    }
    return CapabilityKind.QUERY if last_part in query_indicators else CapabilityKind.ACTION


def _infer_risk_from_name(name: str) -> str:
    """Infer risk level from capability name."""
    from aicp.risk import infer_risk

    return infer_risk(name).value


def _infer_destructive_from_name(name: str) -> bool:
    """Infer destructive flag from capability name."""
    from aicp.risk import is_destructive

    return is_destructive(name)


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return ["python"]

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    if "python" not in seen:
        normalized.append("python")
    return normalized


def capability(
    name: str | None = None,
    description: str | None = None,
    kind: CapabilityKind | None = None,
    tags: list[str] | None = None,
    risk: str | None = None,
    approval: str | None = None,
    destructive: bool | None = None,
    safe: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to create an AICP capability from a Python function.

    Args:
        name: Capability name. Defaults to function name.
        description: Description. Defaults to first docstring line.
        kind: Capability kind. Auto-inferred if omitted.
        tags: Tags for categorization.
        risk: Risk level: low, medium, high, critical.
        approval: Approval requirement: none, optional, required.
        destructive: Whether the action is destructive.
        safe: Shorthand for low-risk, no-approval, non-destructive operations.
    """

    if risk is not None and risk not in _ALLOWED_RISK:
        raise ValueError(f"Invalid risk '{risk}'. Expected one of: {sorted(_ALLOWED_RISK)}")

    if approval is not None and approval not in _ALLOWED_APPROVAL:
        raise ValueError(
            f"Invalid approval '{approval}'. Expected one of: {sorted(_ALLOWED_APPROVAL)}"
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cap_name = (name or func.__name__).strip()
        if not cap_name:
            raise ValueError("Capability name cannot be empty")

        cap_desc = description
        if cap_desc is None:
            doc = inspect.getdoc(func) or ""
            cap_desc = doc.splitlines()[0].strip() if doc else f"Execute {cap_name}"

        cap_kind = kind or _infer_kind_from_name(cap_name)

        cap_risk = risk
        cap_approval = approval
        cap_destructive = destructive

        if safe:
            cap_risk = "low" if cap_risk is None else cap_risk
            cap_approval = "none" if cap_approval is None else cap_approval
            cap_destructive = False if cap_destructive is None else cap_destructive
        else:
            if cap_risk is None:
                cap_risk = _infer_risk_from_name(cap_name)
            if cap_destructive is None:
                cap_destructive = _infer_destructive_from_name(cap_name)
            if cap_approval is None:
                risk_to_approval = {
                    "low": "none",
                    "medium": "optional",
                    "high": "required",
                    "critical": "required",
                }
                cap_approval = risk_to_approval[cap_risk]

        cap_tags = _normalize_tags(tags)
        metadata_tags = [
            f"risk:{cap_risk}",
            f"approval:{cap_approval}",
        ]
        if cap_destructive:
            metadata_tags.append("destructive")

        for tag in metadata_tags:
            if tag not in cap_tags:
                cap_tags.append(tag)

        input_schema, output_schema = _generate_schema(func)

        capability_obj = Capability(
            name=cap_name,
            description=cap_desc,
            kind=cap_kind,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=cap_tags,
        )

        if cap_name in _REGISTERED_CAPABILITIES:
            raise ValueError(f"Capability '{cap_name}' is already registered")

        _REGISTERED_CAPABILITIES[cap_name] = capability_obj

        # Attach metadata to the function for introspection.
        func._aicp_capability = capability_obj  # type: ignore[attr-defined]
        func._aicp_risk = cap_risk  # type: ignore[attr-defined]
        func._aicp_approval = cap_approval  # type: ignore[attr-defined]
        func._aicp_destructive = cap_destructive  # type: ignore[attr-defined]

        return func

    return decorator
