"""Tests for runtime services and persistence."""

import pytest

from aicp import Capability, CapabilityKind
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.interfaces.policy_engine import Policy, PolicyCondition, PolicyEffect, PolicySubject

from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.audit import AuditService
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService
from aicp_runtime.services.workflows import WorkflowService


@pytest.fixture
def capability_repo() -> InMemoryCapabilityRepository:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        )
    )
    return repo


@pytest.mark.asyncio
async def test_execution_service_executes_registered_capability(
    capability_repo: InMemoryCapabilityRepository,
) -> None:
    service = ExecutionService(capability_provider=capability_repo)

    result = await service.execute("payments.transfer", {"amount": 125})

    assert result.status == "success"
    assert result.data == {"executed": "payments.transfer", "args": {"amount": 125}}


@pytest.mark.asyncio
async def test_discovery_service_returns_registered_capabilities(
    capability_repo: InMemoryCapabilityRepository,
) -> None:
    service = DiscoveryService(capability_provider=capability_repo)

    discovery = await service.discover()

    assert discovery["metadata"]["capability_count"] == 1
    assert discovery["capabilities"][0]["name"] == "payments.transfer"


@pytest.mark.asyncio
async def test_workflow_service_persists_workflow_state(
    capability_repo: InMemoryCapabilityRepository,
) -> None:
    store = InMemoryRuntimeStore()
    service = WorkflowService(
        capability_provider=capability_repo,
        runtime_store=store,
    )

    workflow = await service.create_workflow(
        name="transfer_flow",
        steps=[{"capability_name": "payments.transfer", "arguments": {"amount": 20}}],
    )
    loaded = await service.get_workflow(workflow.id)

    assert loaded is not None
    assert loaded.id == workflow.id
    assert loaded.status == "pending"


@pytest.mark.asyncio
async def test_runtime_store_tracks_execution_records() -> None:
    store = InMemoryRuntimeStore()

    await store.save_execution_record(
        "exec-123",
        {"capability_name": "payments.transfer", "status": "success"},
    )

    record = await store.get_execution_record("exec-123")

    assert record == {"capability_name": "payments.transfer", "status": "success"}


@pytest.mark.asyncio
async def test_workflow_service_creates_approval_and_audit_when_policy_pauses(
    capability_repo: InMemoryCapabilityRepository,
) -> None:
    store = InMemoryRuntimeStore()
    policy_engine = DefaultPolicyEngine()
    await policy_engine.add_policy(
        Policy(
            name="high_value_approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
    )
    audit_service = AuditService(runtime_store=store)
    approval_service = ApprovalService(runtime_store=store, audit_service=audit_service)
    workflow_service = WorkflowService(
        capability_provider=capability_repo,
        runtime_store=store,
        policy_engine=policy_engine,
        approval_service=approval_service,
        audit_service=audit_service,
    )

    workflow = await workflow_service.create_workflow(
        name="transfer_flow",
        steps=[{"capability_name": "payments.transfer", "arguments": {"amount": 5000}}],
    )
    result = await workflow_service.execute_step(workflow.id, {"requester": "agent-1"})
    approvals = await approval_service.list_approvals()
    history = await audit_service.list_entries(workflow_id=workflow.id)

    assert result.requires_confirmation is True
    assert approvals[0]["workflow_id"] == workflow.id
    assert approvals[0]["status"] == "pending"
    assert any(entry["event_type"] == "approval_request_created" for entry in history)


@pytest.mark.asyncio
async def test_workflow_resume_after_approval_decision_completes_flow(
    capability_repo: InMemoryCapabilityRepository,
) -> None:
    store = InMemoryRuntimeStore()
    policy_engine = DefaultPolicyEngine()
    await policy_engine.add_policy(
        Policy(
            name="high_value_approval",
            effect=PolicyEffect.ASK,
            subject=PolicySubject(capability_name="payments.transfer"),
            condition=PolicyCondition(require_confirmation=True),
        )
    )
    audit_service = AuditService(runtime_store=store)
    approval_service = ApprovalService(runtime_store=store, audit_service=audit_service)
    workflow_service = WorkflowService(
        capability_provider=capability_repo,
        runtime_store=store,
        policy_engine=policy_engine,
        approval_service=approval_service,
        audit_service=audit_service,
    )

    workflow = await workflow_service.create_workflow(
        name="transfer_flow",
        steps=[{"capability_name": "payments.transfer", "arguments": {"amount": 5000}}],
    )
    await workflow_service.execute_step(workflow.id, {"requester": "agent-1"})
    approval = (await approval_service.list_approvals())[0]

    result = await workflow_service.resume_after_approval(
        workflow.id,
        approval["id"],
        decision="approved",
        approver="manager-1",
    )
    reloaded = await workflow_service.get_workflow(workflow.id)
    history = await audit_service.list_entries(workflow_id=workflow.id)

    assert result.success is True
    assert reloaded is not None
    assert reloaded.status == "completed"
    assert any(entry["event_type"] == "approval_decision_made" for entry in history)


@pytest.mark.asyncio
async def test_file_runtime_store_persists_all_runtime_records(tmp_path) -> None:
    store = FileRuntimeStore(tmp_path / "runtime-store")

    workflow = await store.get_workflow("wf-missing")
    assert workflow is None

    from aicp.interfaces.workflow_runtime import WorkflowState

    saved_workflow = WorkflowState(id="wf-1", name="demo", steps=[])
    await store.save_workflow(saved_workflow)
    await store.save_execution_record("exec-1", {"status": "success"})
    await store.save_approval_request(
        {
            "id": "apr-1",
            "capability_name": "payments.transfer",
            "requester": "agent-1",
            "requested_at": "2026-03-30T12:00:00Z",
            "status": "pending",
        }
    )
    await store.save_approval_decision(
        {
            "id": "dec-1",
            "request_id": "apr-1",
            "decision": "approved",
            "decided_at": "2026-03-30T12:05:00Z",
        }
    )
    await store.append_audit_entry(
        {
            "id": "audit-1",
            "timestamp": "2026-03-30T12:00:00Z",
            "event_type": "workflow_created",
            "actor": "runtime",
        }
    )

    reloaded = FileRuntimeStore(tmp_path / "runtime-store")

    loaded_workflow = await reloaded.get_workflow("wf-1")
    loaded_execution = await reloaded.get_execution_record("exec-1")
    loaded_approval = await reloaded.get_approval_request("apr-1")
    loaded_decision = await reloaded.get_approval_decision("dec-1")
    loaded_history = await reloaded.list_audit_entries()

    assert loaded_workflow is not None
    assert loaded_workflow.id == "wf-1"
    assert loaded_execution == {"status": "success"}
    assert loaded_approval is not None
    assert loaded_approval["status"] == "pending"
    assert loaded_decision is not None
    assert loaded_decision["decision"] == "approved"
    assert loaded_history[0]["event_type"] == "workflow_created"


@pytest.mark.asyncio
async def test_sqlite_runtime_store_persists_all_runtime_records(tmp_path) -> None:
    store = SqliteRuntimeStore(tmp_path / "runtime.db")

    workflow = await store.get_workflow("wf-missing")
    assert workflow is None

    from aicp.interfaces.workflow_runtime import WorkflowState

    saved_workflow = WorkflowState(id="wf-sqlite", name="demo", steps=[])
    await store.save_workflow(saved_workflow)
    await store.save_execution_record("exec-sqlite", {"status": "success"})
    await store.save_approval_request(
        {
            "id": "apr-sqlite",
            "capability_name": "payments.transfer",
            "requester": "agent-1",
            "requested_at": "2026-03-30T12:00:00Z",
            "status": "pending",
        }
    )
    await store.save_approval_decision(
        {
            "id": "dec-sqlite",
            "request_id": "apr-sqlite",
            "decision": "approved",
            "decided_at": "2026-03-30T12:05:00Z",
        }
    )
    await store.append_audit_entry(
        {
            "id": "audit-sqlite",
            "timestamp": "2026-03-30T12:00:00Z",
            "event_type": "workflow_created",
            "actor": "runtime",
        }
    )

    reloaded = SqliteRuntimeStore(tmp_path / "runtime.db")

    loaded_workflow = await reloaded.get_workflow("wf-sqlite")
    loaded_execution = await reloaded.get_execution_record("exec-sqlite")
    loaded_approval = await reloaded.get_approval_request("apr-sqlite")
    loaded_decision = await reloaded.get_approval_decision("dec-sqlite")
    loaded_history = await reloaded.list_audit_entries()

    assert loaded_workflow is not None
    assert loaded_workflow.id == "wf-sqlite"
    assert loaded_execution == {"status": "success"}
    assert loaded_approval is not None
    assert loaded_approval["status"] == "pending"
    assert loaded_decision is not None
    assert loaded_decision["decision"] == "approved"
    assert loaded_history[0]["event_type"] == "workflow_created"
