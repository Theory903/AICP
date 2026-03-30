"""AICP Executor.

Default executor implementation with policy enforcement and result normalization.
"""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from aicp.capability import Capability
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.executor import ExecutionResult, ExecutionStatus, Executor
from aicp.interfaces.policy_engine import PolicyEffect, PolicyEngine

try:
    from aicp.approval import ApprovalContext
    from aicp.approval_service import ApprovalService

    APPROVAL_AVAILABLE = True
except ImportError:
    APPROVAL_AVAILABLE = False
    ApprovalService = None
    ApprovalContext = None


class AicpExecutor(Executor):
    """Default AICP executor with policy enforcement.

    Wraps a capability provider and adds:
    - Policy evaluation before execution
    - Approval (HITL) integration
    - Result normalization
    - Execution timing
    - Error handling with fix hints
    """

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
    ):
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
        context = context or {}
        start_time = time.time()

        capability = await self._provider.get_capability(capability_name)
        if not capability:
            return self._error_result(
                capability_name,
                "capability_not_found",
                f"Capability not found: {capability_name}",
                execution_time_ms=self._elapsed_ms(start_time),
            )

        if self._policy_engine:
            decision = await self._policy_engine.evaluate(
                capability_name,
                arguments,
                {"kind": capability.kind, **context},
            )

            if decision.effect == PolicyEffect.DENY:
                return self._error_result(
                    capability_name,
                    "policy_denied",
                    decision.reason,
                    execution_time_ms=self._elapsed_ms(start_time),
                )

            if decision.effect == PolicyEffect.ASK:
                if APPROVAL_AVAILABLE and self._approval_service:
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
                        ),
                        execution_id=execution_id,
                    )
                    return ExecutionResult(
                        status=ExecutionStatus.FAILURE,
                        error=decision.reason,
                        error_code="requires_approval",
                        execution_time_ms=self._elapsed_ms(start_time),
                        approval_request_id=approval_request.id,
                        approval_status="pending",
                        next={
                            "action": "await_approval",
                            "approval_request_id": approval_request.id,
                            "capability": capability_name,
                            "hint": f"Approval required: {decision.reason}",
                        },
                        can_continue=False,
                    )
                return ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    error=decision.reason,
                    error_code="requires_confirmation",
                    execution_time_ms=self._elapsed_ms(start_time),
                    next={
                        "action": "confirm",
                        "capability": capability_name,
                        "arguments": arguments,
                        "hint": decision.reason,
                    },
                    can_continue=True,
                )

        try:
            result = await self._provider.execute(
                capability_name,
                arguments,
                context,
            )

            return self._success_result(
                capability,
                result,
                execution_time_ms=self._elapsed_ms(start_time),
            )

        except Exception as e:
            return self._error_result(
                capability_name,
                "execution_failed",
                str(e),
                execution_time_ms=self._elapsed_ms(start_time),
            )

    async def execute_many(
        self,
        requests: list[dict[str, Any]],
    ) -> list[ExecutionResult]:
        """Execute multiple capabilities sequentially."""
        results = []
        for req in requests:
            result = await self.execute(
                req["capability_name"],
                req.get("arguments", {}),
                req.get("context"),
            )
            results.append(result)
        return results

    async def execute_after_approval(
        self,
        approval_request_id: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a capability after approval is granted.

        This is called when an approval request is approved, allowing
        the execution to proceed.

        Args:
            approval_request_id: ID of the approved request
            context: Execution context

        Returns:
            ExecutionResult from the capability execution
        """
        if not self._approval_service:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                error="Approval service not configured",
                error_code="approval_not_configured",
            )

        approval_request = await self._approval_service.get_request(approval_request_id)
        if not approval_request:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                error=f"Approval request not found: {approval_request_id}",
                error_code="approval_not_found",
            )

        if approval_request.status.value != "approved":
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                error=f"Approval request not approved: {approval_request.status.value}",
                error_code="approval_denied",
            )

        return await self.execute(
            approval_request.capability_name,
            approval_request.arguments,
            context,
        )

    def _success_result(
        self,
        capability: Capability,
        data: Any,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Create a success result with continuation hints."""
        next_action = "complete"
        can_continue = True

        if capability.continuation and capability.continuation.can_continue:
            if capability.continuation.next_capabilities:
                next_action = "continue"
                can_continue = True

        next_cap = None
        if capability.continuation and capability.continuation.next_capabilities:
            next_cap = capability.continuation.next_capabilities[0]

        next_hint = None
        if capability.continuation:
            next_hint = capability.continuation.next_hint

        render_fmt = None
        if capability.render:
            render_fmt = capability.render.format

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data=data,
            execution_time_ms=execution_time_ms,
            next={
                "action": next_action,
                "capability": next_cap,
                "hint": next_hint,
            },
            format_hint=render_fmt,
            can_continue=can_continue,
        )

    def _error_result(
        self,
        capability_name: str,
        error_code: str,
        error_message: str,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Create an error result with fix hints."""
        fix_hint = self._get_fix_hint(error_code, capability_name)

        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            error=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            next={
                "action": "retry",
                "capability": capability_name,
                "hint": fix_hint,
            },
            can_continue=True,
        )

    def _get_fix_hint(self, error_code: str, capability_name: str) -> str:
        """Get a fix hint based on error code."""
        hints = {
            "capability_not_found": (
                f"Check if '{capability_name}' is registered. "
                "Use list_capabilities() to see available capabilities."
            ),
            "policy_denied": (
                "Review the policy that denied this execution. "
                "Check authentication and authorization."
            ),
            "requires_confirmation": (
                "This capability requires user confirmation. Use confirm_capability() to proceed."
            ),
            "execution_failed": (
                "Check the capability implementation and arguments. "
                "Verify the service is available."
            ),
            "invalid_arguments": (
                "Review the capability's input schema and ensure arguments match."
            ),
            "timeout": "The capability took too long. Try again or increase timeout.",
            "rate_limited": "Too many requests. Wait before retrying.",
        }
        return hints.get(error_code, "Review the error message and try again.")

    def _elapsed_ms(self, start_time: float) -> float:
        """Calculate elapsed time in milliseconds."""
        return (time.time() - start_time) * 1000

    async def execute_streaming(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a capability with streaming support.

        Checks if provider supports streaming, otherwise falls back to regular execution.

        Yields:
            Streaming chunks with type, data, and metadata.
        """
        yield {"type": "start", "capability": capability_name}

        capability = await self._provider.get_capability(capability_name)
        if not capability:
            yield {
                "type": "error",
                "error": f"Capability not found: {capability_name}",
                "error_code": "capability_not_found",
            }
            return

        if self._policy_engine:
            decision = await self._policy_engine.evaluate(
                capability_name,
                arguments,
                {"kind": capability.kind, **(context or {})},
            )

            if decision.effect == PolicyEffect.DENY:
                yield {"type": "error", "error": decision.reason, "error_code": "policy_denied"}
                return

            if decision.effect == PolicyEffect.ASK:
                yield {
                    "type": "approval_required",
                    "reason": decision.reason,
                    "capability": capability_name,
                    "arguments": arguments,
                }
                return

        try:
            provider = self._provider
            if hasattr(provider, 'execute_streaming'):
                async for chunk in provider.execute_streaming(capability_name, arguments, context):
                    yield chunk
            else:
                result = await self.execute(capability_name, arguments, context)
                yield {"type": "result", "status": result.status.value, "data": result.data}
        except Exception as e:
            yield {"type": "error", "error": str(e), "error_code": "execution_failed"}

        yield {"type": "end"}
