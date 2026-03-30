"""Tests for runtime server boot and routes."""

from fastapi.testclient import TestClient

from aicp import Capability, CapabilityKind
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.interfaces.policy_engine import Policy, PolicyCondition, PolicyEffect, PolicySubject

from aicp_runtime.server.app import create_app


def test_runtime_server_boots_with_discover_and_execute_routes() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        )
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    discover_response = client.get("/discover")
    execute_response = client.post(
        "/execute/payments.transfer",
        json={"arguments": {"amount": 50}, "context": {}},
    )

    assert discover_response.status_code == 200
    assert discover_response.json()["metadata"]["capability_count"] == 1
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "success"


def test_runtime_server_creates_and_lists_workflows() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    create_response = client.post(
        "/workflows",
        json={
            "name": "order_flow",
            "description": "Process an order",
            "steps": [{"capability_name": "orders.create", "arguments": {}}],
        },
    )
    list_response = client.get("/workflows")

    assert create_response.status_code == 200
    assert create_response.json()["name"] == "order_flow"
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_runtime_server_exposes_approvals_history_and_resume() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        )
    )
    policy_engine = DefaultPolicyEngine()

    import asyncio

    asyncio.run(
        policy_engine.add_policy(
            Policy(
                name="high_value_approval",
                effect=PolicyEffect.ASK,
                subject=PolicySubject(capability_name="payments.transfer"),
                condition=PolicyCondition(require_confirmation=True),
            )
        )
    )

    app = create_app(capability_provider=repo, policy_engine=policy_engine)
    client = TestClient(app)

    workflow_response = client.post(
        "/workflows",
        json={
            "name": "transfer_flow",
            "steps": [{"capability_name": "payments.transfer", "arguments": {"amount": 5000}}],
        },
    )
    workflow_id = workflow_response.json()["id"]
    step_response = client.post(
        f"/workflows/{workflow_id}/execute",
        json={"arguments": {"requester": "agent-1"}},
    )
    approvals_response = client.get("/approvals")
    approval_id = approvals_response.json()[0]["id"]
    decide_response = client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved", "approver": "manager-1"},
    )
    resume_response = client.post(f"/workflows/{workflow_id}/resume", json={"approval_id": approval_id})
    history_response = client.get("/history", params={"workflow_id": workflow_id})

    assert step_response.status_code == 200
    assert step_response.json()["requires_confirmation"] is True
    assert approvals_response.status_code == 200
    assert approvals_response.json()[0]["status"] == "pending"
    assert decide_response.status_code == 200
    assert decide_response.json()["decision"] == "approved"
    assert resume_response.status_code == 200
    assert resume_response.json()["success"] is True
    assert history_response.status_code == 200
    assert any(entry["event_type"] == "approval_decision_made" for entry in history_response.json())


def test_runtime_server_can_use_file_backed_store(tmp_path) -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        )
    )
    app = create_app(capability_provider=repo, store_path=tmp_path / "runtime-store")
    client = TestClient(app)

    create_response = client.post(
        "/workflows",
        json={
            "name": "transfer_flow",
            "steps": [{"capability_name": "payments.transfer", "arguments": {"amount": 50}}],
        },
    )
    workflow_id = create_response.json()["id"]

    reloaded_app = create_app(capability_provider=repo, store_path=tmp_path / "runtime-store")
    reloaded_client = TestClient(reloaded_app)
    get_response = reloaded_client.get(f"/workflows/{workflow_id}")

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["id"] == workflow_id


def test_runtime_server_can_use_sqlite_backed_store(tmp_path) -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        )
    )
    db_path = tmp_path / "runtime.db"
    app = create_app(capability_provider=repo, store_path=db_path, store_backend="sqlite")
    client = TestClient(app)

    create_response = client.post(
        "/workflows",
        json={
            "name": "transfer_flow",
            "steps": [{"capability_name": "payments.transfer", "arguments": {"amount": 50}}],
        },
    )
    workflow_id = create_response.json()["id"]

    reloaded_app = create_app(capability_provider=repo, store_path=db_path, store_backend="sqlite")
    reloaded_client = TestClient(reloaded_app)
    get_response = reloaded_client.get(f"/workflows/{workflow_id}")

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["id"] == workflow_id
