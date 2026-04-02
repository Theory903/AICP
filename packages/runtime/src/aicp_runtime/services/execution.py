"""Execution service for the runtime package."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, cast

from aicp.capability import Capability
from aicp.executor import AicpExecutor
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.executor import ExecutionError, ExecutionResult
from aicp.interfaces.policy_engine import PolicyEngine
from aicp.interfaces.workflow_runtime import utc_now_rfc3339

from aicp_runtime.persistence.base import RuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.interactions import InteractionStateService
from aicp_runtime.services.sessions import SessionService

_REDACTED = "[redacted]"
_SENSITIVE_CONTEXT_KEYS = {
    "authorization",
    "client_secret",
    "cookie",
    "cookies",
    "csrf_tokens",
    "headers",
    "refresh_token",
    "set-cookie",
    "token",
    "tokens",
}


class ExecutionService:
    """Executes capabilities and stores execution records."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        runtime_store: RuntimeStore | None = None,
        approval_service: ApprovalService | None = None,
        interaction_service: InteractionStateService | None = None,
        session_service: SessionService | None = None,
    ):
        self._provider = capability_provider
        self._executor = AicpExecutor(capability_provider, policy_engine)
        self._store = runtime_store
        self._approvals = approval_service
        self._interactions = interaction_service
        self._sessions = session_service
        if approval_service is not None:
            cast(Any, self._executor)._approval_service = approval_service

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a capability and optionally persist the execution record."""
        capability_name = self._require_text(
            capability_name, field_name="capability_name"
        )
        safe_arguments = deepcopy(arguments or {})
        safe_context = deepcopy(context or {})
        capability = await self._provider.get_capability(capability_name)
        try:
            safe_context = await self._attach_interaction_context(safe_context)
            safe_context = await self._attach_session_context(capability, safe_context)
        except ExecutionError as exc:
            result = self._session_error_result(exc)
            if self._store is not None:
                await self._persist_execution_record(
                    capability_name=capability_name,
                    arguments=safe_arguments,
                    context=safe_context,
                    result=result,
                )
            return result

        result = await self._executor.execute(
            capability_name,
            safe_arguments,
            safe_context,
        )

        if self._store is not None:
            await self._persist_execution_record(
                capability_name=capability_name,
                arguments=safe_arguments,
                context=safe_context,
                result=result,
            )

        await self._record_interaction_result(
            capability_name=capability_name,
            context=safe_context,
            result=result,
        )

        return result

    async def get_execution_record(self, execution_id: str) -> dict[str, Any] | None:
        """Load a persisted execution record by ID."""
        execution_id = self._require_text(execution_id, field_name="execution_id")
        if self._store is None:
            return None
        record = await self._store.get_execution_record(execution_id)
        return deepcopy(record) if record is not None else None

    async def resume_execution(
        self,
        execution_id: str,
        approval_request_id: str,
    ) -> ExecutionResult:
        """Resume an execution after approval has been granted."""
        execution_id = self._require_text(execution_id, field_name="execution_id")
        approval_request_id = self._require_text(approval_request_id, field_name="approval_request_id")

        resolved_execution_id = await self._resolve_execution_id(
            approval_request_id, execution_id
        )

        execution_record = await self.get_execution_record(resolved_execution_id)

        if execution_record is None and self._approvals is not None:
            approval = await self._approvals.get_approval(approval_request_id)
            if approval is not None:
                approval_args = approval.get("arguments") or {}
                approval_context = approval.get("context") or {}
                execution_record = {
                    "execution_id": resolved_execution_id,
                    "capability_name": approval.get("capability_name"),
                    "arguments": approval_args,
                    "context": approval_context,
                }

        if execution_record is None:
            raise ValueError(f"Execution not found: {resolved_execution_id}")

        capability_name = str(execution_record.get("capability_name") or "")
        if not capability_name:
            raise ValueError(f"Execution {execution_id} has no capability_name")

        context = execution_record.get("context") or {}

        resume_result = await self._executor.execute_after_approval(
            approval_request_id=approval_request_id,
            context=context,
        )

        await self._persist_execution_record(
            capability_name=capability_name,
            arguments=execution_record.get("arguments") or {},
            context=context,
            result=resume_result,
        )

        return resume_result

    async def list_execution_records(
        self,
        *,
        limit: int = 25,
        capability_name: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List persisted execution records for operator-facing inspection."""
        if self._store is None:
            return []

        records = await self._store.list_execution_records()
        capability_filter = self._normalize_optional_text(capability_name)
        status_filter = self._normalize_optional_text(status)

        if capability_filter is not None:
            records = [
                record
                for record in records
                if str(record.get("capability_name") or "").strip() == capability_filter
            ]

        if status_filter is not None:
            records = [
                record
                for record in records
                if str(record.get("status") or "").strip() == status_filter
            ]

        records.sort(key=lambda record: str(record.get("created_at") or ""), reverse=True)
        bounded_limit = max(1, min(limit, 100))
        return [deepcopy(record) for record in records[:bounded_limit]]

    async def _persist_execution_record(
        self,
        *,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
        result: ExecutionResult,
    ) -> None:
        """Persist a normalized execution record."""
        if self._store is None:
            return

        execution_id = f"exe_{uuid.uuid4().hex[:12]}"
        approval_request_id = getattr(result, "approval_request_id", None)
        if isinstance(approval_request_id, str) and approval_request_id.strip():
            execution_id = await self._resolve_execution_id(approval_request_id, execution_id)

        record = {
            "execution_id": execution_id,
            "capability_name": capability_name,
            "arguments": deepcopy(arguments),
            "context": self._sanitize_context_for_persistence(context),
            "result": self._serialize_result(result),
            "status": result.status.value,
            "created_at": utc_now_rfc3339(),
        }

        await self._store.save_execution_record(execution_id, record)

    async def _resolve_execution_id(
        self,
        approval_request_id: str,
        fallback_execution_id: str,
    ) -> str:
        """Reuse approval-linked execution ids when available."""
        if self._approvals is None:
            return fallback_execution_id

        approval = await self._approvals.get_approval(approval_request_id)
        linked_execution_id = (
            str((approval or {}).get("execution_id") or "").strip()
            if approval is not None
            else ""
        )
        return linked_execution_id or fallback_execution_id

    def _serialize_result(self, result: ExecutionResult) -> dict[str, Any]:
        """Serialize an execution result safely."""
        data = result.model_dump(mode="json", exclude_none=True)
        if not isinstance(data, dict):
            raise ValueError("Execution result did not serialize to an object")
        return data

    async def _attach_session_context(
        self,
        capability: Capability | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        auth_requirement = getattr(capability, "auth", None)
        requires_session = bool(
            auth_requirement is not None
            and getattr(auth_requirement, "requires_session", False)
        )

        session_id = context.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            if requires_session:
                raise ExecutionError(
                    "Capability requires a session_id in execution context.",
                    error_code="missing_session",
                )
            return context

        if self._sessions is None:
            raise ExecutionError(
                "Session service is not configured.",
                error_code="missing_session",
            )

        session = await self._sessions.get_session(session_id)
        if session is None:
            raise ExecutionError(
                f"Session not found: {session_id}",
                error_code="missing_session",
            )

        requested_tenant_id = str(context.get("tenant_id") or "").strip()
        session_tenant_id = str(session.get("tenant_id") or "").strip()
        if (
            requested_tenant_id
            and session_tenant_id
            and requested_tenant_id != session_tenant_id
        ):
            raise ExecutionError(
                (
                    f"Tenant mismatch: execution requested tenant '{requested_tenant_id}' "
                    f"but session is scoped to '{session_tenant_id}'."
                ),
                error_code="tenant_session_mismatch",
            )

        health_status = str(session.get("health_status") or "").strip().lower()
        if health_status in {"expired", "invalid"}:
            raise ExecutionError(
                "Session is expired or invalid and must be refreshed before use.",
                error_code="needs_reauthentication",
            )

        required_provider = None
        if auth_requirement is not None:
            required_provider = getattr(auth_requirement, "required_session_provider", None)
        if not required_provider and capability is not None:
            provider = getattr(capability, "provider", None)
            required_provider = getattr(provider, "name", None)

        required_provider_text = str(required_provider or "").strip()
        session_provider_text = str(session.get("provider_name") or "").strip()
        if (
            required_provider_text
            and session_provider_text
            and required_provider_text != session_provider_text
        ):
            raise ExecutionError(
                (
                    f"Capability requires session provider '{required_provider_text}' "
                    f"but received '{session_provider_text}'."
                ),
                error_code="provider_session_mismatch",
            )

        if (
            auth_requirement is not None
            and getattr(auth_requirement, "csrf_required", False)
            and not (session.get("csrf_tokens") or {})
        ):
            raise ExecutionError(
                "Capability requires a CSRF token in the attached session.",
                error_code="needs_reauthentication",
            )

        marked_session = await self._sessions.mark_used(session_id)
        if marked_session is not None:
            session = marked_session

        enriched = deepcopy(context)
        enriched["resolved_session"] = session
        if not enriched.get("tenant_id") and session.get("tenant_id"):
            enriched["tenant_id"] = session["tenant_id"]
        if not enriched.get("user_id") and session.get("user_id"):
            enriched["user_id"] = session["user_id"]
        return enriched

    async def _attach_interaction_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if self._interactions is None:
            return context

        interaction_id = context.get("interaction_id")
        if not isinstance(interaction_id, str) or not interaction_id.strip():
            return context

        interaction = await self._interactions.get_interaction(interaction_id)
        if interaction is None:
            raise ExecutionError(
                f"Interaction not found: {interaction_id}",
                error_code="not_found",
            )

        enriched = deepcopy(context)
        enriched["resolved_interaction"] = interaction
        if not enriched.get("session_id") and interaction.get("session_id"):
            enriched["session_id"] = interaction["session_id"]
        for key, value in (interaction.get("selected_context") or {}).items():
            enriched.setdefault(str(key), value)
        return enriched

    async def _record_interaction_result(
        self,
        *,
        capability_name: str,
        context: dict[str, Any],
        result: ExecutionResult,
    ) -> None:
        if self._interactions is None:
            return

        interaction_id = context.get("interaction_id")
        if not isinstance(interaction_id, str) or not interaction_id.strip():
            return

        await self._interactions.record_execution(
            interaction_id,
            capability_name=capability_name,
            result_summary={
                "status": result.status.value,
                "error_code": result.error_code,
                "next": deepcopy(result.next) if isinstance(result.next, dict) else {},
            },
        )

    def _session_error_result(self, exc: ExecutionError) -> ExecutionResult:
        next_payload = {
            "action": "attach_session",
            "message": "Attach a compatible session before retrying.",
        }
        if exc.error_code == "needs_reauthentication":
            next_payload = {
                "action": "reauthenticate",
                "message": "Refresh or recreate the session before retrying this capability.",
            }
        if exc.error_code == "provider_session_mismatch":
            next_payload = {
                "action": "attach_session",
                "message": "Attach a session for the correct provider before retrying.",
            }
        if exc.error_code == "tenant_session_mismatch":
            next_payload = {
                "action": "select_context",
                "message": "Use a session scoped to the requested tenant or switch tenant context.",
            }
        if exc.error_code == "not_found":
            next_payload = {
                "action": "inspect_context",
                "message": "Verify referenced runtime state before retrying.",
            }
        return ExecutionResult.failure(
            error=str(exc),
            error_code=exc.error_code,
            next=next_payload,
        )

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        """Require a non-empty text value."""
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        """Normalize optional text values for list filters."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _sanitize_context_for_persistence(
        self, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Drop attached runtime objects and redact sensitive auth material."""
        sanitized = deepcopy(context)
        sanitized.pop("resolved_session", None)
        sanitized.pop("resolved_interaction", None)
        sanitized_value = self._sanitize_value(sanitized)
        return sanitized_value if isinstance(sanitized_value, dict) else {}

    def _sanitize_value(self, value: Any) -> Any:
        """Recursively redact sensitive fields before persistence."""
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if key_text.strip().lower() in _SENSITIVE_CONTEXT_KEYS:
                    sanitized[key_text] = _REDACTED
                else:
                    sanitized[key_text] = self._sanitize_value(item)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        return deepcopy(value)
