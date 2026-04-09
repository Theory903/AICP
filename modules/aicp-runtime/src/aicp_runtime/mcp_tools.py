from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from aicp.capability import Capability
from aicp.interfaces.executor import ExecutionResult
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService


ToolHandler = Callable[
    [dict[str, Any], ExecutionService | None, DiscoveryService],
    Awaitable[dict[str, Any]],
]


@dataclass(frozen=True, slots=True)
class AicpMcpToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


class _BaseArgsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ArgsModelT = TypeVar("ArgsModelT", bound=_BaseArgsModel)


class AicpSetupArgs(_BaseArgsModel):
    pass


class AicpListCapabilitiesArgs(_BaseArgsModel):
    plugin: str | None = None
    type: str | None = None

    @field_validator("plugin", "type", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class AicpGetSchemaArgs(_BaseArgsModel):
    capability_name: str | None = None

    @field_validator("capability_name", mode="before")
    @classmethod
    def _normalize_capability_name(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("capability_name is required.")
        return normalized


class AicpRunArgs(_BaseArgsModel):
    capability_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] | None = None

    @field_validator("capability_name", mode="before")
    @classmethod
    def _normalize_capability_name(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("capability_name is required.")
        return normalized

    @field_validator("arguments", mode="before")
    @classmethod
    def _validate_arguments(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("arguments must be an object.")
        return value

    @field_validator("context", mode="before")
    @classmethod
    def _validate_context(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("context must be an object.")
        return value


def _error(message: str, code: str) -> dict[str, Any]:
    return {"error": message, "code": code}


def _coerce_args(args: dict[str, Any] | Any, model: type[ArgsModelT]) -> ArgsModelT:
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object.")
    return model.model_validate(args)


def _validation_error_dict(exc: ValidationError) -> dict[str, Any]:
    issue = exc.errors()[0] if exc.errors() else {}
    message = str(
        issue.get("ctx", {}).get("error") or issue.get("msg") or "Invalid arguments."
    )
    return _error(message, "invalid_arguments")


def _serialize_capability_summary(capability: dict[str, Any]) -> dict[str, Any]:
    provider = capability.get("provider")
    provider_name = None
    if isinstance(provider, dict):
        provider_name = provider.get("name")
    elif isinstance(provider, str):
        provider_name = provider

    return {
        "name": capability.get("name"),
        "description": capability.get("description") or "",
        "kind": capability.get("kind"),
        "input_schema": capability.get("input_schema") or {"type": "object"},
        "output_schema": capability.get("output_schema") or {"type": "object"},
        "tags": capability.get("tags") or [],
        "provider": provider_name,
    }


def _approval_required(capability: Capability) -> bool:
    if capability.policy is not None:
        return True
    return capability.is_destructive


def _error_codes(capability: Capability) -> list[str]:
    raw_errors = getattr(capability, "errors", None)
    if not isinstance(raw_errors, list):
        return []
    codes: list[str] = []
    for item in raw_errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if code and code not in codes:
            codes.append(code)
    return codes


def _get_capability_provider(discovery_service: DiscoveryService) -> Any:
    return getattr(discovery_service, "_provider", None)


async def aicp_setup_handler(
    args: dict[str, Any],
    execution_service: ExecutionService | None,
    discovery_service: DiscoveryService,
) -> dict[str, Any]:
    del execution_service
    try:
        _coerce_args(args, AicpSetupArgs)
    except ValidationError as exc:
        return _validation_error_dict(exc)
    except ValueError as exc:
        return _error(str(exc), "invalid_arguments")

    missing_keys = [
        key
        for key in ("AICP_API_KEY", "AICP_MASTER_KEY")
        if not str(os.getenv(key, "")).strip()
    ]

    try:
        await discovery_service.discover()
    except Exception as exc:
        return _error(str(exc), "registry_unhealthy")

    if missing_keys:
        return {
            "status": "needs_setup",
            "missing_keys": missing_keys,
            "setup_instructions": (
                "Export the missing environment variables and ensure the AICP "
                "capability registry is reachable."
            ),
        }

    return {
        "status": "ready",
        "missing_keys": [],
        "setup_instructions": "AICP is configured and the capability registry is healthy.",
    }


async def aicp_list_capabilities_handler(
    args: dict[str, Any],
    execution_service: ExecutionService | None,
    discovery_service: DiscoveryService,
) -> dict[str, Any]:
    del execution_service
    try:
        parsed = _coerce_args(args, AicpListCapabilitiesArgs)
    except ValidationError as exc:
        return _validation_error_dict(exc)
    except ValueError as exc:
        return _error(str(exc), "invalid_arguments")

    capability_payloads: list[dict[str, Any]]
    if parsed.plugin or parsed.type:
        query = " ".join(part for part in [parsed.plugin, parsed.type] if part)
        ranked = await discovery_service.rank_capabilities(query=query, limit=100)
        capability_payloads = []
        for item in ranked:
            if not isinstance(item, dict):
                continue
            capability = item.get("capability")
            if isinstance(capability, dict):
                capability_payloads.append(capability)
    else:
        discovered = await discovery_service.discover()
        raw_capabilities = discovered.get("capabilities")
        capability_payloads = (
            raw_capabilities if isinstance(raw_capabilities, list) else []
        )

    return {
        "capabilities": [
            _serialize_capability_summary(capability)
            for capability in capability_payloads
            if isinstance(capability, dict)
        ]
    }


async def aicp_get_schema_handler(
    args: dict[str, Any],
    execution_service: ExecutionService | None,
    discovery_service: DiscoveryService,
) -> dict[str, Any]:
    del execution_service
    try:
        parsed = _coerce_args(args, AicpGetSchemaArgs)
    except ValidationError as exc:
        return _validation_error_dict(exc)
    except ValueError as exc:
        return _error(str(exc), "invalid_arguments")

    provider = _get_capability_provider(discovery_service)
    if provider is None or not hasattr(provider, "get_capability"):
        return _error("Capability provider is unavailable.", "service_unavailable")
    if not parsed.capability_name:
        return _error("capability_name is required.", "invalid_arguments")

    capability = await provider.get_capability(parsed.capability_name)
    if capability is None:
        return _error(
            f"Capability not found: {parsed.capability_name}",
            "capability_not_found",
        )

    return {
        "name": capability.name,
        "description": capability.description,
        "input_schema": capability.input_schema.model_dump(mode="json"),
        "output_schema": capability.output_schema.model_dump(mode="json"),
        "tags": list(capability.tags),
        "error_codes": _error_codes(capability),
        "approval_required": _approval_required(capability),
    }


def _execution_id(result: ExecutionResult) -> str | None:
    value = getattr(result, "execution_id", None)
    if isinstance(value, str) and value.strip():
        return value
    next_payload = getattr(result, "next", None)
    if isinstance(next_payload, dict):
        next_value = next_payload.get("execution_id")
        if isinstance(next_value, str) and next_value.strip():
            return next_value
    return None


async def aicp_run_handler(
    args: dict[str, Any],
    execution_service: ExecutionService | None,
    discovery_service: DiscoveryService,
) -> dict[str, Any]:
    del discovery_service
    try:
        parsed = _coerce_args(args, AicpRunArgs)
    except ValidationError as exc:
        return _validation_error_dict(exc)
    except ValueError as exc:
        return _error(str(exc), "invalid_arguments")

    if execution_service is None:
        return _error("Execution service is unavailable.", "service_unavailable")

    try:
        result = await execution_service.execute(
            parsed.capability_name,
            parsed.arguments,
            parsed.context,
        )
    except Exception as exc:
        return _error(str(exc), "execution_failed")

    return {
        "execution_id": _execution_id(result),
        "status": result.status.value,
        "data": result.data,
        "error": (
            {"message": result.error, "code": result.error_code}
            if result.error is not None
            else None
        ),
        "allowed_next_actions": list(result.allowed_next_actions),
        "rendered": result.rendered,
    }


def get_canonical_mcp_tools() -> list[AicpMcpToolDef]:
    return [
        AicpMcpToolDef(
            name="aicp_setup",
            description="Initialize or verify AICP MCP configuration.",
            input_schema=AicpSetupArgs.model_json_schema(),
            handler=aicp_setup_handler,
        ),
        AicpMcpToolDef(
            name="aicp_list_capabilities",
            description="List available AICP capabilities with optional filters.",
            input_schema=AicpListCapabilitiesArgs.model_json_schema(),
            handler=aicp_list_capabilities_handler,
        ),
        AicpMcpToolDef(
            name="aicp_get_schema",
            description="Fetch typed schemas and metadata for one AICP capability.",
            input_schema=AicpGetSchemaArgs.model_json_schema(),
            handler=aicp_get_schema_handler,
        ),
        AicpMcpToolDef(
            name="aicp_run",
            description="Execute an AICP capability with validated input.",
            input_schema=AicpRunArgs.model_json_schema(),
            handler=aicp_run_handler,
        ),
    ]


__all__ = ["AicpMcpToolDef", "get_canonical_mcp_tools"]
