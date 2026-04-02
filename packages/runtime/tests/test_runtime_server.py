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
    console_response = client.get("/console")
    execute_response = client.post(
        "/execute/payments.transfer",
        json={"arguments": {"amount": 50}, "context": {}},
    )

    assert discover_response.status_code == 200
    assert console_response.status_code == 200
    assert "AICP Agent Console" in console_response.text
    assert "Session inspector" in console_response.text
    assert "Workflow monitor" in console_response.text
    assert "Execution explorer" in console_response.text
    assert discover_response.json()["metadata"]["capability_count"] == 1
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "success"


def test_runtime_server_discovery_exposes_capability_graph() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
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
            name="students.get",
            description="Get student",
            kind=CapabilityKind.QUERY,
        )
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    response = client.get("/.well-known/aicp")

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph"]["metadata"]["edge_count"] >= 2
    assert any(edge["type"] == "continuation" for edge in payload["graph"]["edges"])
    assert any(edge["type"] == "requires_session" for edge in payload["graph"]["edges"])


def test_runtime_server_discovery_exposes_extended_graph_edges() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
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
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    response = client.get("/discover")

    assert response.status_code == 200
    edge_types = {edge["type"] for edge in response.json()["graph"]["edges"]}
    assert "dependency" in edge_types
    assert "often_follows" in edge_types
    assert "compensation" in edge_types


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


def test_runtime_server_exposes_interaction_lifecycle_and_ranked_capabilities() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
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
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    interaction_response = client.post(
        "/v1/interactions",
        json={
            "session_id": "sess_123",
            "selected_context": {"tenant_id": "tenant-1"},
        },
    )
    interaction_id = interaction_response.json()["id"]

    patch_response = client.patch(
        f"/v1/interactions/{interaction_id}",
        json={
            "last_capability": "students.create",
            "resource_cache": {"student_id": "stu_123"},
        },
    )
    rank_response = client.get(
        "/v1/capabilities/rank",
        params={
            "query": "student",
            "interaction_id": interaction_id,
            "session_provider": "school-http",
        },
    )

    assert interaction_response.status_code == 201
    assert patch_response.status_code == 200
    assert rank_response.status_code == 200
    ranked = rank_response.json()
    assert ranked[0]["capability"]["name"] == "students.get"


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


def test_runtime_server_exposes_provider_health_route() -> None:
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
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "crm-http",
                },
            }
        ),
        handler=lambda args, ctx: {"ok": True},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    client.post(
        "/execute/crm.contacts.list",
        json={"arguments": {}, "context": {}},
    )
    response = client.get("/providers/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["provider_name"] == "crm-http"
    assert payload[0]["auth_failure_count"] == 1
    assert payload[0]["success_rate"] == 0.0
    assert payload[0]["auth_failure_rate"] == 1.0
    assert payload[0]["failure_rate"] == 1.0
    assert payload[0]["recent_error_code_mix"] == {"missing_session": 1}
    assert payload[0]["last_error_code"] == "missing_session"
    assert payload[0]["health_status"] == "unhealthy"


def test_runtime_server_exposes_approval_review_packet() -> None:
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
                },
                "continuation": {
                    "can_continue": True,
                    "next_capabilities": ["payments.receipt.get"],
                    "next_hint": "Fetch the receipt after approval.",
                },
                "rollback_capability": "payments.refund",
            }
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
    execute_response = client.post(
        f"/workflows/{workflow_id}/execute",
        json={"arguments": {"requester": "agent-1"}},
    )
    approval_id = client.get("/approvals").json()[0]["id"]
    client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved", "approver": "manager-1", "reason": "Reviewed"},
    )

    response = client.get(f"/approvals/{approval_id}/review-packet")

    assert execute_response.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["approval"]["id"] == approval_id
    assert payload["requested_capability"]["name"] == "payments.transfer"
    assert payload["requested_capability"]["provider_name"] == "payments-http"
    assert payload["approver_context"]["approver"] == "manager-1"
    assert payload["policy"]["policy_name"] is None
    assert payload["implications"]["next_capabilities"] == ["payments.receipt.get"]
    assert payload["impact_summary"]["risk_level"] == "high"
    assert payload["impact_summary"]["destructive"] is True
    assert payload["impact_summary"]["rollback_capability"] == "payments.refund"
    assert payload["impact_summary"]["auth_session_implications"]["requires_session"] is True


def test_runtime_server_exposes_workflow_detail_and_timeline_with_compensation() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "payments.transfer",
                "description": "Transfer funds",
                "kind": "action",
                "rollback_capability": "payments.refund",
            }
        ),
        handler=lambda args, ctx: {"transferred": True, **args},
    )
    repo.add_capability(
        Capability(
            name="payments.refund",
            description="Refund funds",
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

    execute_response = client.post(
        f"/workflows/{workflow_id}/execute",
        json={"arguments": {"requester": "agent-1"}},
    )
    approval_id = client.get("/approvals").json()[0]["id"]
    client.post(
        f"/approvals/{approval_id}/decide",
        json={"decision": "approved", "approver": "manager-1"},
    )
    resume_response = client.post(
        f"/workflows/{workflow_id}/resume",
        json={"approval_id": approval_id},
    )
    detail_response = client.get(f"/workflows/{workflow_id}/detail")
    timeline_response = client.get(f"/workflows/{workflow_id}/timeline")

    assert execute_response.status_code == 200
    assert resume_response.status_code == 200
    assert detail_response.status_code == 200
    assert timeline_response.status_code == 200

    detail_payload = detail_response.json()
    timeline_payload = timeline_response.json()
    first_step = detail_payload["workflow"]["steps"][0]

    assert first_step["compensation"] == {
        "rollback_capability": "payments.refund",
        "available": True,
    }
    assert first_step["approval_request_id"] == approval_id

    event_types = [event["event_type"] for event in detail_payload["timeline"]]
    assert "workflow_step_started" in event_types
    assert "workflow_step_waiting" in event_types
    assert "workflow_step_resumed" in event_types
    assert "workflow_step_completed" in event_types

    waiting_event = next(
        event for event in detail_payload["timeline"] if event["event_type"] == "workflow_step_waiting"
    )
    assert waiting_event["approval_request_id"] == approval_id
    assert waiting_event["approval_status"] == "pending"
    assert waiting_event["compensation"]["rollback_capability"] == "payments.refund"
    assert timeline_payload["workflow_id"] == workflow_id
    assert timeline_payload["events"] == detail_payload["timeline"]


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


def test_runtime_server_exposes_ai_facing_v1_execute_contract() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="notes.create",
            description="Create note",
            kind=CapabilityKind.ACTION,
        ),
        handler=lambda args, ctx: {"created": True, **args},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    response = client.post(
        "/v1/execute",
        json={
            "capability_name": "notes.create",
            "arguments": {"title": "AI note"},
            "context": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["capability_name"] == "notes.create"
    assert payload["data"]["created"] is True


def test_runtime_server_exposes_v1_execution_explorer_records() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="notes.create",
            description="Create note",
            kind=CapabilityKind.ACTION,
        ),
        handler=lambda args, ctx: {"created": True, **args},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    execute_response = client.post(
        "/v1/execute",
        json={
            "capability_name": "notes.create",
            "arguments": {"title": "Explorer note"},
            "context": {},
        },
    )

    list_response = client.get("/v1/executions")

    assert execute_response.status_code == 200
    assert list_response.status_code == 200
    execution_id = list_response.json()[0]["execution_id"]
    get_response = client.get(f"/v1/executions/{execution_id}")
    missing_response = client.get("/v1/executions/exe_missing")

    assert list_response.json()[0]["capability_name"] == "notes.create"
    assert get_response.status_code == 200
    assert get_response.json()["execution_id"] == execution_id
    assert get_response.json()["result"]["data"]["title"] == "Explorer note"
    assert missing_response.status_code == 404


def test_runtime_server_redacts_sensitive_execution_context_in_explorer() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "crm.contacts.get",
                "description": "Get contact",
                "kind": "query",
                "auth": {
                    "mode": "session",
                    "requires_session": True,
                    "required_session_provider": "crm-http",
                },
            }
        ),
        handler=lambda args, ctx: {"ok": True},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    session_response = client.post(
        "/v1/sessions",
        json={
            "provider_name": "crm-http",
            "auth_mode": "session",
            "tokens": {"access_token": "super-secret"},
            "headers": {"Authorization": "Bearer secret"},
            "csrf_tokens": {"X-CSRF-Token": "csrf-secret"},
        },
    )
    session_id = session_response.json()["id"]

    execute_response = client.post(
        "/v1/execute",
        json={
            "capability_name": "crm.contacts.get",
            "arguments": {"contact_id": "c_123"},
            "context": {
                "session_id": session_id,
                "headers": {"Authorization": "Bearer user-secret"},
            },
        },
    )
    list_response = client.get("/v1/executions")

    assert execute_response.status_code == 200
    assert list_response.status_code == 200
    record = list_response.json()[0]
    assert record["context"]["session_id"] == session_id
    assert record["context"]["headers"] == "[redacted]"
    assert "resolved_session" not in record["context"]
    assert "resolved_interaction" not in record["context"]


def test_runtime_server_v1_execute_returns_not_found_shape_for_missing_interaction() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="notes.create",
            description="Create note",
            kind=CapabilityKind.ACTION,
        ),
        handler=lambda args, ctx: {"created": True},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    response = client.post(
        "/v1/execute",
        json={
            "capability_name": "notes.create",
            "arguments": {"title": "Missing interaction"},
            "context": {"interaction_id": "int_missing"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "not_found"
    assert payload["next"]["action"] == "inspect_context"


def test_runtime_server_exposes_ai_facing_v1_pause_and_resume_flow() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability(
            name="payments.transfer",
            description="Transfer funds",
            kind=CapabilityKind.ACTION,
        ),
        handler=lambda args, ctx: {"transferred": True, **args},
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
        "/v1/workflows",
        json={
            "name": "travel_checkout",
            "description": "Search, form fill, approval, payment, booking",
            "steps": [
                {
                    "capability_name": "payments.transfer",
                    "arguments": {"amount": 2500, "merchant": "airline"},
                }
            ],
        },
    )
    workflow_id = workflow_response.json()["id"]

    execute_response = client.post(
        f"/v1/workflows/{workflow_id}/execute",
        json={"arguments": {"requester": "ai-agent-1"}},
    )

    assert execute_response.status_code == 202
    paused = execute_response.json()
    assert paused["status"] == "paused_for_approval"
    assert paused["approval_request"]["id"].startswith("apr_")

    approval_id = paused["approval_request"]["id"]
    decide_response = client.post(
        f"/v1/approvals/{approval_id}/decide",
        json={
            "decision": "approved",
            "approver_id": "finance-manager",
            "reason": "Approved by human operator",
        },
    )

    assert decide_response.status_code == 200
    resumed = decide_response.json()
    assert resumed["workflow_id"] == workflow_id
    assert resumed["status"] == "completed"
    assert resumed["data"]["transferred"] is True


def test_runtime_server_exposes_v1_session_lifecycle() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    create_response = client.post(
        "/v1/sessions",
        json={
            "provider_name": "crm-http",
            "auth_mode": "session",
            "cookies": [{"name": "sessionid", "value": "abc123"}],
            "tokens": {"access_token": "secret-token"},
            "csrf_tokens": {"X-CSRF-Token": "csrf-123"},
            "tenant_id": "tenant-1",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    list_response = client.get("/v1/sessions")
    get_response = client.get(f"/v1/sessions/{session_id}")
    revoke_response = client.delete(f"/v1/sessions/{session_id}")
    missing_response = client.get(f"/v1/sessions/{session_id}")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == session_id
    assert get_response.status_code == 200
    assert get_response.json()["provider_name"] == "crm-http"
    assert get_response.json()["tokens"]["access_token"] == "***redacted***"
    assert revoke_response.status_code == 204
    assert missing_response.status_code == 404


def test_runtime_server_v1_execute_fails_on_tenant_session_mismatch() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
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
        ),
        handler=lambda args, ctx: {"ok": True},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    session_response = client.post(
        "/v1/sessions",
        json={
            "provider_name": "school-http",
            "auth_mode": "session",
            "tenant_id": "tenant-a",
            "tokens": {"access_token": "secret-token"},
        },
    )
    session_id = session_response.json()["id"]

    execute_response = client.post(
        "/v1/execute",
        json={
            "capability_name": "students.get",
            "arguments": {},
            "context": {
                "session_id": session_id,
                "tenant_id": "tenant-b",
            },
        },
    )

    assert execute_response.status_code == 200
    payload = execute_response.json()
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "tenant_session_mismatch"


def test_runtime_server_v1_execute_returns_reauth_hint_for_expired_session() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
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
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    session_response = client.post(
        "/v1/sessions",
        json={
            "provider_name": "crm-http",
            "auth_mode": "session",
            "expires_at": "2000-01-01T00:00:00+00:00",
        },
    )
    session_id = session_response.json()["id"]

    execute_response = client.post(
        "/v1/execute",
        json={
            "capability_name": "crm.contacts.update",
            "arguments": {"email": "new@example.com"},
            "context": {"session_id": session_id},
        },
    )

    assert execute_response.status_code == 200
    payload = execute_response.json()
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "needs_reauthentication"
    assert payload["error"]["fix_hint"] == "Refresh or recreate the session before retrying this capability."


def test_runtime_server_v1_refreshes_session() -> None:
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class RefreshHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            body = json.dumps(
                {
                    "access_token": "refreshed-token",
                    "refresh_token": "refreshed-refresh-token",
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
        repo = InMemoryCapabilityRepository("runtime-test")
        app = create_app(capability_provider=repo)
        client = TestClient(app)

        create_response = client.post(
            "/v1/sessions",
            json={
                "provider_name": "crm-http",
                "auth_mode": "bearer",
                "refreshable": True,
                "tokens": {
                    "access_token": "old-token",
                    "refresh_token": "old-refresh-token",
                },
                "auth_recipe": {
                    "kind": "oauth_refresh_token",
                    "token_url": f"http://127.0.0.1:{server.server_port}/oauth/token",
                    "client_id": "client-1",
                    "client_secret": "secret-1",
                },
            },
        )
        session_id = create_response.json()["id"]

        refresh_response = client.post(f"/v1/sessions/{session_id}/refresh")

        assert refresh_response.status_code == 200
        payload = refresh_response.json()
        assert payload["tokens"]["access_token"] == "***redacted***"
        assert payload["tokens"]["refresh_token"] == "***redacted***"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_runtime_server_v1_execute_surfaces_output_validation_warnings() -> None:
    repo = InMemoryCapabilityRepository("runtime-test")
    repo.add_capability(
        Capability.model_validate(
            {
                "name": "students.get",
                "description": "Get student",
                "kind": "query",
                "output_schema": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
                "output_validation_mode": "warn",
            }
        ),
        handler=lambda args, ctx: {"name": "Abhi"},
    )
    app = create_app(capability_provider=repo)
    client = TestClient(app)

    response = client.post(
        "/v1/execute",
        json={
            "capability_name": "students.get",
            "arguments": {},
            "context": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["warnings"][0]["code"] == "output_validation_warning"
