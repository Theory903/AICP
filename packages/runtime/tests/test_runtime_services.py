"""Tests for runtime services and persistence."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aicp import Capability, CapabilityKind, InputSchema, OutputSchema, ProviderInfo
from aicp.implementations import InMemoryCapabilityRepository
from aicp.implementations.execution import HttpCapabilityHandler
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.interfaces.policy_engine import Policy, PolicyCondition, PolicyEffect, PolicySubject

from aicp_runtime.persistence.memory import InMemoryRuntimeStore
from aicp_runtime.persistence.file import FileRuntimeStore
from aicp_runtime.persistence.sqlite import SqliteRuntimeStore
from aicp_runtime.services.approvals import ApprovalService
from aicp_runtime.services.audit import AuditService
from aicp_runtime.services.discovery import DiscoveryService
from aicp_runtime.services.execution import ExecutionService
from aicp_runtime.services.interactions import InteractionStateService
from aicp_runtime.services.provider_health import ProviderHealthService
from aicp_runtime.services.sessions import SessionService
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
async def test_discovery_service_includes_capability_graph_edges() -> None:
    repo = InMemoryCapabilityRepository("graph-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.create",
                "description": "Create student",
                "kind": "action",
                "tags": ["destructive"],
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "school-http",
                },
                "continuation": {
                    "can_continue": True,
                    "next_capabilities": ["students.get"],
                    "next_hint": "Fetch the created student details.",
                },
                "policy": {"policy_name": "high_risk_approval"},
            }
        )
    )
    repo.add_capability(
        Capability(
            name="students.get",
            description="Get student",
            kind=CapabilityKind.QUERY,
        )
    )
    service = DiscoveryService(capability_provider=repo)

    discovery = await service.discover()

    graph = discovery["graph"]
    edge_types = {(edge["source"], edge["target"], edge["type"]) for edge in graph["edges"]}
    node_ids = {node["id"] for node in graph["nodes"]}

    assert "students.create" in node_ids
    assert "students.get" in node_ids
    assert "session:school-http" in node_ids
    assert "approval:human_review" in node_ids
    assert ("students.create", "students.get", "continuation") in edge_types
    assert ("students.create", "session:school-http", "requires_session") in edge_types
    assert ("students.create", "approval:human_review", "requires_approval") in edge_types


@pytest.mark.asyncio
async def test_discovery_service_includes_dependency_and_compensation_edges() -> None:
    repo = InMemoryCapabilityRepository("graph-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "invoice.send",
                "description": "Send invoice",
                "kind": "action",
                "dependency_capabilities": ["invoice.get"],
                "often_follows": ["invoice.mark_paid"],
                "rollback_capability": "invoice.cancel",
            }
        )
    )
    repo.add_capability(
        Capability(name="invoice.get", description="Get invoice", kind=CapabilityKind.QUERY)
    )
    repo.add_capability(
        Capability(
            name="invoice.mark_paid",
            description="Mark invoice paid",
            kind=CapabilityKind.ACTION,
        )
    )
    repo.add_capability(
        Capability(
            name="invoice.cancel",
            description="Cancel invoice",
            kind=CapabilityKind.ACTION,
        )
    )
    service = DiscoveryService(capability_provider=repo)

    discovery = await service.discover()

    edge_types = {
        (edge["source"], edge["target"], edge["type"]) for edge in discovery["graph"]["edges"]
    }

    assert ("invoice.send", "invoice.get", "dependency") in edge_types
    assert ("invoice.send", "invoice.mark_paid", "often_follows") in edge_types
    assert ("invoice.send", "invoice.cancel", "compensation") in edge_types


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
    assert loaded.status == "created"


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
async def test_session_service_persists_and_revokes_session_state() -> None:
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    session = await session_service.create_session(
        provider_name="crm-http",
        auth_mode="session",
        cookies=[{"name": "sessionid", "value": "abc123"}],
        headers={"X-Tenant-Id": "tenant-1"},
        tokens={"access_token": "secret-token"},
        csrf_tokens={"X-CSRF-Token": "csrf-123"},
        tenant_id="tenant-1",
        user_id="ops-user",
    )

    loaded = await session_service.get_session(session["id"])
    sessions = await session_service.list_sessions()
    await session_service.revoke_session(session["id"])
    revoked = await session_service.get_session(session["id"])

    assert loaded is not None
    assert loaded["provider_name"] == "crm-http"
    assert loaded["cookies"][0]["name"] == "sessionid"
    assert sessions[0]["id"] == session["id"]
    assert revoked is None


@pytest.mark.asyncio
async def test_interaction_service_persists_and_updates_state() -> None:
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    interaction_service = InteractionStateService(
        runtime_store=store,
        audit_service=audit_service,
    )

    interaction = await interaction_service.create_interaction(
        session_id="sess_123",
        selected_context={"tenant_id": "tenant-1"},
    )
    updated = await interaction_service.update_interaction(
        interaction["id"],
        last_capability="students.create",
        last_result_summary={"status": "success"},
        resource_cache={"student_id": "stu_123"},
    )
    loaded = await interaction_service.get_interaction(interaction["id"])

    assert updated["last_capability"] == "students.create"
    assert updated["resource_cache"]["student_id"] == "stu_123"
    assert loaded is not None
    assert loaded["session_id"] == "sess_123"


@pytest.mark.asyncio
async def test_discovery_service_ranks_capabilities_with_graph_and_session_context() -> None:
    repo = InMemoryCapabilityRepository("rank-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.create",
                "description": "Create student",
                "kind": "action",
                "continuation": {
                    "can_continue": True,
                    "next_capabilities": ["students.get"],
                },
            }
        )
    )
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.get",
                "description": "Get student",
                "kind": "query",
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "school-http",
                },
            }
        )
    )
    repo.add_capability(
        Capability(
            name="reports.export",
            description="Export report",
            kind=CapabilityKind.ACTION,
        )
    )
    service = DiscoveryService(capability_provider=repo)

    ranked = await service.rank_capabilities(
        query="student",
        session={"provider_name": "school-http"},
        interaction={"last_capability": "students.create"},
        limit=3,
    )

    assert ranked[0]["capability"]["name"] == "students.get"
    assert ranked[0]["score"] > ranked[1]["score"]
    assert any(reason.startswith("graph:") for reason in ranked[0]["reasons"])


@pytest.mark.asyncio
async def test_discovery_service_prefers_semantic_query_and_tag_matches() -> None:
    repo = InMemoryCapabilityRepository("rank-semantic")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.get",
                "description": "Retrieve student profile details for review",
                "kind": "query",
                "tags": ["student", "profile", "lookup"],
            }
        )
    )
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.update",
                "description": "Update student enrollment profile",
                "kind": "action",
                "tags": ["student", "profile"],
            }
        )
    )
    service = DiscoveryService(capability_provider=repo)

    ranked = await service.rank_capabilities(query="lookup student profile", limit=2)

    assert ranked[0]["capability"]["name"] == "students.get"
    assert "query:description_terms" in ranked[0]["reasons"]
    assert "query:tag_match" in ranked[0]["reasons"]
    assert "kind:query_match" in ranked[0]["reasons"]


@pytest.mark.asyncio
async def test_discovery_service_uses_stemming_lite_for_term_overlap() -> None:
    repo = InMemoryCapabilityRepository("rank-stemming")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "invoice.archive",
                "description": "Archive invoice records after processing",
                "kind": "action",
                "tags": ["invoice", "archive"],
            }
        )
    )
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "invoice.send",
                "description": "Send invoice to customer",
                "kind": "action",
                "tags": ["invoice", "delivery"],
            }
        )
    )
    service = DiscoveryService(capability_provider=repo)

    ranked = await service.rank_capabilities(query="archiving invoices", limit=2)

    assert ranked[0]["capability"]["name"] == "invoice.archive"
    assert "query:description_terms" in ranked[0]["reasons"] or "query:tag_match" in ranked[0]["reasons"]


@pytest.mark.asyncio
async def test_discovery_service_reports_planner_friendly_reasons() -> None:
    repo = InMemoryCapabilityRepository("rank-reasons")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "orders.submit",
                "description": "Submit order after cart review",
                "kind": "action",
                "often_follows": ["orders.status.get"],
            }
        )
    )
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "orders.status.get",
                "description": "Get order status details",
                "kind": "query",
                "tags": ["order", "status", "tracking"],
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "orders-http",
                },
            }
        )
    )
    service = DiscoveryService(capability_provider=repo)

    ranked = await service.rank_capabilities(
        query="get order status",
        session={"provider_name": "orders-http"},
        interaction={"last_capability": "orders.submit"},
        limit=2,
    )

    assert ranked[0]["capability"]["name"] == "orders.status.get"
    assert "query:name_contains" in ranked[0]["reasons"]
    assert "query:description_terms" in ranked[0]["reasons"]
    assert "query:tag_match" in ranked[0]["reasons"]
    assert "graph:often_follows" in ranked[0]["reasons"]
    assert "auth:session_compatible" in ranked[0]["reasons"]
    assert "kind:query_match" in ranked[0]["reasons"]


@pytest.mark.asyncio
async def test_provider_health_counts_tenant_session_mismatch_as_auth_failure() -> None:
    repo = InMemoryCapabilityRepository("provider-health")
    repo.add_capability(
        Capability(
            name="students.get",
            description="Get student",
            kind=CapabilityKind.QUERY,
        )
    )
    store = InMemoryRuntimeStore()
    await store.save_execution_record(
        "exec-tenant-mismatch",
        {
            "capability_name": "students.get",
            "status": "failure",
            "created_at": "2026-04-01T12:00:00Z",
            "result": {
                "status": "failure",
                "error_code": "tenant_session_mismatch",
            },
        },
    )
    service = ProviderHealthService(runtime_store=store, capability_provider=repo)

    summaries = await service.list_provider_health()

    assert summaries[0]["auth_failure_count"] == 1


@pytest.mark.asyncio
async def test_session_service_reports_expired_session_health() -> None:
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    session = await session_service.create_session(
        provider_name="crm-http",
        auth_mode="session",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    loaded = await session_service.get_session(session["id"])

    assert loaded is not None
    assert loaded["health_status"] == "expired"
    assert loaded["requires_reauth"] is True


@pytest.mark.asyncio
async def test_execution_service_returns_missing_session_for_session_required_capability() -> None:
    repo = InMemoryCapabilityRepository("runtime-auth")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "crm.contacts.update",
                "description": "Update contact",
                "kind": "action",
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "crm-http",
                },
            }
        ),
        handler=lambda args, ctx: {"ok": True},
    )

    service = ExecutionService(capability_provider=repo)

    result = await service.execute(
        "crm.contacts.update",
        {"email": "new@example.com"},
        {},
    )

    assert result.status == "failure"
    assert result.error_code == "missing_session"
    assert result.next is not None
    assert result.next["action"] == "attach_session"


@pytest.mark.asyncio
async def test_execution_service_persists_preflight_auth_failures() -> None:
    repo = InMemoryCapabilityRepository("runtime-auth")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "crm.contacts.update",
                "description": "Update contact",
                "kind": "action",
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "crm-http",
                },
                "provider": {
                    "name": "crm-http",
                    "type": "openapi",
                },
            }
        ),
        handler=lambda args, ctx: {"ok": True},
    )
    store = InMemoryRuntimeStore()
    service = ExecutionService(capability_provider=repo, runtime_store=store)

    result = await service.execute("crm.contacts.update", {"email": "new@example.com"}, {})
    records = await service.list_execution_records()

    assert result.status == "failure"
    assert len(records) == 1
    assert records[0]["status"] == "failure"
    assert records[0]["result"]["error_code"] == "missing_session"


@pytest.mark.asyncio
async def test_provider_health_service_aggregates_recent_runtime_signals() -> None:
    repo = InMemoryCapabilityRepository("runtime-health")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "crm.contacts.list",
                "description": "List contacts",
                "kind": "query",
                "provider": {
                    "name": "crm-http",
                    "type": "openapi",
                },
            }
        )
    )
    store = InMemoryRuntimeStore()
    await store.save_execution_record(
        "exe_success",
        {
            "execution_id": "exe_success",
            "capability_name": "crm.contacts.list",
            "status": "success",
            "result": {"status": "success"},
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    await store.save_execution_record(
        "exe_auth",
        {
            "execution_id": "exe_auth",
            "capability_name": "crm.contacts.list",
            "status": "failure",
            "result": {"status": "failure", "error_code": "missing_session"},
            "created_at": "2026-01-02T00:00:00Z",
        },
    )
    await store.append_audit_entry(
        {
            "id": "audit_1",
            "timestamp": "2026-01-03T00:00:00Z",
            "event_type": "workflow_step_completed",
            "capability_name": "crm.contacts.list",
        }
    )

    service = ProviderHealthService(runtime_store=store, capability_provider=repo)

    summary = await service.list_provider_health(limit=10)

    assert len(summary) == 1
    assert summary[0]["provider_name"] == "crm-http"
    assert summary[0]["provider_type"] == "openapi"
    assert summary[0]["success_count"] == 2
    assert summary[0]["failure_count"] == 1
    assert summary[0]["auth_failure_count"] == 1
    assert summary[0]["rate_limit_count"] == 0
    assert summary[0]["health_status"] == "degraded"


@pytest.mark.asyncio
async def test_provider_health_service_exposes_rates_latency_and_error_mix() -> None:
    repo = InMemoryCapabilityRepository("runtime-health")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "crm.contacts.list",
                "description": "List contacts",
                "kind": "query",
                "provider": {
                    "name": "crm-http",
                    "type": "openapi",
                },
            }
        )
    )
    store = InMemoryRuntimeStore()
    await store.save_execution_record(
        "exe_success",
        {
            "execution_id": "exe_success",
            "capability_name": "crm.contacts.list",
            "status": "success",
            "result": {"status": "success", "execution_time_ms": 120.0},
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    await store.save_execution_record(
        "exe_auth",
        {
            "execution_id": "exe_auth",
            "capability_name": "crm.contacts.list",
            "status": "failure",
            "result": {
                "status": "failure",
                "error_code": "missing_session",
                "execution_time_ms": 60.0,
            },
            "created_at": "2026-01-02T00:00:00Z",
        },
    )
    await store.save_execution_record(
        "exe_rate_limited",
        {
            "execution_id": "exe_rate_limited",
            "capability_name": "crm.contacts.list",
            "status": "failure",
            "result": {
                "status": "failure",
                "error_code": "rate_limited",
                "execution_time_ms": 180.0,
            },
            "created_at": "2026-01-03T00:00:00Z",
        },
    )

    service = ProviderHealthService(runtime_store=store, capability_provider=repo)

    summary = (await service.list_provider_health(limit=10))[0]

    assert summary["success_rate"] == pytest.approx(1 / 3, rel=1e-3)
    assert summary["failure_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert summary["auth_failure_rate"] == pytest.approx(1 / 3, rel=1e-3)
    assert summary["recent_latency_ms"] == pytest.approx(120.0, rel=1e-3)
    assert summary["recent_error_code_mix"] == {
        "missing_session": 1,
        "rate_limited": 1,
    }
    assert summary["last_error_code"] == "rate_limited"


@pytest.mark.asyncio
async def test_approval_service_builds_review_packet() -> None:
    repo = InMemoryCapabilityRepository("runtime-review")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "payments.transfer",
                "description": "Transfer funds",
                "kind": "action",
                "tags": ["destructive", "risk:high"],
                "provider": {
                    "name": "payments-http",
                    "type": "openapi",
                },
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "payments-http",
                    "refreshable": True,
                },
                "continuation": {
                    "can_continue": True,
                    "next_capabilities": ["payments.receipt.get"],
                    "next_hint": "Fetch the generated receipt after approval.",
                },
                "rollback_capability": "payments.refund",
            }
        )
    )
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    approval_service = ApprovalService(
        runtime_store=store,
        audit_service=audit_service,
        capability_provider=repo,
    )

    workflow_service = WorkflowService(
        capability_provider=repo,
        runtime_store=store,
        audit_service=audit_service,
    )
    workflow = await workflow_service.create_workflow(
        name="transfer_flow",
        steps=[{"capability_name": "payments.transfer", "arguments": {"amount": 5000}}],
    )
    await store.save_execution_record(
        "exe_transfer",
        {
            "execution_id": "exe_transfer",
            "capability_name": "payments.transfer",
            "status": "failure",
            "result": {"status": "failure", "error_code": "requires_approval"},
            "created_at": "2026-01-01T00:00:00Z",
        },
    )

    approval = await approval_service.create_approval_request(
        capability_name="payments.transfer",
        workflow_id=workflow.id,
        arguments={"amount": 5000, "account_id": "acct_123"},
        requester="agent-1",
        message="Transfer requires approval",
        step_id=workflow.steps[0].id,
        policy_name="high_value_approval",
        execution_id="exe_transfer",
        context={
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "session_id": "sess_123",
            "interaction_id": "int_123",
        },
    )
    await approval_service.decide(
        approval_id=approval["id"],
        decision="approved",
        approver="manager-1",
        reason="Transfer validated",
    )

    packet = await approval_service.get_review_packet(approval["id"])

    if packet is None:
        pytest.fail("expected approval review packet")
    assert packet["requested_capability"]["name"] == "payments.transfer"
    assert packet["requested_capability"]["provider_name"] == "payments-http"
    assert packet["requester_context"]["tenant_id"] == "tenant-1"
    assert packet["approver_context"]["approver"] == "manager-1"
    assert packet["linkage"]["workflow"]["id"] == workflow.id
    assert packet["linkage"]["execution"]["id"] == "exe_transfer"
    assert packet["policy"]["policy_name"] == "high_value_approval"
    assert packet["implications"]["resume_available"] is True
    assert packet["implications"]["next_capabilities"] == ["payments.receipt.get"]
    assert packet["impact_summary"] == {
        "risk_level": "high",
        "destructive": True,
        "affected_resource_hints": ["payments", "account_id"],
        "affected_capabilities": ["payments.transfer.list", "payments.transfer.get", "payments.transfer.refund", "payments.transfer.revert", "payments.transfer.cancel"],
        "data_classification": "internal",
        "compliance_flags": ["financial_transaction"],
        "time_sensitivity": "standard",
        "rollback_capability": "payments.refund",
        "reversible": True,
        "blast_radius_estimate": "tenant_scope",
        "auth_session_implications": {
            "auth_mode": "session",
            "requires_session": True,
            "required_session_provider": "payments-http",
            "refreshable": True,
            "session_present": True,
        },
    }


@pytest.mark.asyncio
async def test_execution_service_applies_session_state_to_http_handler() -> None:
    captured: dict[str, str | None] = {}

    class SessionAwareHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            captured["authorization"] = self.headers.get("Authorization")
            captured["cookie"] = self.headers.get("Cookie")
            captured["csrf"] = self.headers.get("X-CSRF-Token")
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), SessionAwareHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        repo = InMemoryCapabilityRepository("runtime-http")
        capability = Capability(
            name="crm.contacts.update",
            description="Update contact",
            kind=CapabilityKind.ACTION,
            input_schema=InputSchema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "body": {"type": "object", "x-location": "body"},
                    },
                    "required": ["body"],
                    "x-aicp-http": {"method": "POST", "path": "/contacts/update"},
                }
            ),
            output_schema=OutputSchema(
                type="object",
                properties={"ok": {"type": "boolean"}},
            ),
            provider=ProviderInfo(
                name="crm-http",
                type="openapi",
                url=f"http://127.0.0.1:{server.server_port}",
            ),
        )
        repo.add_capability(capability, handler=HttpCapabilityHandler(capability))

        store = InMemoryRuntimeStore()
        audit_service = AuditService(runtime_store=store)
        session_service = SessionService(runtime_store=store, audit_service=audit_service)
        session = await session_service.create_session(
            provider_name="crm-http",
            auth_mode="session",
            cookies=[{"name": "sessionid", "value": "abc123"}],
            tokens={"access_token": "secret-token"},
            csrf_tokens={"X-CSRF-Token": "csrf-123"},
        )
        service = ExecutionService(
            capability_provider=repo,
            runtime_store=store,
            session_service=session_service,
        )

        result = await service.execute(
            "crm.contacts.update",
            {"body": {"email": "new@example.com"}},
            {"session_id": session["id"]},
        )

        assert result.status == "success"
        assert captured["authorization"] == "Bearer secret-token"
        assert captured["cookie"] == "sessionid=abc123"
        assert captured["csrf"] == "csrf-123"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@pytest.mark.asyncio
async def test_execution_service_applies_api_key_auth_recipe() -> None:
    captured: dict[str, str | None] = {}

    class ApiKeyHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            captured["api_key"] = self.headers.get("X-API-Key")
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ApiKeyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        repo = InMemoryCapabilityRepository("runtime-http")
        capability = Capability(
            name="crm.contacts.list",
            description="List contacts",
            kind=CapabilityKind.QUERY,
            input_schema=InputSchema.model_validate(
                {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "x-aicp-http": {"method": "GET", "path": "/contacts"},
                }
            ),
            output_schema=OutputSchema(
                type="object",
                properties={"ok": {"type": "boolean"}},
            ),
            provider=ProviderInfo(
                name="crm-http",
                type="openapi",
                url=f"http://127.0.0.1:{server.server_port}",
            ),
        )
        repo.add_capability(capability, handler=HttpCapabilityHandler(capability))

        store = InMemoryRuntimeStore()
        audit_service = AuditService(runtime_store=store)
        session_service = SessionService(runtime_store=store, audit_service=audit_service)
        session = await session_service.create_session(
            provider_name="crm-http",
            auth_mode="api_key",
            tokens={"api_key": "key-123"},
            auth_recipe={
                "kind": "api_key_header",
                "header_name": "X-API-Key",
                "token_field": "api_key",
            },
        )
        service = ExecutionService(
            capability_provider=repo,
            runtime_store=store,
            session_service=session_service,
        )

        result = await service.execute(
            "crm.contacts.list",
            {},
            {"session_id": session["id"]},
        )

        assert result.status == "success"
        assert captured["api_key"] == "key-123"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@pytest.mark.asyncio
async def test_session_service_refreshes_oauth_recipe_session() -> None:
    captured: dict[str, str | None] = {}

    class RefreshHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            captured["body"] = self.rfile.read(length).decode("utf-8")
            body = json.dumps(
                {
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "expires_in": 3600,
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RefreshHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        store = InMemoryRuntimeStore()
        audit_service = AuditService(runtime_store=store)
        session_service = SessionService(runtime_store=store, audit_service=audit_service)
        session = await session_service.create_session(
            provider_name="crm-http",
            auth_mode="bearer",
            tokens={
                "access_token": "old-access-token",
                "refresh_token": "old-refresh-token",
            },
            auth_recipe={
                "kind": "oauth_refresh_token",
                "token_url": f"http://127.0.0.1:{server.server_port}/oauth/token",
                "client_id": "client-1",
                "client_secret": "secret-1",
            },
            refreshable=True,
        )

        refreshed = await session_service.refresh_session(session["id"])

        assert refreshed["tokens"]["access_token"] == "new-access-token"
        assert refreshed["tokens"]["refresh_token"] == "new-refresh-token"
        assert refreshed["health_status"] == "healthy"
        assert captured["body"] is not None
        assert "grant_type=refresh_token" in captured["body"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


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
async def test_runtime_approval_request_accepts_execution_metadata() -> None:
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    approval_service = ApprovalService(runtime_store=store, audit_service=audit_service)

    approval = await approval_service.create_approval_request(
        capability_name="students.create",
        workflow_id=None,
        arguments={"body": {"name": "Abhi"}},
        requester="cli-user",
        message="Approval needed",
        execution_id="exec-123",
        context={"kind": "action"},
    )
    approvals = await approval_service.list_approvals()
    history = await audit_service.list_entries()

    assert approval["execution_id"] == "exec-123"
    assert approval["context"] == {"kind": "action"}
    assert approvals[0]["execution_id"] == "exec-123"
    assert history[0]["metadata"]["execution_id"] == "exec-123"


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
async def test_workflow_service_exposes_detail_timeline_with_failure_and_compensation() -> None:
    repo = InMemoryCapabilityRepository("workflow-detail")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "invoice.send",
                "description": "Send invoice",
                "kind": "action",
                "rollback_capability": "invoice.cancel",
            }
        ),
        handler=lambda args, ctx: (_ for _ in ()).throw(RuntimeError("provider offline")),
    )
    repo.add_capability(
        Capability(
            name="invoice.cancel",
            description="Cancel invoice",
            kind=CapabilityKind.ACTION,
        )
    )
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    workflow_service = WorkflowService(
        capability_provider=repo,
        runtime_store=store,
        audit_service=audit_service,
    )

    workflow = await workflow_service.create_workflow(
        name="invoice_flow",
        steps=[{"capability_name": "invoice.send", "arguments": {"invoice_id": "inv_123"}}],
    )

    result = await workflow_service.execute_step(workflow.id)
    detail = await workflow_service.get_workflow_detail(workflow.id)
    timeline = await workflow_service.get_workflow_timeline(workflow.id)

    assert result.success is False
    assert detail is not None
    assert timeline is not None
    assert detail["workflow"]["status"] == "failed"
    assert detail["workflow"]["steps"][0]["compensation"] == {
        "rollback_capability": "invoice.cancel",
        "available": True,
    }
    event_types = [event["event_type"] for event in detail["timeline"]]
    assert "workflow_step_started" in event_types
    assert "workflow_step_failed" in event_types
    failed_event = next(
        event for event in detail["timeline"] if event["event_type"] == "workflow_step_failed"
    )
    assert failed_event["compensation"]["rollback_capability"] == "invoice.cancel"
    assert failed_event["summary"] == "Step failed: provider offline"
    assert timeline["events"] == detail["timeline"]


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
    await store.save_session_state(
        {
            "id": "sess-1",
            "provider_name": "crm-http",
            "auth_mode": "session",
            "cookies": [{"name": "sessionid", "value": "abc123"}],
            "headers": {},
            "tokens": {},
            "csrf_tokens": {},
            "metadata": {},
            "selected_context": {},
            "created_at": "2026-03-30T12:00:00Z",
            "updated_at": "2026-03-30T12:00:00Z",
        }
    )

    reloaded = FileRuntimeStore(tmp_path / "runtime-store")

    loaded_workflow = await reloaded.get_workflow("wf-1")
    loaded_execution = await reloaded.get_execution_record("exec-1")
    loaded_approval = await reloaded.get_approval_request("apr-1")
    loaded_decision = await reloaded.get_approval_decision("dec-1")
    loaded_history = await reloaded.list_audit_entries()
    loaded_session = await reloaded.get_session_state("sess-1")

    assert loaded_workflow is not None
    assert loaded_workflow.id == "wf-1"
    assert loaded_execution == {"status": "success"}
    assert loaded_approval is not None
    assert loaded_approval["status"] == "pending"
    assert loaded_decision is not None
    assert loaded_decision["decision"] == "approved"
    assert loaded_history[0]["event_type"] == "workflow_created"
    assert loaded_session is not None
    assert loaded_session["provider_name"] == "crm-http"


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
    await store.save_session_state(
        {
            "id": "sess-sqlite",
            "provider_name": "crm-http",
            "auth_mode": "session",
            "cookies": [{"name": "sessionid", "value": "xyz"}],
            "headers": {},
            "tokens": {},
            "csrf_tokens": {},
            "metadata": {},
            "selected_context": {},
            "created_at": "2026-03-30T12:00:00Z",
            "updated_at": "2026-03-30T12:00:00Z",
        }
    )

    reloaded = SqliteRuntimeStore(tmp_path / "runtime.db")

    loaded_workflow = await reloaded.get_workflow("wf-sqlite")
    loaded_execution = await reloaded.get_execution_record("exec-sqlite")
    loaded_approval = await reloaded.get_approval_request("apr-sqlite")
    loaded_decision = await reloaded.get_approval_decision("dec-sqlite")
    loaded_history = await reloaded.list_audit_entries()
    loaded_session = await reloaded.get_session_state("sess-sqlite")

    assert loaded_workflow is not None
    assert loaded_workflow.id == "wf-sqlite"
    assert loaded_execution == {"status": "success"}
    assert loaded_approval is not None
    assert loaded_approval["status"] == "pending"
    assert loaded_decision is not None
    assert loaded_decision["decision"] == "approved"
    assert loaded_history[0]["event_type"] == "workflow_created"
    assert loaded_session is not None
    assert loaded_session["provider_name"] == "crm-http"


# ---------------------------------------------------------------------------
# Memory persistence via SessionService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_service_saves_and_restores_memory_snapshot() -> None:
    """update_memory persists a MemorySnapshot; get_memory restores it."""
    from aicp_runtime.memory.store import MemorySnapshot

    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    session = await session_service.create_session(
        provider_name="test-provider",
        auth_mode="none",
        cookies=[],
        headers={},
        tokens={},
        csrf_tokens={},
        metadata={},
    )
    session_id = session["id"]

    snap = MemorySnapshot(
        episodic=[{"event": "user clicked buy", "ts": "2026-04-01T10:00:00Z"}],
        semantic={"product_id": "prod-123"},
        working={"cart_total": 49.99},
        procedural=[{"name": "checkout", "steps": ["address", "payment", "confirm"]}],
        meta={"token_budget": 1000, "tokens_used": 0},
    )

    await session_service.update_memory(session_id, snap)
    restored = await session_service.get_memory(session_id)

    assert restored is not None
    assert restored.episodic == snap.episodic
    assert restored.semantic == snap.semantic
    assert restored.working == snap.working
    assert restored.procedural == snap.procedural
    assert restored.meta == snap.meta


@pytest.mark.asyncio
async def test_session_service_get_memory_returns_none_when_not_set() -> None:
    """get_memory returns None for a fresh session with no memory set."""
    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    session_id = await session_service.create_session(
        provider_name="test-provider",
        auth_mode="none",
        cookies=[],
        headers={},
        tokens={},
        csrf_tokens={},
        metadata={},
    )

    result = await session_service.get_memory(session_id["id"])
    assert result is None


@pytest.mark.asyncio
async def test_session_service_update_memory_raises_for_missing_session() -> None:
    """update_memory raises ValueError if session does not exist."""
    from aicp_runtime.memory.store import MemorySnapshot

    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    snap = MemorySnapshot()

    with pytest.raises(ValueError, match="not found"):
        await session_service.update_memory("sess-nonexistent", snap)


@pytest.mark.asyncio
async def test_session_service_memory_overwrites_previous_snapshot() -> None:
    """Calling update_memory twice keeps only the latest snapshot."""
    from aicp_runtime.memory.store import MemorySnapshot

    store = InMemoryRuntimeStore()
    audit_service = AuditService(runtime_store=store)
    session_service = SessionService(runtime_store=store, audit_service=audit_service)

    session_id = await session_service.create_session(
        provider_name="test-provider",
        auth_mode="none",
        cookies=[],
        headers={},
        tokens={},
        csrf_tokens={},
        metadata={},
    )
    sid = session_id["id"]

    snap_v1 = MemorySnapshot(working={"step": "checkout"})
    snap_v2 = MemorySnapshot(working={"step": "confirmation", "order_id": "ord-999"})

    await session_service.update_memory(sid, snap_v1)
    await session_service.update_memory(sid, snap_v2)
    restored = await session_service.get_memory(sid)

    assert restored is not None
    assert restored.working == snap_v2.working
    assert restored.working.get("order_id") == "ord-999"
