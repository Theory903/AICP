"""Execution service for the runtime package."""

import uuid
from typing import Any

from aicp.executor import AicpExecutor
from aicp.interfaces.capability_provider import CapabilityProvider
from aicp.interfaces.executor import ExecutionResult
from aicp.interfaces.policy_engine import PolicyEngine

from aicp_runtime.persistence.base import RuntimeStore


class ExecutionService:
    """Executes capabilities and stores execution records."""

    def __init__(
        self,
        capability_provider: CapabilityProvider,
        policy_engine: PolicyEngine | None = None,
        runtime_store: RuntimeStore | None = None,
    ):
        self._executor = AicpExecutor(capability_provider, policy_engine)
        self._store = runtime_store

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        result = await self._executor.execute(capability_name, arguments, context)

        if self._store is not None:
            execution_id = str(uuid.uuid4())
            await self._store.save_execution_record(
                execution_id,
                {
                    "execution_id": execution_id,
                    "capability_name": capability_name,
                    "arguments": arguments,
                    "context": context or {},
                    "result": result.model_dump(mode="json"),
                    "status": result.status.value,
                },
            )

        return result
