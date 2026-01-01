"""AICP Executor.

Default executor implementation with policy enforcement and result normalization.
"""

import time
from typing import Any

from aicp.capability import Capability
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.executor import ExecutionResult, ExecutionStatus, Executor
from aicp.interfaces.policy_engine import PolicyEffect, PolicyEngine


class AicpExecutor(Executor):
    """Default AICP executor with policy enforcement.

    Wraps a capability provider and adds:
    - Policy evaluation before execution
    - Result normalization
    - Execution timing
    - Error handling with fix hints
    """

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
    ):
        self._provider = capability_provider
        self._policy_engine = policy_engine

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
