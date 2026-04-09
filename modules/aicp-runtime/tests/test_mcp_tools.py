from __future__ import annotations

from typing import Any

import pytest

from aicp import Capability, ExecutionResult

from aicp_runtime.mcp_tools import get_canonical_mcp_tools


class FakeCapabilityProvider:
    def __init__(self, capabilities: list[Capability] | None = None):
        self._capabilities = {cap.name: cap for cap in capabilities or []}

    async def get_capability(self, name: str) -> Capability | None:
        return self._capabilities.get(name)


class FakeDiscoveryService:
    def __init__(
        self,
        *,
        discover_result: dict[str, Any] | None = None,
        ranked_result: list[dict[str, Any]] | None = None,
        provider: FakeCapabilityProvider | None = None,
        discover_error: Exception | None = None,
    ):
        self._discover_result = discover_result or {
            "capabilities": [],
            "metadata": {"capability_count": 0},
        }
        self._ranked_result = ranked_result or []
        self._provider = provider or FakeCapabilityProvider()
        self._discover_error = discover_error
        self.discover_calls = 0
        self.rank_calls: list[dict[str, Any]] = []

    async def discover(self) -> dict[str, Any]:
        self.discover_calls += 1
        if self._discover_error is not None:
            raise self._discover_error
        return self._discover_result

    async def rank_capabilities(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.rank_calls.append(kwargs)
        return self._ranked_result


class FakeExecutionService:
    def __init__(
        self,
        result: ExecutionResult | None = None,
        error: Exception | None = None,
    ):
        self._result = result or ExecutionResult.success(data={"ok": True})
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        capability_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        self.calls.append(
            {
                "capability_name": capability_name,
                "arguments": arguments,
                "context": context,
            }
        )
        if self._error is not None:
            raise self._error
        return self._result


def _tool_map() -> dict[str, Any]:
    return {tool.name: tool for tool in get_canonical_mcp_tools()}


def _sample_capability() -> Capability:
    capability = Capability.model_validate(
        {
            "name": "payments.transfer",
            "description": "Transfer funds",
            "kind": "action",
            "tags": ["payments", "destructive"],
            "input_schema": {
                "type": "object",
                "properties": {"amount": {"type": "number"}},
                "required": ["amount"],
            },
            "output_schema": {
                "type": "object",
                "properties": {"transfer_id": {"type": "string"}},
            },
            "provider": {"name": "payments-http", "type": "openapi"},
            "policy": {"policy_name": "finance_approval"},
        }
    )
    object.__setattr__(
        capability,
        "errors",
        [{"code": "insufficient_funds", "message": "Balance too low"}],
    )
    return capability


def test_get_canonical_mcp_tools_returns_four_expected_tools() -> None:
    tools = get_canonical_mcp_tools()

    assert [tool.name for tool in tools] == [
        "aicp_setup",
        "aicp_list_capabilities",
        "aicp_get_schema",
        "aicp_run",
    ]
    assert all(isinstance(tool.input_schema, dict) for tool in tools)


@pytest.mark.asyncio
async def test_aicp_setup_reports_ready_status_when_env_and_registry_are_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AICP_API_KEY", "api-key")
    monkeypatch.setenv("AICP_MASTER_KEY", "master-key")
    tool = _tool_map()["aicp_setup"]
    discovery = FakeDiscoveryService(
        discover_result={"capabilities": [{"name": "payments.transfer"}]}
    )

    result = await tool.handler({}, None, discovery)

    assert result["status"] == "ready"
    assert result["missing_keys"] == []
    assert "configured" in result["setup_instructions"].lower()


@pytest.mark.asyncio
async def test_aicp_setup_reports_missing_env_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AICP_API_KEY", raising=False)
    monkeypatch.delenv("AICP_MASTER_KEY", raising=False)
    tool = _tool_map()["aicp_setup"]
    discovery = FakeDiscoveryService()

    result = await tool.handler({}, None, discovery)

    assert result["status"] == "needs_setup"
    assert result["missing_keys"] == ["AICP_API_KEY", "AICP_MASTER_KEY"]
    assert "export" in result["setup_instructions"].lower()


@pytest.mark.asyncio
async def test_aicp_setup_reports_registry_error_even_with_env_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AICP_API_KEY", "api-key")
    monkeypatch.setenv("AICP_MASTER_KEY", "master-key")
    tool = _tool_map()["aicp_setup"]
    discovery = FakeDiscoveryService(discover_error=RuntimeError("registry offline"))

    result = await tool.handler({}, None, discovery)

    assert result == {"error": "registry offline", "code": "registry_unhealthy"}


@pytest.mark.asyncio
async def test_aicp_list_capabilities_returns_discovered_capabilities() -> None:
    tool = _tool_map()["aicp_list_capabilities"]
    discovery = FakeDiscoveryService(
        discover_result={
            "capabilities": [
                {
                    "name": "payments.transfer",
                    "description": "Transfer funds",
                    "kind": "action",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "tags": ["payments"],
                    "provider": {"name": "payments-http", "type": "openapi"},
                }
            ]
        }
    )

    result = await tool.handler({}, None, discovery)

    assert result == {
        "capabilities": [
            {
                "name": "payments.transfer",
                "description": "Transfer funds",
                "kind": "action",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "tags": ["payments"],
                "provider": "payments-http",
            }
        ]
    }


@pytest.mark.asyncio
async def test_aicp_list_capabilities_uses_ranked_search_when_filter_present() -> None:
    tool = _tool_map()["aicp_list_capabilities"]
    discovery = FakeDiscoveryService(
        ranked_result=[
            {
                "capability": {
                    "name": "students.get",
                    "description": "Get student",
                    "kind": "query",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "tags": ["school", "query"],
                    "provider": {"name": "school-http", "type": "openapi"},
                },
                "score": 20,
            }
        ]
    )

    result = await tool.handler({"plugin": "school", "type": "query"}, None, discovery)

    assert discovery.rank_calls == [{"query": "school query", "limit": 100}]
    assert result["capabilities"][0]["name"] == "students.get"
    assert result["capabilities"][0]["provider"] == "school-http"


@pytest.mark.asyncio
async def test_aicp_list_capabilities_returns_validation_error_for_non_object_args() -> None:
    tool = _tool_map()["aicp_list_capabilities"]

    result = await tool.handler("bad", None, FakeDiscoveryService())

    assert result == {"error": "Arguments must be an object.", "code": "invalid_arguments"}


@pytest.mark.asyncio
async def test_aicp_get_schema_returns_capability_schema_details() -> None:
    tool = _tool_map()["aicp_get_schema"]
    capability = _sample_capability()
    discovery = FakeDiscoveryService(provider=FakeCapabilityProvider([capability]))

    result = await tool.handler({"capability_name": "payments.transfer"}, None, discovery)

    assert result["name"] == "payments.transfer"
    assert result["input_schema"]["required"] == ["amount"]
    assert result["output_schema"]["properties"]["transfer_id"]["type"] == "string"
    assert result["tags"] == ["payments", "destructive"]
    assert result["approval_required"] is True
    assert result["error_codes"] == ["insufficient_funds"]


@pytest.mark.asyncio
async def test_aicp_get_schema_returns_not_found_error_for_missing_capability() -> None:
    tool = _tool_map()["aicp_get_schema"]
    discovery = FakeDiscoveryService(provider=FakeCapabilityProvider())

    result = await tool.handler({"capability_name": "missing.capability"}, None, discovery)

    assert result == {
        "error": "Capability not found: missing.capability",
        "code": "capability_not_found",
    }


@pytest.mark.asyncio
async def test_aicp_get_schema_requires_capability_name() -> None:
    tool = _tool_map()["aicp_get_schema"]

    result = await tool.handler({}, None, FakeDiscoveryService())

    assert result == {
        "error": "capability_name is required.",
        "code": "invalid_arguments",
    }


@pytest.mark.asyncio
async def test_aicp_run_executes_capability_and_returns_mcp_payload() -> None:
    tool = _tool_map()["aicp_run"]
    execution = FakeExecutionService(
        result=ExecutionResult.success(
            data={"transfer_id": "tr_123"},
            rendered="Transfer complete",
            allowed_next_actions=[
                {
                    "kind": "capability",
                    "name": "payments.receipt.get",
                    "requires_approval": False,
                }
            ],
        )
    )

    result = await tool.handler(
        {
            "capability_name": "payments.transfer",
            "arguments": {"amount": 25},
            "context": {"tenant_id": "tenant-1"},
        },
        execution,
        FakeDiscoveryService(),
    )

    assert execution.calls == [
        {
            "capability_name": "payments.transfer",
            "arguments": {"amount": 25},
            "context": {"tenant_id": "tenant-1"},
        }
    ]
    assert result["status"] == "success"
    assert result["data"] == {"transfer_id": "tr_123"}
    assert result["rendered"] == "Transfer complete"
    assert result["allowed_next_actions"][0]["name"] == "payments.receipt.get"


@pytest.mark.asyncio
async def test_aicp_run_returns_validation_error_when_arguments_is_not_an_object() -> None:
    tool = _tool_map()["aicp_run"]

    result = await tool.handler(
        {"capability_name": "payments.transfer", "arguments": "bad"},
        FakeExecutionService(),
        FakeDiscoveryService(),
    )

    assert result == {
        "error": "arguments must be an object.",
        "code": "invalid_arguments",
    }


@pytest.mark.asyncio
async def test_aicp_run_returns_execution_error_payload() -> None:
    tool = _tool_map()["aicp_run"]
    execution = FakeExecutionService(
        result=ExecutionResult.failure(
            error="Approval required",
            error_code="requires_approval",
            allowed_next_actions=[
                {
                    "kind": "approval",
                    "name": "approval.submit",
                    "requires_approval": False,
                }
            ],
        )
    )

    result = await tool.handler(
        {"capability_name": "payments.transfer", "arguments": {"amount": 5000}},
        execution,
        FakeDiscoveryService(),
    )

    assert result["status"] == "failure"
    assert result["error"] == {"message": "Approval required", "code": "requires_approval"}
    assert result["allowed_next_actions"][0]["name"] == "approval.submit"


@pytest.mark.asyncio
async def test_aicp_run_returns_service_error_when_execution_raises() -> None:
    tool = _tool_map()["aicp_run"]
    execution = FakeExecutionService(error=RuntimeError("executor unavailable"))

    result = await tool.handler(
        {"capability_name": "payments.transfer", "arguments": {}},
        execution,
        FakeDiscoveryService(),
    )

    assert result == {"error": "executor unavailable", "code": "execution_failed"}
