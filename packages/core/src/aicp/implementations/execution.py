"""AICP Mock Execution.

Provides a default handler that returns structured results for capabilities
to enable testing governance and execution flow without a live backend.
"""

from __future__ import annotations

import time
from typing import Any

from aicp.interfaces.executor import ExecutionResult, ExecutionStatus


class DefaultMockExecutionHandler:
    """Default mock handler for capability execution.

    Supports:
    - success responses by default
    - optional forced failure via context/arguments
    - simple capability-aware next hints
    - predictable structured payloads for CLI and runtime testing
    """

    def __init__(
        self,
        *,
        include_arguments: bool = True,
        default_format_hint: str = "json",
    ) -> None:
        self.include_arguments = include_arguments
        self.default_format_hint = default_format_hint

    async def __call__(
        self,
        arguments: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> ExecutionResult:
        """Execute mock logic and return a standard ExecutionResult."""
        started = time.perf_counter()

        safe_arguments = arguments or {}
        safe_context = context or {}

        capability_name = safe_context.get("capability_name", "unknown")
        kind = safe_context.get("kind", "action")
        force_error = bool(safe_context.get("mock_error") or safe_arguments.get("__mock_error"))
        force_timeout = bool(safe_context.get("mock_timeout") or safe_arguments.get("__mock_timeout"))
        force_unavailable = bool(
            safe_context.get("mock_unavailable") or safe_arguments.get("__mock_unavailable")
        )

        if force_timeout:
            return ExecutionResult.failure(
                error=f"Mock timeout while executing {capability_name}",
                error_code="timeout",
                status=ExecutionStatus.TIMEOUT,
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "retry",
                    "capability": capability_name,
                    "hint": "Retry later or reduce request complexity.",
                },
                can_continue=True,
            )

        if force_unavailable:
            return ExecutionResult.failure(
                error=f"Mock backend unavailable for {capability_name}",
                error_code="unavailable",
                status=ExecutionStatus.UNAVAILABLE,
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "retry",
                    "capability": capability_name,
                    "hint": "The service is temporarily unavailable.",
                },
                can_continue=True,
            )

        if force_error:
            return ExecutionResult.failure(
                error=f"Mock execution failed for {capability_name}",
                error_code="mock_execution_failed",
                execution_time_ms=self._elapsed_ms(started),
                next={
                    "action": "inspect",
                    "capability": capability_name,
                    "hint": "Inspect arguments or clear the mock failure flag.",
                },
                can_continue=True,
            )

        payload: dict[str, Any] = {
            "mock": True,
            "capability_name": capability_name,
            "kind": kind,
            "message": f"Successfully executed {capability_name} (mock)",
        }

        if self.include_arguments:
            payload["arguments_received"] = safe_arguments

        next_hint = self._infer_next_hint(capability_name, kind)
        next_action = self._infer_next_action(kind)
        continuation_hint = f"Mock execution completed for {capability_name}."

        return ExecutionResult.success(
            data=payload,
            execution_time_ms=self._elapsed_ms(started),
            rendered=f"Mock result: '{capability_name}' completed safely.",
            format_hint=self.default_format_hint,
            next={
                "action": next_action,
                "capability": capability_name if next_action != "complete" else None,
                "hint": next_hint,
            },
            can_continue=True,
            continuation_hint=continuation_hint,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        """Return elapsed time in milliseconds."""
        return (time.perf_counter() - started) * 1000

    @staticmethod
    def _infer_next_action(kind: str) -> str:
        """Infer a sensible next action from capability kind."""
        if kind == "query":
            return "complete"
        return "list"

    @staticmethod
    def _infer_next_hint(capability_name: str, kind: str) -> str:
        """Infer a human-friendly next hint."""
        name = capability_name.lower()

        if "create" in name or "register" in name:
            return "Try fetching or listing the newly created resource next."
        if "update" in name:
            return "Try reading the resource again to verify the update."
        if "delete" in name or "remove" in name:
            return "Try listing remaining resources to confirm deletion."
        if "login" in name or "auth" in name:
            return "Try calling an authenticated capability next."
        if kind == "query":
            return "This was a read operation. Continue only if you need a follow-up action."
        return "Try listing related resources next."