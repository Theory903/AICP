"""AICP Executor.

Default executor implementation with policy enforcement, approval flow,
streaming support, and normalized execution results.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, cast

from jsonschema import Draft202012Validator

from .approval import ApprovalContext, ResumedExecution
from .approval_service import ApprovalService
from .capability import Capability
from .interfaces.capability_provider import CapabilityProvider
from .interfaces.executor import ExecutionError, ExecutionResult, ExecutionStatus, Executor
from .interfaces.policy_engine import PolicyDecision, PolicyEffect, PolicyEngine


class AicpExecutor(Executor):
    """Default AICP executor with policy enforcement.

    Responsibilities:
    - capability lookup
    - policy evaluation
    - approval / HITL handling
    - execution dispatch
    - result normalization
    - streaming fallback support
    """

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
        default_timeout_seconds: float | None = 35.0,
    ) -> None:
        self._provider = capability_provider
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._default_timeout_seconds = default_timeout_seconds

    @property
    def executor_type(self) -> str:
        return "aicp"

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a capability with policy enforcement."""
        started_at = time.perf_counter()
        safe_context = dict(context or {})

        try:
            preflight = await self._preflight(
                capability_name=capability_name,
                arguments=arguments,
                context=safe_context,
                started_at=started_at,
            )
            if isinstance(preflight, ExecutionResult):
                return preflight

            capability, _decision = preflight

            execution_context = self._build_execution_context(
                capability=capability,
                capability_name=capability_name,
                context=safe_context,
            )

            result_data = await self._execute_provider_call(
                capability_name,
                arguments,
                execution_context,
                timeout_seconds=self._resolve_timeout_seconds(safe_context),
            )

            return self._success_result(
                capability=capability,
                data=result_data,
                execution_time_ms=self._elapsed_ms(started_at),
            )
        except ExecutionError as exc:
            return self._error_result(
                capability_name=capability_name,
                error_code=exc.error_code or "execution_failed",
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(started_at),
            )
        except TimeoutError:
            return self._error_result(
                capability_name=capability_name,
                error_code="timeout",
                error_message="Capability execution timed out.",
                execution_time_ms=self._elapsed_ms(started_at),
            )
        except Exception as exc:
            return self._error_result(
                capability_name=capability_name,
                error_code="execution_failed",
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(started_at),
            )

    async def execute_many(
        self,
        requests: list[dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Execute multiple capabilities sequentially."""
        results: list[ExecutionResult] = []
        for request in requests:
            result = await self.execute(
                capability_name=request["capability_name"],
                arguments=request.get("arguments", {}),
                context=request.get("context"),
            )
            results.append(result)
        return results

    async def execute_after_approval(
        self,
        approval_request_id: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a capability after approval has been granted."""
        if self._approval_service is None:
            return self._error_result(
                capability_name="approval",
                error_code="approval_not_configured",
                error_message="Approval service not configured",
                execution_time_ms=0.0,
            )

        approval_request = await self._get_approval_request(approval_request_id)
        if approval_request is None:
            return self._error_result(
                capability_name="approval",
                error_code="approval_not_found",
                error_message=f"Approval request not found: {approval_request_id}",
                execution_time_ms=0.0,
            )

        status_value = self._approval_status_value(approval_request)
        if status_value != "approved":
            return self._error_result(
                capability_name=self._approval_capability_name(approval_request),
                error_code="approval_denied",
                error_message=(
                    f"Approval request is not approved: {status_value}"
                ),
                execution_time_ms=0.0,
            )

        resumed_execution = ResumedExecution(
            approval_id=approval_request_id,
            workflow_id=self._approval_workflow_id(approval_request),
            authorized_by=self._approval_decided_by(approval_request),
            authorized_at=self._approval_decided_at(approval_request),
        )

        started_at = time.perf_counter()
        resumed_context = dict(context or {})
        resumed_context["approval_request_id"] = approval_request_id

        try:
            preflight = await self._preflight(
                capability_name=self._approval_capability_name(approval_request),
                arguments=self._approval_arguments(approval_request),
                context=resumed_context,
                started_at=started_at,
                resumed_execution=resumed_execution,
            )
            if isinstance(preflight, ExecutionResult):
                return preflight

            capability, _decision = preflight
            execution_context = self._build_execution_context(
                capability=capability,
                capability_name=capability.name,
                context=resumed_context,
                resumed_execution=resumed_execution,
            )
            result_data = await self._execute_provider_call(
                capability.name,
                self._approval_arguments(approval_request),
                execution_context,
                timeout_seconds=self._resolve_timeout_seconds(resumed_context),
            )
            return self._success_result(
                capability=capability,
                data=result_data,
                execution_time_ms=self._elapsed_ms(started_at),
            )
        except ExecutionError as exc:
            return self._error_result(
                capability_name=self._approval_capability_name(approval_request),
                error_code=exc.error_code or "execution_failed",
                error_message=str(exc),
                execution_time_ms=self._elapsed_ms(started_at),
            )
        except TimeoutError:
            return self._error_result(
                capability_name=self._approval_capability_name(approval_request),
                error_code="timeout",
                error_message="Capability execution timed out.",
                execution_time_ms=self._elapsed_ms(started_at),
            )

    async def execute_streaming(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a capability with streaming support."""
        started_at = time.perf_counter()
        safe_context = dict(context or {})

        yield {"type": "start", "capability": capability_name}

        try:
            preflight = await self._preflight(
                capability_name=capability_name,
                arguments=arguments,
                context=safe_context,
                started_at=started_at,
            )
            if isinstance(preflight, ExecutionResult):
                yield {
                    "type": "error",
                    "error": preflight.error,
                    "error_code": preflight.error_code,
                    "metadata": preflight.model_dump(exclude_none=True),
                }
                return

            capability, _decision = preflight

            execution_context = self._build_execution_context(
                capability=capability,
                capability_name=capability_name,
                context=safe_context,
            )

            if hasattr(self._provider, "execute_streaming"):
                streaming_provider = cast(Any, self._provider)
                async for chunk in streaming_provider.execute_streaming(
                    capability_name,
                    arguments,
                    execution_context,
                ):
                    yield chunk
            else:
                result = await self.execute(capability_name, arguments, safe_context)
                yield {
                    "type": "result",
                    "status": result.status.value,
                    "data": result.data,
                    "metadata": result.model_dump(exclude_none=True),
                }
        except Exception as exc:
            yield {
                "type": "error",
                "error": str(exc),
                "error_code": "execution_failed",
            }
        finally:
            yield {"type": "end"}

    async def _preflight(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
        started_at: float,
        resumed_execution: ResumedExecution | None = None,
    ) -> tuple[Capability, PolicyDecision] | ExecutionResult:
        """Run centralized pre-execution checks."""
        capability = await self._provider.get_capability(capability_name)
        if capability is None:
            return self._error_result(
                capability_name=capability_name,
                error_code="capability_not_found",
                error_message=f"Capability not found: {capability_name}",
                execution_time_ms=self._elapsed_ms(started_at),
            )

        if resumed_execution is not None:
            return capability, PolicyDecision(
                effect=PolicyEffect.ALLOW,
                reason=f"Approved resume via {resumed_execution.approval_id}",
            )

        if self._policy_engine is None:
            default_decision = PolicyDecision(
                effect=PolicyEffect.ALLOW,
                reason="No policy engine configured",
            )
            return capability, default_decision

        policy_context = self._build_policy_context(capability, context)

        decision = await self._policy_engine.evaluate(
            capability_name,
            arguments,
            policy_context,
        )

        if decision.effect == PolicyEffect.DENY:
            return self._error_result(
                capability_name=capability_name,
                error_code="policy_denied",
                error_message=decision.reason or "Execution denied by policy",
                execution_time_ms=self._elapsed_ms(started_at),
            )

        if decision.effect == PolicyEffect.LIMIT:
            return self._error_result(
                capability_name=capability_name,
                error_code="rate_limited",
                error_message=decision.reason or "Rate limit exceeded",
                execution_time_ms=self._elapsed_ms(started_at),
            )

        if decision.effect == PolicyEffect.ASK:
            return await self._approval_or_confirmation_result(
                capability=capability,
                capability_name=capability_name,
                arguments=arguments,
                context=context,
                decision=decision,
                started_at=started_at,
            )

        return capability, decision

    def _build_policy_context(
        self,
        capability: Capability,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build context payload used during policy evaluation."""
        policy_context = dict(context)
        policy_context.setdefault("kind", capability.kind.value)
        policy_context.setdefault(
            "is_destructive",
            bool(getattr(capability, "is_destructive", False)),
        )
        policy_context.setdefault("tags", list(getattr(capability, "tags", []) or []))

        provider = getattr(capability, "provider", None)
        if provider is not None:
            provider_name = getattr(provider, "name", None)
            provider_type = getattr(provider, "type", None)
            if provider_name:
                policy_context.setdefault("provider", provider_name)
            if provider_type:
                policy_context.setdefault("provider_type", provider_type)

        return policy_context

    def _build_execution_context(
        self,
        capability: Capability,
        capability_name: str,
        context: dict[str, Any],
        resumed_execution: ResumedExecution | None = None,
    ) -> dict[str, Any]:
        """Build context payload passed into execution."""
        execution_context = dict(context)
        execution_context["capability_name"] = capability_name
        execution_context["kind"] = capability.kind.value
        execution_context["is_destructive"] = bool(
            getattr(capability, "is_destructive", False)
        )
        execution_context["tags"] = list(getattr(capability, "tags", []) or [])
        if resumed_execution is not None:
            execution_context["resumed_execution"] = resumed_execution.to_dict()
        return execution_context

    async def _execute_provider_call(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        execution_context: dict[str, Any],
        *,
        timeout_seconds: float | None,
    ) -> Any:
        execution = self._provider.execute(capability_name, arguments, execution_context)
        if timeout_seconds is None:
            return await execution
        return await asyncio.wait_for(execution, timeout=timeout_seconds)

    def _resolve_timeout_seconds(self, context: dict[str, Any]) -> float | None:
        timeout_value = context.get("execution_timeout_seconds", self._default_timeout_seconds)
        if timeout_value is None:
            return None
        try:
            timeout_seconds = float(timeout_value)
        except (TypeError, ValueError):
            return self._default_timeout_seconds
        return timeout_seconds if timeout_seconds > 0 else self._default_timeout_seconds

    def _approval_status_value(self, approval_request: Any) -> str:
        status = (
            approval_request.get("status")
            if isinstance(approval_request, dict)
            else getattr(approval_request, "status", None)
        )
        status = getattr(status, "value", status)
        return str(status or "").strip().lower()

    def _approval_capability_name(self, approval_request: Any) -> str:
        if isinstance(approval_request, dict):
            return str(approval_request.get("capability_name") or "approval")
        return str(getattr(approval_request, "capability_name", "approval"))

    def _approval_arguments(self, approval_request: Any) -> dict[str, Any]:
        if isinstance(approval_request, dict):
            modified = approval_request.get("modified_arguments")
            original = approval_request.get("arguments")
        else:
            modified = getattr(approval_request, "modified_arguments", None)
            original = getattr(approval_request, "arguments", None)
        selected = modified if isinstance(modified, dict) else original
        return dict(selected or {})

    def _approval_workflow_id(self, approval_request: Any) -> str | None:
        value = (
            approval_request.get("workflow_id")
            if isinstance(approval_request, dict)
            else getattr(approval_request, "workflow_id", None)
        )
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _approval_decided_by(self, approval_request: Any) -> str | None:
        value = (
            approval_request.get("decided_by")
            if isinstance(approval_request, dict)
            else getattr(approval_request, "decided_by", None)
        )
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _approval_decided_at(self, approval_request: Any) -> datetime | None:
        value = (
            approval_request.get("decided_at")
            if isinstance(approval_request, dict)
            else getattr(approval_request, "decided_at", None)
        )
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    async def _get_approval_request(self, approval_request_id: str) -> dict[str, Any] | None:
        """Get approval request - works with both core and runtime approval services."""
        approval_service = self._approval_service
        if approval_service is None:
            return None

        try:
            from aicp_runtime.services.approvals import ApprovalService as RuntimeApprovalService
            if isinstance(approval_service, RuntimeApprovalService):
                result: Any = await approval_service.get_approval(approval_request_id)
                return result
        except ImportError:
            pass

        if hasattr(approval_service, "get_request"):
            result: Any = await approval_service.get_request(approval_request_id)
            if isinstance(result, dict):
                return result
            if result is not None and hasattr(result, "to_dict"):
                return result.to_dict()
            return None
        return None

    async def _approval_or_confirmation_result(
        self,
        capability: Capability,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
        decision: PolicyDecision,
        started_at: float,
    ) -> ExecutionResult:
        """Handle ASK effect via approval flow or plain confirmation fallback."""
        if self._approval_service is not None:
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            intent_hash = self._generate_intent_hash(capability_name, arguments, context)

            existing_approved = await self._check_existing_approval(
                capability_name, arguments, context
            )
            if existing_approved is not None:
                approved_execution_id = existing_approved.get("execution_id")
                return ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    error=decision.reason,
                    error_code="requires_approval",
                    execution_time_ms=self._elapsed_ms(started_at),
                    approval_request_id=existing_approved.get("id"),
                    approval_status="approved",
                    next={
                        "action": "resume_approved",
                        "approval_request_id": existing_approved.get("id"),
                        "execution_id": approved_execution_id,
                        "capability": capability_name,
                        "hint": "Already approved - execution can be resumed",
                    },
                    can_continue=True,
                )

            approval_request = await self._approval_service.create_approval_request(
                capability_name=capability_name,
                arguments=arguments,
                requester=ApprovalContext(
                    requester_id=context.get("requester_id"),
                    requester_email=context.get("requester_email"),
                    requester_role=context.get("requester_role"),
                    tenant_id=context.get("tenant_id"),
                    session_id=context.get("session_id"),
                    ip_address=context.get("ip_address"),
                    user_agent=context.get("user_agent"),
                ),
                execution_id=execution_id,
                workflow_id=context.get("workflow_id"),
            )
            approval_request_id = self._approval_request_id(approval_request)

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                error=decision.reason,
                error_code="requires_approval",
                execution_time_ms=self._elapsed_ms(started_at),
                approval_request_id=approval_request_id,
                approval_status="pending",
                next={
                    "action": "await_approval",
                    "approval_request_id": approval_request_id,
                    "execution_id": execution_id,
                    "intent_hash": intent_hash,
                    "capability": capability_name,
                    "hint": decision.reason or "Approval required before execution",
                },
                can_continue=True,
            )

        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            error=decision.reason,
            error_code="requires_confirmation",
            execution_time_ms=self._elapsed_ms(started_at),
            next={
                "action": "confirm",
                "capability": capability_name,
                "arguments": arguments,
                "hint": decision.reason or "Confirmation required before execution",
            },
            can_continue=True,
        )

    def _approval_request_id(self, approval_request: Any) -> str:
        """Extract an approval request ID from object or dict responses."""
        if isinstance(approval_request, dict):
            approval_id = approval_request.get("id")
        else:
            approval_id = getattr(approval_request, "id", None)

        if isinstance(approval_id, str) and approval_id.strip():
            return approval_id

        raise ValueError("Approval service returned a request without a valid id")

    def _success_result(
        self,
        capability: Capability,
        data: Any,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Create a success result with continuation and rendering hints."""
        validation_issue = self._validate_output(capability, data)
        validation_mode = str(
            getattr(capability, "output_validation_mode", "") or "disabled"
        )
        if validation_issue is not None and validation_mode == "strict":
            return self._error_result(
                capability_name=capability.name,
                error_code="output_validation_failed",
                error_message=validation_issue["message"],
                execution_time_ms=execution_time_ms,
            )

        continuation = getattr(capability, "continuation", None)
        render = getattr(capability, "render", None)

        next_action = "complete"
        next_capability = None
        next_arguments = None
        next_hint = None
        next_poll_after_ms = None
        next_poll_url = None
        continuation_hint = None
        can_continue = True

        if continuation is not None:
            next_hint = getattr(continuation, "next_hint", None)
            next_capabilities = getattr(continuation, "next_capabilities", None) or []
            continuation_allowed = bool(getattr(continuation, "can_continue", False))

            if continuation_allowed and next_capabilities:
                next_action = "continue"
                next_capability = next_capabilities[0]
            elif continuation_allowed:
                next_action = "continue"

        polling_metadata = self._polling_metadata(data)
        if polling_metadata is not None:
            next_action = "wait"
            next_capability = polling_metadata.get("capability") or next_capability
            next_arguments = polling_metadata.get("arguments")
            next_hint = next_hint or polling_metadata.get("hint")
            next_poll_after_ms = polling_metadata.get("poll_after_ms")
            next_poll_url = polling_metadata.get("poll_url")
            continuation_hint = next_hint

        format_hint = getattr(render, "format", None) if render is not None else None

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data=data,
            execution_time_ms=execution_time_ms,
            next={
                "action": next_action,
                "capability": next_capability,
                "arguments": next_arguments,
                "hint": next_hint,
                "poll_after_ms": next_poll_after_ms,
                "poll_url": next_poll_url,
            },
            warnings=[validation_issue] if validation_issue is not None else None,
            format_hint=format_hint,
            can_continue=can_continue,
            continuation_hint=continuation_hint,
        )

    def _polling_metadata(self, data: Any) -> dict[str, Any] | None:
        if not isinstance(data, dict):
            return None
        metadata = data.get("_aicp")
        if not isinstance(metadata, dict):
            return None
        polling = metadata.get("polling")
        return polling if isinstance(polling, dict) else None

    def _error_result(
        self,
        capability_name: str,
        error_code: str,
        error_message: str,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Create a normalized error result with next-action guidance."""
        next_action = self._get_next_action(error_code)
        fix_hint = self._get_fix_hint(error_code, capability_name)

        status = (
            ExecutionStatus.RATE_LIMITED
            if error_code == "rate_limited"
            else ExecutionStatus.TIMEOUT
            if error_code == "timeout"
            else ExecutionStatus.UNAVAILABLE
            if error_code in {"server_error", "connectivity_error", "circuit_open"}
            else ExecutionStatus.FAILURE
        )

        return ExecutionResult(
            status=status,
            error=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            next={
                "action": next_action,
                "capability": None if next_action == "list" else capability_name,
                "hint": fix_hint,
            },
            can_continue=True,
        )

    def _get_next_action(self, error_code: str) -> str:
        """Map error codes to logical agent next actions."""
        mapping = {
            "capability_not_found": "list",
            "policy_denied": "inspect",
            "rate_limited": "wait",
            "requires_approval": "await_approval",
            "requires_confirmation": "confirm",
            "execution_failed": "retry",
            "authentication_failed": "inspect",
            "missing_session": "attach_session",
            "needs_reauthentication": "reauthenticate",
            "provider_session_mismatch": "attach_session",
            "tenant_session_mismatch": "select_context",
            "output_validation_failed": "inspect",
            "resource_not_found": "inspect",
            "validation_failed": "retry_with_fixes",
            "server_error": "retry",
            "connectivity_error": "retry",
            "timeout": "retry",
            "circuit_open": "wait",
            "invalid_arguments": "inspect",
            "approval_not_configured": "inspect",
            "approval_not_found": "inspect",
            "approval_denied": "stop",
        }
        return mapping.get(error_code, "retry")

    def _get_fix_hint(self, error_code: str, capability_name: str) -> str:
        """Get fix hint based on error code."""
        hints = {
            "capability_not_found": (
                f"Check if '{capability_name}' is registered. "
                "Use list_capabilities() to inspect available capabilities."
            ),
            "policy_denied": (
                "Review the policy that denied this execution. "
                "Check permissions, auth context, and policy rules."
            ),
            "rate_limited": "Too many requests. Wait and retry later.",
            "requires_confirmation": (
                "This capability requires confirmation before execution."
            ),
            "requires_approval": (
                "This capability requires approval before execution."
            ),
            "execution_failed": (
                "Check the capability implementation, inputs, and downstream service health."
            ),
            "authentication_failed": (
                "Check auth configuration, credentials, and provider-specific headers."
            ),
            "missing_session": (
                "Attach a compatible session before retrying this capability."
            ),
            "needs_reauthentication": (
                "Refresh or recreate the session before retrying this capability."
            ),
            "provider_session_mismatch": (
                "Use a session created for the capability's provider."
            ),
            "tenant_session_mismatch": (
                "Use a session scoped to the requested tenant or switch tenant context."
            ),
            "output_validation_failed": (
                "Inspect the provider response and update the declared "
                "output schema or execution adapter."
            ),
            "resource_not_found": (
                "Check the target resource identifier or backend route mapping."
            ),
            "validation_failed": (
                "Review the backend validation error and retry with corrected inputs."
            ),
            "server_error": "The backend failed. Retry once, then inspect service health.",
            "connectivity_error": "The backend could not be reached. Check network and base URL.",
            "timeout": "The backend timed out. Retry later or reduce request complexity.",
            "circuit_open": (
                "The backend is failing repeatedly. Wait for the circuit breaker to reset."
            ),
            "invalid_arguments": (
                "Review the capability input schema and supply valid arguments."
            ),
            "approval_not_configured": (
                "Configure ApprovalService to support HITL approval flows."
            ),
            "approval_not_found": (
                "Check the approval request ID and ensure it still exists."
            ),
            "approval_denied": (
                "Approval is not in an approved state. Review the approval decision."
            ),
        }
        return hints.get(error_code, "Review the error and retry with corrected input.")

    def _validate_output(
        self,
        capability: Capability,
        data: Any,
    ) -> dict[str, Any] | None:
        validation_mode = str(
            getattr(capability, "output_validation_mode", "") or "disabled"
        )
        if validation_mode == "disabled":
            return None

        output_schema = getattr(capability, "output_schema", None)
        if output_schema is None:
            return None

        schema = output_schema.model_dump(exclude_none=True, mode="json")
        if not isinstance(schema, dict) or not schema:
            return None

        if self._matches_normalized_binary_output(schema, data):
            return None

        errors = list(Draft202012Validator(schema).iter_errors(data))
        if not errors:
            return None

        first_error = errors[0]
        path = ".".join(str(part) for part in first_error.absolute_path)
        path_text = path or "$"
        return {
            "code": "output_validation_warning",
            "message": (
                "Execution result did not match declared output schema: "
                f"{first_error.message} at {path_text}."
            ),
            "details": {
                "path": path_text,
                "validator": str(first_error.validator),
            },
        }

    def _matches_normalized_binary_output(self, schema: dict[str, Any], data: Any) -> bool:
        if schema.get("type") != "string" or schema.get("format") != "binary":
            return False
        if not isinstance(data, dict):
            return False
        file_payload = data.get("file")
        if not isinstance(file_payload, dict):
            return False
        content_base64 = file_payload.get("content_base64")
        return isinstance(content_base64, str) and bool(content_base64)

    def _elapsed_ms(self, started_at: float) -> float:
        """Calculate elapsed time in milliseconds."""
        return (time.perf_counter() - started_at) * 1000.0

    def _generate_intent_hash(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Generate a deterministic hash for the execution intent.

        This hash is used to identify when the same execution intent
        has been approved, allowing auto-resume after approval.
        """
        normalized_args = self._normalize_for_hashing(arguments or {})
        normalized_context = self._normalize_for_hashing({
            k: v for k, v in (context or {}).items()
            if k in {"tenant_id", "user_id", "session_id"}
        })

        hash_input = f"{capability_name}:{normalized_args}:{normalized_context}"
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]

    def _normalize_for_hashing(self, data: Any) -> str:
        """Normalize data for consistent hashing."""
        if isinstance(data, dict):
            normalized_items = sorted(
                (k, self._normalize_for_hashing(v)) for k, v in data.items()
            )
            return f"{{{','.join(f'{k}:{v}' for k, v in normalized_items)}}}"
        if isinstance(data, list):
            return f"[{','.join(self._normalize_for_hashing(item) for item in data)}]"
        if isinstance(data, str):
            return f'"{data}"'
        if isinstance(data, (int, float, bool)):
            return str(data).lower()
        if data is None:
            return "null"
        return f'"{str(data)}"'

    async def _check_existing_approval(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Check if there's an already approved execution for the same intent."""
        try:
            from aicp_runtime.services.approvals import ApprovalService as RuntimeApprovalService
            if isinstance(self._approval_service, RuntimeApprovalService):
                return await self._approval_service.find_approved_for_intent(
                    capability_name=capability_name,
                    arguments=arguments,
                    context=context,
                )
        except ImportError:
            pass
        return None
