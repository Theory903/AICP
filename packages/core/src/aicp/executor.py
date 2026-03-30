"""AICP Executor.

Default executor implementation with policy enforcement, approval flow,
streaming support, and normalized execution results.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any, cast

from .approval import ApprovalContext
from .approval_service import ApprovalService
from .capability import Capability
from .interfaces.capability_provider import CapabilityProvider
from .interfaces.executor import ExecutionResult, ExecutionStatus, Executor
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
    ) -> None:
        self._provider = capability_provider
        self._policy_engine = policy_engine
        self._approval_service = approval_service

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

            result_data = await self._provider.execute(
                capability_name,
                arguments,
                execution_context,
            )

            return self._success_result(
                capability=capability,
                data=result_data,
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

        approval_request = await self._approval_service.get_request(approval_request_id)
        if approval_request is None:
            return self._error_result(
                capability_name="approval",
                error_code="approval_not_found",
                error_message=f"Approval request not found: {approval_request_id}",
                execution_time_ms=0.0,
            )

        if approval_request.status.value != "approved":
            return self._error_result(
                capability_name=approval_request.capability_name,
                error_code="approval_denied",
                error_message=(
                    f"Approval request is not approved: {approval_request.status.value}"
                ),
                execution_time_ms=0.0,
            )

        resumed_context = dict(context or {})
        resumed_context["_approval_granted"] = True
        resumed_context["approval_request_id"] = approval_request_id

        return await self.execute(
            capability_name=approval_request.capability_name,
            arguments=approval_request.arguments,
            context=resumed_context,
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
            approval_granted = bool(context.get("_approval_granted"))
            if not approval_granted:
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
    ) -> dict[str, Any]:
        """Build context payload passed into execution."""
        execution_context = dict(context)
        execution_context["capability_name"] = capability_name
        execution_context["kind"] = capability.kind.value
        execution_context["is_destructive"] = bool(
            getattr(capability, "is_destructive", False)
        )
        execution_context["tags"] = list(getattr(capability, "tags", []) or [])
        return execution_context

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

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                error=decision.reason,
                error_code="requires_approval",
                execution_time_ms=self._elapsed_ms(started_at),
                approval_request_id=approval_request.id,
                approval_status="pending",
                next={
                    "action": "await_approval",
                    "approval_request_id": approval_request.id,
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

    def _success_result(
        self,
        capability: Capability,
        data: Any,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Create a success result with continuation and rendering hints."""
        continuation = getattr(capability, "continuation", None)
        render = getattr(capability, "render", None)

        next_action = "complete"
        next_capability = None
        next_hint = None
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

        format_hint = getattr(render, "format", None) if render is not None else None

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data=data,
            execution_time_ms=execution_time_ms,
            next={
                "action": next_action,
                "capability": next_capability,
                "hint": next_hint,
            },
            format_hint=format_hint,
            can_continue=can_continue,
        )

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

    def _elapsed_ms(self, started_at: float) -> float:
        """Calculate elapsed time in milliseconds."""
        return (time.perf_counter() - started_at) * 1000.0